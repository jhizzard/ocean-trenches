#!/usr/bin/env python3
"""World ocean-trench scanner -> Google Earth pins.

For every trench (and a few specific steepness targets) this:
  1. fetches a coarse bathymetry grid of the whole bounding box (GMRT),
  2. finds a candidate deepest point and a candidate steepest cliff,
  3. re-fetches a small high-resolution window around each candidate and
     re-scans it -- the two-pass "zoom in" refinement,
  4. writes everything to output/trench-pins.kmz for Google Earth.

Usage:
    python trenches.py                 # scan everything
    python trenches.py mariana tonga   # scan targets matching these names
    python trenches.py --refresh       # ignore the cache, re-download
    python trenches.py --overlays      # also embed depth-colored topo maps

First full run downloads ~150 small grids and may take 10-20 min; grids are
cached, so re-runs finish in seconds.
"""

import math
import os
import re
import sys

from analyze import find_deepest, find_steepest_cliff, load_grid
from build_kml import build_kmz
from fetch import fetch_grid
from trench_data import ALL_TARGETS

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "output", "trench-pins.kmz")

# Half-width (degrees) of the high-resolution window used for the second pass.
ZOOM_HALF_DEG = 0.25
# Half-width (degrees) of the window searched for a trench's steepest cliff,
# centred on the deepest point so the search stays on the trench wall.
CLIFF_SEARCH_HALF_DEG = 0.4
# Horizontal span over which sustained vertical relief ("cliff") is measured.
CLIFF_SPAN_KM = 3.0


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def zoom_window(lat, lon, bbox, half=ZOOM_HALF_DEG):
    """A small bbox centred on (lat, lon), clamped inside the target bbox."""
    w, s, e, n = bbox
    return (
        max(w, lon - half), max(s, lat - half),
        min(e, lon + half), min(n, lat + half),
    )


def refine(point, bbox, scan_fn, refresh):
    """Re-fetch a high-res window around `point` and re-run `scan_fn`."""
    win = zoom_window(point["lat"], point["lon"], bbox)
    if win[2] - win[0] < 0.05 or win[3] - win[1] < 0.05:
        return point  # candidate sat on an edge; keep the coarse result
    path = fetch_grid(*win, resolution="max", refresh=refresh)
    return scan_fn(load_grid(path))


def scan_target(target, refresh):
    """Run the full two-pass scan for one trench / point of interest."""
    coarse_path = fetch_grid(*target.bbox, resolution="med", refresh=refresh)
    coarse = load_grid(coarse_path)

    result = {"target": target, "deepest": None, "deepest_delta_km": None}

    if target.kind == "trench":
        # Seed the high-res refinement from TWO places: the coarse-grid
        # argmin, and the published "best-guess" coordinate. Narrow slots
        # like Challenger Deep are smoothed away at coarse resolution, so
        # the coarse argmin alone can miss them -- the published seed gives
        # the zoom a second, well-placed starting point.
        seeds = [find_deepest(coarse)]
        if target.published is not None:
            # depth_m is a sentinel for the edge-case where refine() cannot
            # open a window and returns the seed unchanged; 0.0 keeps such a
            # seed from ever winning the min() below.
            seeds.append({"lat": target.published.lat,
                          "lon": target.published.lon, "depth_m": 0.0})
        refined = []
        for seed in seeds:
            try:
                refined.append(refine(seed, target.bbox,
                                      find_deepest, refresh))
            except Exception as err:  # noqa: BLE001
                print(f"    (deepest seed skipped: {err})")
        # Keep the genuinely deepest of the refined windows.
        deepest = min(refined, key=lambda d: d["depth_m"])
        result["deepest"] = deepest
        if target.published is not None:
            result["deepest_delta_km"] = haversine_km(
                deepest["lat"], deepest["lon"],
                target.published.lat, target.published.lon,
            )

    # Steepest cliff. For a trench, search the inner wall AROUND THE DEEPEST
    # POINT -- searching the whole (often ~1000 km wide) trench box lets the
    # scan wander onto seamounts and open-ocean features far from the trench.
    # For a point-of-interest the box already IS the feature, so a coarse
    # candidate within it is fine.
    if target.kind == "trench" and result["deepest"] is not None:
        d = result["deepest"]
        cwin = zoom_window(d["lat"], d["lon"], target.bbox,
                           half=CLIFF_SEARCH_HALF_DEG)
    else:
        cand = find_steepest_cliff(coarse, span_km=CLIFF_SPAN_KM)
        cwin = zoom_window(cand["lat"], cand["lon"], target.bbox)

    if cwin[2] - cwin[0] >= 0.05 and cwin[3] - cwin[1] >= 0.05:
        cliff_path = fetch_grid(*cwin, resolution="max", refresh=refresh)
        cliff = find_steepest_cliff(load_grid(cliff_path),
                                    span_km=CLIFF_SPAN_KM)
    else:
        cliff_path = coarse_path  # window collapsed on an edge
        cliff = find_steepest_cliff(coarse, span_km=CLIFF_SPAN_KM)
    result["cliff"] = cliff
    result["cliff_grid_path"] = cliff_path
    return result


def print_summary(results):
    print()
    print(f"{'Target':<42}{'Scan depth':>12}{'Published':>12}"
          f"{'Delta':>9}{'Cliff drop':>12}{'Slope':>9}")
    print("-" * 96)
    for r in results:
        t = r["target"]
        if r["deepest"] is not None:
            scan_d = f"{abs(r['deepest']['depth_m']):,.0f} m"
        else:
            scan_d = "-"
        if t.published is not None:
            pub_d = f"{t.published.depth_m:,.0f} m"
        else:
            pub_d = "-"
        delta = (f"{r['deepest_delta_km']:.0f} km"
                 if r["deepest_delta_km"] is not None else "-")
        c = r["cliff"]
        print(f"{t.name:<42}{scan_d:>12}{pub_d:>12}{delta:>9}"
              f"{c['relief_m']:>9,.0f} m{c['mean_slope_deg']:>8.1f}°")


def render_overlays(results):
    """Render a depth-colored topo PNG for each target's cliff window."""
    from overlays import render_topo  # lazy import: matplotlib only if used
    outdir = os.path.join(os.path.dirname(OUTPUT), "overlays")
    for r in results:
        name = r["target"].name
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        try:
            grid = load_grid(r["cliff_grid_path"])
            png = os.path.join(outdir, f"{slug}.png")
            r["overlay_bounds"] = render_topo(grid, png)
            r["overlay_png"] = png
        except Exception as err:  # noqa: BLE001 - overlays are best-effort
            print(f"    (overlay skipped for {name}: {err})")


def main(argv):
    refresh = "--refresh" in argv
    overlays = "--overlays" in argv
    names = [a.lower() for a in argv if not a.startswith("--")]

    if names:
        targets = [t for t in ALL_TARGETS
                   if any(n in t.name.lower() for n in names)]
        if not targets:
            print(f"No targets matched {names}.")
            return 1
    else:
        targets = ALL_TARGETS

    results = []
    for i, target in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] Scanning {target.name} ...")
        try:
            results.append(scan_target(target, refresh))
        except Exception as err:  # noqa: BLE001 - one bad target must not abort
            print(f"    !! skipped {target.name}: {err}")

    if not results:
        print("No results produced.")
        return 1

    print_summary(results)
    if overlays:
        print("\nRendering topo-map overlays ...")
        render_overlays(results)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    build_kmz(results, OUTPUT, with_overlays=overlays)
    print(f"\nWrote {len(results)} target(s) to {OUTPUT}")
    print("Open it in Google Earth, or import it into Google Earth Web "
          "and share the project link.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
