"""Fetch bathymetry grids from the GMRT GridServer, with a local disk cache.

GMRT (Global Multi-Resolution Topography) blends the GEBCO global grid with
high-resolution multibeam surveys where they exist. The GridServer returns a
GeoTIFF for any bounding box, no auth required.

  https://www.gmrt.org/services/gridserverinfo.php

A first full run downloads ~3 grids per target; everything is cached under
cache/ so re-runs are instant.
"""

import hashlib
import os
import time

import requests

GRIDSERVER = "https://www.gmrt.org/services/GridServer"
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")

# GeoTIFF byte-order magic numbers ("II" little-endian, "MM" big-endian).
_TIFF_MAGIC = (b"II", b"MM")


def _cache_path(west, south, east, north, layer, resolution):
    key = f"{west:.4f}|{south:.4f}|{east:.4f}|{north:.4f}|{layer}|{resolution}"
    digest = hashlib.sha1(key.encode()).hexdigest()[:16]
    return os.path.join(CACHE_DIR, f"gmrt_{digest}.tif")


def fetch_grid(west, south, east, north,
               resolution="med", layer="topo", refresh=False):
    """Download (or read from cache) a GeoTIFF for the given bounding box.

    bbox must not cross the antimeridian (west < east). Returns the local
    file path. `resolution` is one of GMRT's named tiers: default / med /
    high / max.
    """
    if not west < east:
        raise ValueError(
            f"bbox west ({west}) must be < east ({east}); "
            "antimeridian-crossing boxes are not supported"
        )
    if not south < north:
        raise ValueError(f"bbox south ({south}) must be < north ({north})")

    os.makedirs(CACHE_DIR, exist_ok=True)
    path = _cache_path(west, south, east, north, layer, resolution)
    if os.path.exists(path) and not refresh and os.path.getsize(path) > 1024:
        return path

    params = {
        "north": north, "south": south, "east": east, "west": west,
        "layer": layer, "format": "geotiff", "resolution": resolution,
    }

    last_err = None
    for attempt in range(3):
        try:
            resp = requests.get(GRIDSERVER, params=params, timeout=600)
            resp.raise_for_status()
            content = resp.content
            if content[:2] not in _TIFF_MAGIC:
                snippet = content[:160].decode("utf-8", "replace").strip()
                raise RuntimeError(
                    f"GMRT did not return a GeoTIFF. Response begins: {snippet!r}"
                )
            with open(path, "wb") as fh:
                fh.write(content)
            return path
        except Exception as err:  # noqa: BLE001 - retry any transient failure
            last_err = err
            if attempt < 2:
                time.sleep(4 * (attempt + 1))

    raise RuntimeError(f"GMRT fetch failed after 3 attempts: {last_err}")
