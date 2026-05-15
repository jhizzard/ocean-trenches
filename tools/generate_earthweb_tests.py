#!/usr/bin/env python3
"""Generate tiny KML/KMZ probes for Google Earth Web import testing.

The scanner output is too complex to debug by inspection alone. These probes
add one KML feature class at a time so the browser import path can be tested
empirically.
"""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path

import simplekml
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "earthweb-tests"
PNG = OUT / "files" / "tiny-overlay.png"

LAT = 11.3733
LON = 142.5917


def lookat(lon: float = LON, lat: float = LAT, range_m: int = 35000) -> simplekml.LookAt:
    return simplekml.LookAt(
        longitude=lon,
        latitude=lat,
        altitude=0,
        heading=0,
        tilt=0,
        range=range_m,
    )


def save_pair(kml: simplekml.Kml, stem: str) -> None:
    kml_path = OUT / f"{stem}.kml"
    kmz_path = OUT / f"{stem}.kmz"
    kml.save(str(kml_path))
    kml.savekmz(str(kmz_path))


def save_kmz_with_file(kml: simplekml.Kml, stem: str, files: list[Path]) -> None:
    kml_path = OUT / f"{stem}.kml"
    kmz_path = OUT / f"{stem}.kmz"
    kml.save(str(kml_path))
    with zipfile.ZipFile(kmz_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(kml_path, "doc.kml")
        for path in files:
            zf.write(path, f"files/{path.name}")


def make_overlay_png() -> None:
    PNG.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for y in range(256):
        # Violet/deep through red/shallow, with transparency.
        r = int(255 * y / 255)
        b = int(255 * (1 - y / 255))
        draw.line([(0, y), (255, y)], fill=(r, 50, b, 180))
    for x in range(0, 256, 32):
        draw.line([(x, 0), (x, 255)], fill=(255, 255, 255, 200), width=2)
    for y in range(0, 256, 32):
        draw.line([(0, y), (255, y)], fill=(255, 255, 255, 200), width=2)
    img.save(PNG)


def base_doc(stem: str) -> simplekml.Kml:
    return simplekml.Kml(name=stem.replace("_", " ").title())


def point(folder: simplekml.Folder, name: str, lat: float = LAT, lon: float = LON):
    return folder.newpoint(name=name, coords=[(lon, lat)])


def t00_minimal() -> None:
    kml = base_doc("EW Test 00 Minimal Folder Title")
    f = kml.newfolder(name="One Folder")
    point(f, "Minimal placemark")
    save_pair(kml, "t00_minimal_folder_title")


def t01_two_folders() -> None:
    kml = base_doc("EW Test 01 Two Folders")
    point(kml.newfolder(name="Deepest Points"), "Deepest example")
    point(kml.newfolder(name="Steepest Cliffs & Walls"), "Cliff example", LAT + 0.08, LON + 0.08)
    save_pair(kml, "t01_two_folders")


def t02_plain_description() -> None:
    kml = base_doc("EW Test 02 Plain Description")
    p = point(kml.newfolder(name="Deepest Points"), "Plain description placemark")
    p.description = "Depth 10,920 m / 35,827 ft; Challenger Deep."
    save_pair(kml, "t02_plain_description")


def t03_html_description() -> None:
    kml = base_doc("EW Test 03 Html Description")
    p = point(kml.newfolder(name="Deepest Points"), "HTML description placemark")
    p.description = (
        "<b>Depth:</b> 10,920 m / 35,827 ft<br/>"
        "<b>Location:</b> 11.3733, 142.5917<br/>"
        "<hr><i>HTML description probe.</i>"
    )
    save_pair(kml, "t03_html_description")


def t04_lookat() -> None:
    kml = base_doc("EW Test 04 LookAt")
    p = point(kml.newfolder(name="Deepest Points"), "LookAt placemark")
    p.description = "Double-click or open should fly to Challenger Deep."
    p.lookat = lookat()
    save_pair(kml, "t04_lookat")


def t05_polygon() -> None:
    kml = base_doc("EW Test 05 Polygon Outline")
    f = kml.newfolder(name="Trench Outlines")
    pol = f.newpolygon(
        name="Tiny outline",
        outerboundaryis=[
            (LON - 0.25, LAT - 0.2),
            (LON + 0.25, LAT - 0.2),
            (LON + 0.25, LAT + 0.2),
            (LON - 0.25, LAT + 0.2),
            (LON - 0.25, LAT - 0.2),
        ],
    )
    pol.style.polystyle.color = simplekml.Color.changealphaint(40, simplekml.Color.blue)
    pol.style.linestyle.color = simplekml.Color.blue
    pol.style.linestyle.width = 2
    pol.lookat = lookat(range_m=90000)
    save_pair(kml, "t05_polygon_outline")


def t06_http_iconstyle() -> None:
    kml = base_doc("EW Test 06 Http Iconstyle")
    p = point(kml.newfolder(name="Deepest Points"), "HTTP icon style")
    p.description = "Tests original http:// Google-hosted marker icon."
    p.style.iconstyle.icon.href = "http://maps.google.com/mapfiles/kml/paddle/wht-circle.png"
    p.style.iconstyle.color = simplekml.Color.red
    p.style.iconstyle.scale = 1.2
    save_pair(kml, "t06_http_iconstyle")


def t07_https_iconstyle() -> None:
    kml = base_doc("EW Test 07 Https Iconstyle")
    p = point(kml.newfolder(name="Deepest Points"), "HTTPS icon style")
    p.description = "Tests https:// Google-hosted marker icon."
    p.style.iconstyle.icon.href = "https://maps.google.com/mapfiles/kml/paddle/wht-circle.png"
    p.style.iconstyle.color = simplekml.Color.red
    p.style.iconstyle.scale = 1.2
    save_pair(kml, "t07_https_iconstyle")


def t08_hotspot_iconstyle() -> None:
    kml = base_doc("EW Test 08 Hotspot Iconstyle")
    p = point(kml.newfolder(name="Deepest Points"), "HTTPS icon style with hotspot")
    p.description = "Tests icon hotSpot."
    p.style.iconstyle.icon.href = "https://maps.google.com/mapfiles/kml/paddle/wht-circle.png"
    p.style.iconstyle.color = simplekml.Color.red
    p.style.iconstyle.scale = 1.2
    p.style.iconstyle.hotspot = simplekml.HotSpot(
        x=0.5,
        y=0.0,
        xunits=simplekml.Units.fraction,
        yunits=simplekml.Units.fraction,
    )
    save_pair(kml, "t08_hotspot_iconstyle")


def t09_one_groundoverlay() -> None:
    kml = base_doc("EW Test 09 One Groundoverlay")
    f = kml.newfolder(name="Topo Overlays")
    ground = f.newgroundoverlay(name="One embedded overlay")
    ground.icon.href = "files/tiny-overlay.png"
    ground.latlonbox.west = LON - 0.25
    ground.latlonbox.east = LON + 0.25
    ground.latlonbox.south = LAT - 0.2
    ground.latlonbox.north = LAT + 0.2
    ground.description = "One embedded PNG GroundOverlay."
    ground.lookat = lookat(range_m=90000)
    save_kmz_with_file(kml, "t09_one_groundoverlay", [PNG])


def t10_small_full() -> None:
    kml = base_doc("EW Test 10 Small Full Mixed")
    deep = kml.newfolder(name="Deepest Points")
    cliff = kml.newfolder(name="Steepest Cliffs & Walls")
    outline = kml.newfolder(name="Trench Outlines")
    overlays = kml.newfolder(name="Topo Overlays")
    overlays.visibility = 0

    p = point(deep, "Challenger Deep - 10,920 m / 35,827 ft")
    p.description = "<b>Depth:</b> 10,920 m / 35,827 ft<br/>Published comparison included."
    p.lookat = lookat()

    c = point(cliff, "Example cliff - 1,467 m / 4,813 ft drop", LAT + 0.08, LON + 0.08)
    c.description = "<b>Vertical relief:</b> 1,467 m / 4,813 ft<br/>Mean slope: 26 deg."
    c.lookat = lookat(LON + 0.08, LAT + 0.08)

    pol = outline.newpolygon(
        name="Mariana mini outline",
        outerboundaryis=[
            (LON - 0.25, LAT - 0.2),
            (LON + 0.25, LAT - 0.2),
            (LON + 0.25, LAT + 0.2),
            (LON - 0.25, LAT + 0.2),
            (LON - 0.25, LAT - 0.2),
        ],
    )
    pol.style.polystyle.color = simplekml.Color.changealphaint(40, simplekml.Color.blue)
    pol.style.linestyle.color = simplekml.Color.blue
    pol.style.linestyle.width = 2

    ground = overlays.newgroundoverlay(name="Tiny topo overlay")
    ground.icon.href = "files/tiny-overlay.png"
    ground.latlonbox.west = LON - 0.25
    ground.latlonbox.east = LON + 0.25
    ground.latlonbox.south = LAT - 0.2
    ground.latlonbox.north = LAT + 0.2
    ground.description = "Tiny depth-colored test overlay."

    save_kmz_with_file(kml, "t10_small_full_mixed", [PNG])


def t11_many_placemarks() -> None:
    kml = base_doc("EW Test 11 Many Placemarks No Overlays")
    folders = [
        kml.newfolder(name="Deepest Points"),
        kml.newfolder(name="Steepest Cliffs & Walls"),
        kml.newfolder(name="Trench Outlines"),
    ]
    for i in range(75):
        f = folders[i % len(folders)]
        p = point(f, f"Placemark {i + 1:02d}", LAT + (i % 15) * 0.02, LON + (i // 15) * 0.02)
        p.description = f"Probe placemark {i + 1}."
    save_pair(kml, "t11_many_placemarks_no_overlays")


def write_readme() -> None:
    readme = OUT / "README.md"
    readme.write_text(
        """# Google Earth Web KMZ Probe Matrix

Import these files into earth.google.com one at a time, in order. For each
file record: auto-title yes/no, folder tree yes/no, marker visible yes/no,
description popup yes/no, fly-to yes/no, overlay visible yes/no.

Use the same import path each time. Also repeat t00 with the alternate import
path if Earth Web offers both "project" and "data layer" behavior.

Suggested order:

1. t00_minimal_folder_title.kmz
2. t01_two_folders.kmz
3. t02_plain_description.kmz
4. t03_html_description.kmz
5. t04_lookat.kmz
6. t05_polygon_outline.kmz
7. t06_http_iconstyle.kmz
8. t07_https_iconstyle.kmz
9. t08_hotspot_iconstyle.kmz
10. t09_one_groundoverlay.kmz
11. t10_small_full_mixed.kmz
12. t11_many_placemarks_no_overlays.kmz

The first file that degrades from a normal titled project with folders is the
next debugging target.
""",
        encoding="utf-8",
    )


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    make_overlay_png()
    t00_minimal()
    t01_two_folders()
    t02_plain_description()
    t03_html_description()
    t04_lookat()
    t05_polygon()
    t06_http_iconstyle()
    t07_https_iconstyle()
    t08_hotspot_iconstyle()
    t09_one_groundoverlay()
    t10_small_full()
    t11_many_placemarks()
    write_readme()
    print(f"Wrote Google Earth Web probe files to {OUT}")


if __name__ == "__main__":
    main()
