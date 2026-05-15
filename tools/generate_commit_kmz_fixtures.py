#!/usr/bin/env python3
"""Generate KMZ fixtures from each historical build_kml.py implementation."""

from __future__ import annotations

import subprocess
import types
import zipfile
from pathlib import Path
from types import SimpleNamespace

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "earthweb-tests" / "commit-fixtures"
PNG = OUT / "tiny-overlay.png"

COMMITS = [
    "4a9055c",
    "d9eb302",
    "7533d5b",
    "6a22ac0",
    "2a94eb3",
    "9a3dc53",
    "e215fcc",
]


def make_overlay_png() -> None:
    PNG.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for y in range(256):
        draw.line([(0, y), (255, y)], fill=(255, y, 255 - y, 180))
    for y in range(0, 256, 32):
        draw.line([(0, y), (255, y)], fill=(255, 255, 255, 220), width=2)
    img.save(PNG)


def load_builder(commit: str):
    source = subprocess.check_output(
        ["git", "show", f"{commit}:build_kml.py"],
        cwd=ROOT,
        text=True,
    )
    module = types.ModuleType(f"build_kml_{commit}")
    exec(compile(source, f"{commit}:build_kml.py", "exec"), module.__dict__)
    return module.build_kmz


def synthetic_results() -> list[dict]:
    published = SimpleNamespace(
        name="Challenger Deep",
        lat=11.3733,
        lon=142.5917,
        depth_m=10920,
        source="fixture",
    )
    target = SimpleNamespace(
        name="Mariana Fixture",
        bbox=(141.0, 10.0, 145.5, 12.7),
        published=published,
        kind="trench",
        note="Synthetic fixture, not scanner output.",
    )
    return [
        {
            "target": target,
            "deepest": {"lat": 11.3733, "lon": 142.5917, "depth_m": -10920},
            "deepest_delta_km": 0.0,
            "cliff": {
                "lat": 11.45,
                "lon": 142.67,
                "depth_m": -6200,
                "relief_m": 1467,
                "span_km": 3.0,
                "mean_slope_deg": 26.1,
                "peak_slope_deg": 38.0,
            },
            "overlay_png": str(PNG),
            "overlay_bounds": (142.35, 11.15, 142.85, 11.55),
        }
    ]


def count_features(kmz_path: Path) -> str:
    with zipfile.ZipFile(kmz_path) as zf:
        kml = zf.read("doc.kml").decode("utf-8")
    return (
        f"folders={kml.count('<Folder')}, "
        f"placemarks={kml.count('<Placemark')}, "
        f"groundoverlays={kml.count('<GroundOverlay')}, "
        f"iconstyles={kml.count('<IconStyle')}"
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    make_overlay_png()
    results = synthetic_results()

    rows = []
    for commit in COMMITS:
        builder = load_builder(commit)
        pins_path = OUT / f"{commit}_pins_only.kmz"
        overlay_path = OUT / f"{commit}_with_overlay.kmz"
        builder(results, str(pins_path), with_overlays=False)
        builder(results, str(overlay_path), with_overlays=True)
        rows.append((commit, pins_path.name, count_features(pins_path)))
        rows.append((commit, overlay_path.name, count_features(overlay_path)))

    summary = OUT / "README.md"
    summary.write_text(
        "# Commit KMZ Fixtures\n\n"
        "Each file uses the historical build_kml.py from that commit with the "
        "same synthetic trench result. Test these only after the minimal "
        "one-variable probes identify the feature class that breaks Earth Web.\n\n"
        "| Commit | File | Contents |\n"
        "|---|---|---|\n"
        + "\n".join(f"| `{commit}` | `{name}` | {contents} |" for commit, name, contents in rows)
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote commit fixtures to {OUT}")


if __name__ == "__main__":
    main()
