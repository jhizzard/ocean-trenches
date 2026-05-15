"""Turn scan results into a shareable Google Earth KMZ.

Output is organised into toggleable folders:
  * Deepest Points          -- one pin per trench
  * Steepest Cliffs & Walls -- one pin per trench and per point-of-interest
  * Trench Outlines         -- the bounding box scanned for each target
  * Topo Overlays           -- (with --overlays) depth-colored maps draped
                               on the seafloor; off by default, toggle on
"""

import simplekml

M_TO_FT = 3.280839895
_OUTLINE_STYLE_ID = "trench-outline-style"
_CLIFF_STYLE_ID = "cliff-caution-style"
_CLIFF_ICON = "https://maps.google.com/mapfiles/kml/shapes/caution.png"


def _norm_lon(lon):
    """Normalize longitude to the KML-valid [-180, 180] range."""
    while lon > 180.0:
        lon -= 360.0
    while lon < -180.0:
        lon += 360.0
    if lon < -180.0:
        return -180.0
    if lon > 180.0:
        return 180.0
    return lon


def _norm_lon_bounds(west, east):
    """Normalize an east/west pair without breaking antimeridian boxes.

    GMRT sometimes returns Aleutian windows as 180..193 degrees east. Google
    Earth Web rejects those longitudes, so shift the whole box into the
    equivalent -180..-167 range.
    """
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
    return (_norm_lon(west), _norm_lon(east))


def _depth_str(value_m):
    """A vertical distance shown in both metres and feet."""
    m = abs(value_m)
    return f"{m:,.0f} m ({m * M_TO_FT:,.0f} ft)"


def _depth_color(depth_m):
    """Amber (shallower) -> red (deepest) ramp over roughly 6.5-11 km."""
    d = abs(depth_m)
    t = max(0.0, min(1.0, (d - 6500.0) / (11000.0 - 6500.0)))
    red = 255
    green = int(round(200 * (1.0 - t)))
    return simplekml.Color.rgb(red, green, 0)


def _dms(value, positive, negative):
    """Format a decimal degree as degrees/minutes/seconds with a hemisphere."""
    hemi = positive if value >= 0 else negative
    v = abs(value)
    deg = int(v)
    minutes_full = (v - deg) * 60.0
    minutes = int(minutes_full)
    seconds = (minutes_full - minutes) * 60.0
    return f"{deg}°{minutes:02d}'{seconds:05.2f}\"{hemi}"


def _coord_str(lat, lon):
    lon = _norm_lon(lon)
    return (f"{_dms(lat, 'N', 'S')}, {_dms(lon, 'E', 'W')}"
            f" ({lat:.5f}, {lon:.5f})")


def _deepest_description(result):
    t = result["target"]
    d = result["deepest"]
    rows = [
        "<b>Deepest point found by grid scan</b>",
        f"Depth: <b>{_depth_str(d['depth_m'])}</b>",
        f"Location: {_coord_str(d['lat'], d['lon'])}",
        "Source: GMRT bathymetry grid, two-pass scan (coarse + high-res zoom)",
    ]
    pub = t.published
    if pub is not None:
        rows.append("<hr><b>Published deepest point (for comparison)</b>")
        rows.append(f"{pub.name}: {_depth_str(pub.depth_m)}")
        rows.append(f"Location: {_coord_str(pub.lat, pub.lon)}")
        rows.append(f"Source: {pub.source}")
        if result.get("deepest_delta_km") is not None:
            diff_m = abs(d["depth_m"]) - pub.depth_m
            rows.append(
                f"<i>Scan vs published: {result['deepest_delta_km']:.1f} km "
                f"apart; grid scan is {diff_m:+,.0f} m "
                f"({diff_m * M_TO_FT:+,.0f} ft) relative to the published "
                "depth.</i>"
            )
    return "<br/>".join(rows)


def _cliff_description(result):
    t = result["target"]
    c = result["cliff"]
    rows = [
        "<b>Steepest sustained drop found by grid scan</b>",
        f"Vertical relief: <b>{_depth_str(c['relief_m'])}</b> "
        f"over a {c['span_km']:.1f} km span",
        f"Mean slope across the wall: <b>{c['mean_slope_deg']:.1f}&deg;</b>",
        f"Peak single-pixel slope: {c['peak_slope_deg']:.1f}&deg;",
        f"Seafloor depth here: {_depth_str(c['depth_m'])}",
        f"Location: {_coord_str(c['lat'], c['lon'])}",
    ]
    if t.note:
        rows.append(f"<hr><i>{t.note}</i>")
    rows.append(
        "<hr><i>Note: GMRT grid cells are ~100-450 m, which smooths real "
        "cliffs &mdash; true steepness is greater than shown.</i>"
    )
    return "<br/>".join(rows)


