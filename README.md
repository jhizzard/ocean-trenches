# Ocean-Trench Deeps & Cliffs → Google Earth

A hobby tool that scans the world's ocean trenches for their **deepest points**
and their **steepest underwater cliffs / walls**, then writes a shareable
Google Earth `.kmz` of pins.

## What it does

For each of ~18 major trenches (plus a few specific steepness targets):

1. Fetches a coarse bathymetry grid of the whole trench from the **GMRT
   GridServer** (blends GEBCO + multibeam surveys, no API key needed).
2. Brute-force scans that grid for the deepest cell and the steepest cliff.
3. Re-fetches a small **high-resolution window** around each candidate and
   re-scans it — a two-pass "zoom in" refinement.
4. Writes `output/trench-pins.kmz` with toggleable folders: Deepest Points,
   Steepest Cliffs & Walls, Trench Outlines, and (with `--overlays`) Topo
   Overlays. It also writes Google Earth Web-safe split imports for browser
   sharing.

A "cliff" is the location of the greatest **sustained vertical relief over a
fixed horizontal span** — the biggest sustained drop, not a single noisy pixel.
For a trench it is searched on the inner wall **around the deepest point**, so
the result is the trench wall itself rather than an off-trench seamount; land
is masked out so coastlines cannot masquerade as submarine cliffs.

Every pin description gives depths in both **metres and feet**.

## Setup

```sh
cd ~/Documents/Trenches
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```sh
python trenches.py                 # scan everything
python trenches.py mariana tonga   # scan only matching targets
python trenches.py --refresh       # ignore cache, re-download
python trenches.py --overlays      # also write Earth Web-safe overlay KMZs
```

First full run downloads ~150 small grids (10–20 min). Grids are cached under
`cache/`, so re-runs finish in seconds.

### Topo overlays

`--overlays` renders each target's steepest-cliff window as a depth-colored
map with white contour lines (the Five Deeps Expedition cliff-map style) and
drapes it on the seafloor as a KML `GroundOverlay`.

Google Earth Web project imports currently allow only 20 image fetches per
import. The Earth Web output is therefore split:

- `output/trench-pins-earthweb-main.kmz` — the main project: all pins,
  folders, outlines, descriptions, yellow caution triangles for steepest-cliff
  pins, and the first 19 topo overlays.
- `output/trench-pins-earthweb-overlay-supplement.kmz` — the remaining topo
  overlays, imported into the same Earth project.

Use **Import file to project** and choose **project features**, not data-layer
import. Data-layer import flattens the folder tree and loses the project
behavior.

## Sharing the result

For Google Earth Web sharing, import `output/trench-pins-earthweb-main.kmz`
as project features, then import
`output/trench-pins-earthweb-overlay-supplement.kmz` into the same project.
Use the resulting Earth project's share link. Google Earth has no global public
pin registry — sharing always means a file or a link.

## Honest caveats

- **Resolution caps precision.** GMRT grid cells are ~100–450 m. The "deepest
  point" is the deepest *grid cell*, not the ±6 m precision of crewed
  submersible surveys. For famous deeps, each pin's description cites the
  authoritative published coordinate and depth for comparison.
- **Cliffs are smoothed.** At grid resolution, true near-vertical walls are
  flattened — computed slopes *underestimate* reality. Steepness here is a
  relative ranking, not an absolute geological measurement.
- Some grid depths are gravity-*predicted*, not sonar-*measured*; provenance
  varies by region.

## Files

| File | Role |
|------|------|
| `trench_data.py` | Registry: trench bounding boxes + published deeps |
| `fetch.py`       | GMRT GridServer download + disk cache |
| `analyze.py`     | Deepest-point and steepest-cliff scanning |
| `overlays.py`    | Depth-colored topo-map PNG rendering (matplotlib) |
| `build_kml.py`   | KMZ generation (simplekml) |
| `trenches.py`    | Orchestrator + summary table (entry point) |
| `tools/rewrite_kmz_for_earthweb.py` | Repackages the full KMZ into Earth Web-safe imports |
