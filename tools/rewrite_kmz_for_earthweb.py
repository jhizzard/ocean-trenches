#!/usr/bin/env python3
"""Rewrite an existing trench KMZ into stricter Google Earth Web KML.

This avoids re-running the bathymetry scanner while testing importer fixes.
It fixes only KML packaging issues reported by Earth Web:
  * folder-local outline styles -> one document-level style
  * longitudes outside [-180, 180] -> normalized longitudes
  * optional overlay limiting for probing image-fetch limits
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


KML_NS = "http://www.opengis.net/kml/2.2"
GX_NS = "http://www.google.com/kml/ext/2.2"
K = f"{{{KML_NS}}}"
STYLE_ID = "trench-outline-style"
CLIFF_STYLE_ID = "cliff-caution-style"
CLIFF_ICON = "https://maps.google.com/mapfiles/kml/shapes/caution.png"

ET.register_namespace("", KML_NS)
ET.register_namespace("gx", GX_NS)


def norm_lon(value: float) -> float:
    while value > 180.0:
        value -= 360.0
    while value < -180.0:
        value += 360.0
    return max(-180.0, min(180.0, value))


def fmt(value: float) -> str:
    text = f"{value:.12f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def normalize_coordinates(text: str | None) -> str | None:
    if not text:
        return text
    parts = []
    for coord in text.split():
        values = coord.split(",")
        if len(values) < 2:
            parts.append(coord)
            continue
        try:
            values[0] = fmt(norm_lon(float(values[0])))
        except ValueError:
            pass
        parts.append(",".join(values))
    return " ".join(parts)


def normalize_latlon_boxes(root: ET.Element) -> None:
    for box in root.findall(f".//{K}LatLonBox"):
        west_el = box.find(f"{K}west")
        east_el = box.find(f"{K}east")
        if west_el is None or east_el is None or west_el.text is None or east_el.text is None:
            continue
        west = float(west_el.text)
        east = float(east_el.text)
        if east > 180.0 and west >= 0.0:
            west -= 360.0
            east -= 360.0
            if west < -180.0:
                west = -180.0
        elif west < -180.0 and east <= 0.0:
            west += 360.0
            east += 360.0
            if east > 180.0:
                east = 180.0
        west_el.text = fmt(norm_lon(west))
        east_el.text = fmt(norm_lon(east))


def outline_style() -> ET.Element:
    style = ET.Element(f"{K}Style", {"id": STYLE_ID})
    line = ET.SubElement(style, f"{K}LineStyle")
    ET.SubElement(line, f"{K}color").text = "ffff0000"
    ET.SubElement(line, f"{K}colorMode").text = "normal"
    ET.SubElement(line, f"{K}width").text = "2"
    poly = ET.SubElement(style, f"{K}PolyStyle")
    ET.SubElement(poly, f"{K}color").text = "28ff0000"
    ET.SubElement(poly, f"{K}colorMode").text = "normal"
    ET.SubElement(poly, f"{K}fill").text = "1"
    ET.SubElement(poly, f"{K}outline").text = "1"
    return style


def cliff_icon_style() -> ET.Element:
    style = ET.Element(f"{K}Style", {"id": CLIFF_STYLE_ID})
    icon_style = ET.SubElement(style, f"{K}IconStyle")
    ET.SubElement(icon_style, f"{K}scale").text = "1.2"
    icon = ET.SubElement(icon_style, f"{K}Icon")
    ET.SubElement(icon, f"{K}href").text = CLIFF_ICON
    ET.SubElement(
        icon_style,
        f"{K}hotSpot",
        {"x": "0.5", "y": "0.5", "xunits": "fraction", "yunits": "fraction"},
    )
    return style


def parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def set_style_url(placemark: ET.Element, style_id: str) -> None:
    style_url = placemark.find(f"{K}styleUrl")
    if style_url is None:
        style_url = ET.Element(f"{K}styleUrl")
        insert_at = 0
        for index, child in enumerate(list(placemark)):
            if child.tag not in {f"{K}name", f"{K}description", f"{K}LookAt"}:
                insert_at = index
                break
        else:
            insert_at = len(placemark)
        placemark.insert(insert_at, style_url)
    style_url.text = f"#{style_id}"


def fix_styles(root: ET.Element, add_cliff_icons: bool) -> None:
    doc = root.find(f"{K}Document")
    if doc is None:
        return

    parents = parent_map(root)
    for style in list(root.findall(f".//{K}Style")):
        parent = parents.get(style)
        if parent is not None:
            parent.remove(style)

    doc.insert(0, outline_style())
    if add_cliff_icons:
        doc.insert(1, cliff_icon_style())

    for placemark in root.findall(f".//{K}Placemark"):
        if placemark.find(f"{K}Polygon") is None:
            continue
        set_style_url(placemark, STYLE_ID)

    if not add_cliff_icons:
        return
    for folder in root.findall(f".//{K}Folder"):
        name = folder.find(f"{K}name")
        if name is None or name.text != "Steepest Cliffs & Walls":
            continue
        for placemark in folder.findall(f"{K}Placemark"):
            set_style_url(placemark, CLIFF_STYLE_ID)


def limit_overlays(
    root: ET.Element,
    start: int,
    limit: int | None,
) -> set[str] | None:
    if limit is None and start == 0:
        return None
    used: set[str] = set()
    overlays = root.findall(f".//{K}GroundOverlay")
    parents = parent_map(root)
    for index, overlay in enumerate(overlays):
        href = overlay.find(f"{K}Icon/{K}href")
        keep = index >= start and (limit is None or index < start + limit)
        if keep:
            if href is not None and href.text:
                used.add(href.text)
        else:
            parent = parents.get(overlay)
            if parent is not None:
                parent.remove(overlay)
    return used


def rename_overlay_folder(root: ET.Element, folder_name: str | None) -> None:
    if not folder_name:
        return
    for folder in root.findall(f".//{K}Folder"):
        name = folder.find(f"{K}name")
        if name is not None and name.text == "Topo Overlays":
            name.text = folder_name


def keep_only_overlay_folder(root: ET.Element) -> None:
    doc = root.find(f"{K}Document")
    if doc is None:
        return
    for child in list(doc):
        if child.tag != f"{K}Folder":
            continue
        name = child.find(f"{K}name")
        if name is None or name.text != "Topo Overlays":
            doc.remove(child)


def remove_empty_overlay_folder(root: ET.Element) -> None:
    parents = parent_map(root)
    for folder in root.findall(f".//{K}Folder"):
        name = folder.find(f"{K}name")
        if name is None or name.text != "Topo Overlays":
            continue
        if folder.findall(f"{K}GroundOverlay"):
            return
        parent = parents.get(folder)
        if parent is not None:
            parent.remove(folder)


def rewrite_kml(
    kml_bytes: bytes,
    overlay_start: int,
    overlay_limit: int | None,
    overlays_only: bool,
    overlay_folder_name: str | None,
) -> tuple[bytes, set[str] | None]:
    root = ET.fromstring(kml_bytes)

    for lon in root.findall(f".//{K}longitude"):
        if lon.text:
            lon.text = fmt(norm_lon(float(lon.text)))
    for coords in root.findall(f".//{K}coordinates"):
        coords.text = normalize_coordinates(coords.text)
    normalize_latlon_boxes(root)
    fix_styles(root, add_cliff_icons=not overlays_only)
    used_overlays = limit_overlays(root, overlay_start, overlay_limit)
    if overlays_only:
        keep_only_overlay_folder(root)
    rename_overlay_folder(root, overlay_folder_name)
    remove_empty_overlay_folder(root)

    return ET.tostring(root, encoding="utf-8", xml_declaration=True), used_overlays


def rewrite_kmz(
    source: Path,
    dest: Path,
    overlay_start: int,
    overlay_limit: int | None,
    overlays_only: bool,
    overlay_folder_name: str | None,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(source) as zf:
            zf.extractall(tmp_path)

        doc_path = tmp_path / "doc.kml"
        fixed_kml, used_overlays = rewrite_kml(
            doc_path.read_bytes(),
            overlay_start,
            overlay_limit,
            overlays_only,
            overlay_folder_name,
        )
        doc_path.write_bytes(fixed_kml)

        if used_overlays is not None:
            files_dir = tmp_path / "files"
            if files_dir.exists():
                for path in files_dir.iterdir():
                    href = f"files/{path.name}"
                    if href not in used_overlays:
                        path.unlink()

        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(tmp_path.rglob("*")):
                if path.is_file():
                    zf.write(path, path.relative_to(tmp_path).as_posix())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("dest", type=Path)
    parser.add_argument(
        "--overlay-limit",
        type=int,
        default=None,
        help="Keep only the first N GroundOverlays. Use 0 for no overlays.",
    )
    parser.add_argument(
        "--overlay-start",
        type=int,
        default=0,
        help="Zero-based index of the first GroundOverlay to keep.",
    )
    parser.add_argument(
        "--overlays-only",
        action="store_true",
        help="Remove pin and outline folders, keeping only the Topo Overlays folder.",
    )
    parser.add_argument(
        "--overlay-folder-name",
        default=None,
        help="Rename the Topo Overlays folder in the rewritten KMZ.",
    )
    args = parser.parse_args()
    rewrite_kmz(
        args.source,
        args.dest,
        args.overlay_start,
        args.overlay_limit,
        args.overlays_only,
        args.overlay_folder_name,
    )
    print(f"Wrote {args.dest}")


if __name__ == "__main__":
    main()