def _lookat(lon, lat, range_m):
    """A camera view so Google Earth flies to the feature when it is clicked.

    Without an explicit view, Earth only opens the info balloon and leaves
    the camera where it is.
    """
    return simplekml.LookAt(
        longitude=_norm_lon(lon), latitude=lat, altitude=0,
        heading=0, tilt=0, range=range_m,
    )


def _add_outline_style(kml):
    """One document-level style; Earth Web does not resolve folder-local IDs."""
    style = simplekml.Style()
    style._id = _OUTLINE_STYLE_ID  # simplekml has no public setter for ids.
    style.polystyle.color = simplekml.Color.changealphaint(
        40, simplekml.Color.blue)
    style.linestyle.color = simplekml.Color.blue
    style.linestyle.width = 2
    kml.document._addstyle(style)


def _add_cliff_style(kml):
    """Shared caution-triangle style for steepest-cliff midpoint markers."""
    style = simplekml.Style()
    style._id = _CLIFF_STYLE_ID
    style.iconstyle.icon.href = _CLIFF_ICON
    style.iconstyle.scale = 1.2
    style.iconstyle.hotspot = simplekml.HotSpot(
        x=0.5, y=0.5,
        xunits=simplekml.Units.fraction,
        yunits=simplekml.Units.fraction,
    )
    kml.document._addstyle(style)


def build_kmz(results, path, with_overlays=False):
    # Plain-ASCII name so Google Earth Web auto-titles the project from it.
    kml = simplekml.Kml(name="World Ocean Trenches - Deeps and Cliffs")
    _add_outline_style(kml)
    _add_cliff_style(kml)
    deep_folder = kml.newfolder(name="Deepest Points")
    cliff_folder = kml.newfolder(name="Steepest Cliffs & Walls")
    box_folder = kml.newfolder(name="Trench Outlines")
    overlay_folder = None
    if with_overlays:
        overlay_folder = kml.newfolder(name="Topo Overlays")
        overlay_folder.visibility = 0  # off until the viewer toggles it on

    for result in results:
        t = result["target"]

        if result.get("deepest") is not None:
            d = result["deepest"]
            m = abs(d["depth_m"])
            pnt = deep_folder.newpoint(
                name=f"{t.name} — {m:,.0f} m / {m * M_TO_FT:,.0f} ft",
                coords=[(_norm_lon(d["lon"]), d["lat"])],
            )
            pnt.description = _deepest_description(result)
            pnt.lookat = _lookat(d["lon"], d["lat"], 35000)
            # No custom icon: Earth's built-in marker always renders. An
            # external icon URL (http://) is blocked by Earth Web's HTTPS
            # page and leaves the pin as a gray placeholder.

        c = result["cliff"]
        drop = c["relief_m"]
        cliff = cliff_folder.newpoint(
            name=(f"{t.name} — {drop:,.0f} m / {drop * M_TO_FT:,.0f} ft drop "
                  f"({c['mean_slope_deg']:.0f}°)"),
            coords=[(_norm_lon(c["lon"]), c["lat"])],
        )
        cliff.description = _cliff_description(result)
        cliff.lookat = _lookat(c["lon"], c["lat"], 35000)
        cliff._placemark.styleurl = f"#{_CLIFF_STYLE_ID}"

        w, s, e, n = t.bbox
        pol = box_folder.newpolygon(
            name=t.name,
            outerboundaryis=[
                (_norm_lon(w), s),
                (_norm_lon(e), s),
                (_norm_lon(e), n),
                (_norm_lon(w), n),
                (_norm_lon(w), s),
            ],
        )
        # Range sized to the box so the whole outline fits in view.
        span_deg = max(e - w, n - s)
        pol.lookat = _lookat((w + e) / 2, (s + n) / 2,
                             span_deg * 111_320 * 1.4)
        pol._placemark.styleurl = f"#{_OUTLINE_STYLE_ID}"

        if overlay_folder is not None and result.get("overlay_png"):
            ow, os_, oe, on = result["overlay_bounds"]
            ow, oe = _norm_lon_bounds(ow, oe)
            ground = overlay_folder.newgroundoverlay(name=f"{t.name} — topo")
            ground.icon.href = kml.addfile(result["overlay_png"])
            ground.latlonbox.west = ow
            ground.latlonbox.south = os_
            ground.latlonbox.east = oe
            ground.latlonbox.north = on
            ground.description = ("Depth-colored bathymetry with contour "
                                  "lines, around the steepest cliff (GMRT "
                                  "high-resolution grid).")
            ground.lookat = _lookat((ow + oe) / 2, (os_ + on) / 2,
                                    max(oe - ow, on - os_) * 111_320 * 2.0)

    kml.savekmz(path)
    return path
