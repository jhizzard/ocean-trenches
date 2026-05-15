"""Render bathymetry windows as colored topo-map overlays for Google Earth.

Each overlay is a depth-colored raster with white contour lines -- the style
of the Five Deeps Expedition cliff-ascent maps -- saved as a PNG and draped
on the seafloor via a KML GroundOverlay.
"""

import os

import matplotlib

matplotlib.use("Agg")  # headless rendering, no display needed

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def render_topo(grid, png_path, contour_levels=22, max_px=750):
    """Render `grid` to a depth-colored PNG with white contour lines.

    Returns (west, south, east, north) bounds for the KML GroundOverlay.
    """
    z = grid.z
    # Downsample only very large grids so PNGs stay a sane size; the
    # geographic extent is unchanged by striding.
    step = max(1, max(z.shape) // max_px)
    z = np.ma.masked_invalid(z[::step, ::step])
    h, w = z.shape

    dpi = 100
    fig = plt.figure(figsize=(w / dpi, h / dpi), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()

    # 'rainbow' runs violet (deepest) -> red (shallowest), matching the
    # Five Deeps Expedition cliff-ascent maps.
    cmap = plt.get_cmap("rainbow").copy()
    cmap.set_bad(alpha=0.0)  # NaN / no-data -> transparent

    extent = (0, w, h, 0)
    ax.imshow(z, cmap=cmap, origin="upper", aspect="auto", extent=extent)
    if z.count() > 4:
        try:
            ax.contour(z, levels=contour_levels, colors="white",
                       linewidths=1.0, alpha=1.0,
                       origin="upper", extent=extent)
        except Exception:  # noqa: BLE001 - contouring is best-effort
            pass
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)

    os.makedirs(os.path.dirname(png_path), exist_ok=True)
    fig.savefig(png_path, dpi=dpi, transparent=True)
    plt.close(fig)

    b = grid.bounds
    return (b.left, b.bottom, b.right, b.top)
