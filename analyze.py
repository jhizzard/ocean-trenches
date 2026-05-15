"""Scan a bathymetry grid for the deepest point and the steepest "cliff".

A "cliff" is defined as the location of the greatest *vertical relief over a
fixed horizontal span* -- i.e. the biggest sustained drop. That is more
meaningful (and far less noise-prone) than a single-pixel gradient, and it
directly answers "biggest / most sustained underwater drop".

Both scans run on a *despiked* copy of the grid: a 3x3 median filter that
removes isolated bad soundings. Global bathymetry grids contain occasional
spurious cells (a single pixel hundreds of metres off its neighbours); a raw
argmin would happily report one as the "deepest point".

For each cliff we report:
  * relief_m      -- vertical drop within the analysis window
  * span_km       -- horizontal width of that window
  * mean_slope    -- atan(relief / span): the slope sustained across the wall
  * peak_slope    -- the single steepest pixel inside the window

Caveat: at GMRT grid resolution (~100-450 m/pixel) real cliffs are smoothed,
so computed slopes UNDERESTIMATE reality. Treat steepness as a relative
ranking, not an absolute geological measurement.
"""

import math
import warnings

import numpy as np
import rasterio
from rasterio.transform import xy as transform_xy

M_PER_DEG_LAT = 111_320.0


class Grid:
    """A loaded bathymetry tile: elevation array + geo-referencing."""

    def __init__(self, z, transform, bounds):
        self.z = z                      # 2-D float array, NaN where no data
        self.transform = transform
        self.bounds = bounds
        mean_lat = (bounds.top + bounds.bottom) / 2.0
        self.dx_m = abs(transform.a) * M_PER_DEG_LAT * math.cos(math.radians(mean_lat))
        self.dy_m = abs(transform.e) * M_PER_DEG_LAT

    def lonlat(self, row, col):
        """Pixel-center (lon, lat) for an array index."""
        lon, lat = transform_xy(self.transform, int(row), int(col))
        return lon, lat


def load_grid(path):
    with rasterio.open(path) as src:
        masked = src.read(1, masked=True)
        z = np.ma.filled(masked.astype("float64"), np.nan)
        return Grid(z, src.transform, src.bounds)


def _despike(z, k=3):
    """k x k median filter: removes isolated bad-sounding pixels.

    A genuine deep or wall is many pixels wide and survives the filter; a
    lone spurious pixel is replaced by its neighbourhood median.
    """
    if min(z.shape) < k:
        return z
    windows = np.lib.stride_tricks.sliding_window_view(z, (k, k))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        med = np.nanmedian(windows, axis=(-1, -2))
    return np.pad(med, k // 2, mode="edge")


def _safe_depth(z, smooth, row, col):
    """Real grid depth at (row, col), falling back to the despiked value."""
    value = z[row, col]
    if np.isnan(value):
        value = smooth[row, col]
    return float(value)


def find_deepest(grid):
    """Deepest *corroborated* cell in the grid (spurious pixels ignored)."""
    z = grid.z
    if np.all(np.isnan(z)):
        raise RuntimeError("grid is empty / all-nodata")
    smooth = _despike(z)
    if np.all(np.isnan(smooth)):
        raise RuntimeError("grid has no corroborated data")
    row, col = np.unravel_index(np.nanargmin(smooth), smooth.shape)
    lon, lat = grid.lonlat(row, col)
    return {"lat": lat, "lon": lon, "depth_m": _safe_depth(z, smooth, row, col)}


def _slope_field(z, dx_m, dy_m):
    """Per-pixel slope magnitude in degrees."""
    gy, gx = np.gradient(z, dy_m, dx_m)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def _relief_field(z, k):
    """Vertical relief (max - min) over every k x k window.

    Returns an array of shape (H-k+1, W-k+1); element (i, j) covers the
    window whose top-left corner is (i, j).
    """
    windows = np.lib.stride_tricks.sliding_window_view(z, (k, k))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        hi = np.nanmax(windows, axis=(-1, -2))
        lo = np.nanmin(windows, axis=(-1, -2))
    return hi - lo


def find_steepest_cliff(grid, span_km=3.0):
    """Locate the window of greatest sustained vertical relief.

    Underwater features only: land and any above-water cells (elevation
    >= 0) are dropped, so a window straddling a coastline cannot
    masquerade as a giant submarine cliff.
    """
    z = np.where(grid.z >= 0.0, np.nan, grid.z)
    smooth = _despike(z)
    if np.all(np.isnan(smooth)):
        raise RuntimeError("grid has no corroborated data")

    pix_m = min(grid.dx_m, grid.dy_m)
    k = int(round((span_km * 1000.0) / pix_m))
    k = max(3, min(k, smooth.shape[0], smooth.shape[1]))

    relief = _relief_field(smooth, k)
    if np.all(np.isnan(relief)):
        raise RuntimeError("no valid relief could be computed for this grid")

    wi, wj = np.unravel_index(np.nanargmax(relief), relief.shape)
    relief_m = float(relief[wi, wj])

    # Centre of the winning window, in original-array coordinates.
    row, col = wi + k // 2, wj + k // 2
    lon, lat = grid.lonlat(row, col)

    # Peak single-pixel slope inside that window.
    slope = _slope_field(smooth, grid.dx_m, grid.dy_m)
    patch = slope[wi:wi + k, wj:wj + k]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        peak_slope = float(np.nanmax(patch))

    span_m = k * pix_m
    mean_slope = math.degrees(math.atan(relief_m / span_m))

    return {
        "lat": lat, "lon": lon,
        "depth_m": _safe_depth(z, smooth, row, col),
        "relief_m": relief_m,
        "span_km": span_m / 1000.0,
        "mean_slope_deg": mean_slope,
        "peak_slope_deg": peak_slope,
    }
