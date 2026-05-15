"""Static registry of the world's major ocean trenches and a handful of
specific steepness targets ("points of interest").

Each bounding box is (west, south, east, north) in decimal degrees, WGS84.
Boxes are deliberately chosen NOT to cross the antimeridian (+/-180 deg) so the
GMRT fetch can stay simple -- see fetch.py.

`published` carries an authoritative, externally-surveyed deepest point where
one is documented. The scanner pins its own grid result and cites this for
comparison. Many values are marked "approximate" -- that is honest: precise
crewed-submersible coordinates only exist for a few deeps.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PublishedDeep:
    name: str
    lat: float
    lon: float
    depth_m: float
    source: str


@dataclass(frozen=True)
class Trench:
    name: str
    west: float
    south: float
    east: float
    north: float
    published: Optional[PublishedDeep] = None
    # "trench" -> emit both a deepest pin and a steepest-cliff pin
    # "feature" -> a focused steepness target; emit only a cliff pin
    kind: str = "trench"
    note: str = ""

    @property
    def bbox(self):
        return (self.west, self.south, self.east, self.north)


# --------------------------------------------------------------------------
# Major ocean trenches
# --------------------------------------------------------------------------
TRENCHES = [
    Trench(
        "Mariana Trench", 141.0, 10.0, 145.5, 12.7,
        PublishedDeep("Challenger Deep", 11.3733, 142.5917, 10920,
                      "Five Deeps Expedition 2019 (vertical accuracy ~+/-6 m)"),
    ),
    Trench(
        # A second hadal deep in the Mariana Trench, ~200 km ENE of
        # Challenger Deep. Box kept tight so the scan stays on Sirena Deep.
        "Mariana Trench - Sirena Deep", 144.42, 11.90, 144.78, 12.25,
        PublishedDeep("Sirena Deep", 12.0654, 144.5811, 10714,
                      "first crewed descent, Five Deeps Expedition 2019"),
    ),
    Trench(
        "Tonga Trench", -176.5, -25.5, -172.5, -14.5,
        PublishedDeep("Horizon Deep", -23.2583, -174.7267, 10817,
                      "Five Deeps Expedition 2019"),
    ),
    Trench(
        "Philippine Trench", 125.0, 5.5, 128.5, 12.5,
        PublishedDeep("Emden Deep", 10.36, 126.66, 10540,
                      "approximate (historical Galathea / Emden soundings)"),
    ),
    Trench(
        "Kuril-Kamchatka Trench", 150.0, 40.0, 161.0, 51.5,
        PublishedDeep("Kuril-Kamchatka deep", 44.07, 150.0, 10542,
                      "approximate (historical Vityaz soundings)"),
    ),
    Trench(
        "Kermadec Trench", -179.5, -37.5, -175.0, -24.5,
        PublishedDeep("Scholl Deep", -31.9, -177.3, 10047,
                      "approximate (Five Deeps Expedition 2019)"),
    ),
    Trench(
        # South edge kept north of ~35.5 N so the box does not reach into the
        # deeper Izu-Ogasawara junction and mis-report it as the Japan Trench.
        "Japan Trench", 142.0, 35.5, 145.5, 40.8,
        PublishedDeep("Japan Trench deep", 36.08, 142.75, 8412,
                      "approximate"),
    ),
    Trench(
        "Izu-Ogasawara Trench", 140.5, 26.5, 144.0, 33.5,
        PublishedDeep("Izu-Ogasawara deep", 29.65, 142.67, 9826,
                      "approximate"),
    ),
    Trench(
        "New Britain Trench", 148.0, -8.5, 154.5, -3.5,
        PublishedDeep("Planet Deep", -6.3, 153.9, 9140,
                      "approximate"),
    ),
    Trench(
        "Aleutian Trench", -180.0, 48.5, -167.5, 54.5,
        PublishedDeep("Aleutian deep", 50.9, -177.0, 7679,
                      "approximate"),
    ),
    Trench(
        "Yap Trench", 136.0, 6.5, 139.5, 11.5,
        PublishedDeep("Yap deep", 8.6, 137.7, 8527,
                      "approximate"),
    ),
    Trench(
        "Palau Trench", 133.0, 5.5, 136.5, 9.5,
        PublishedDeep("Palau deep", 7.85, 134.9, 8054,
                      "approximate"),
    ),
    Trench(
        "Java (Sunda) Trench", 105.0, -13.5, 121.0, -7.5,
        PublishedDeep("Java Deep / Central Deep", -11.13, 114.94, 7290,
                      "approximate (RV Sonne; Five Deeps Expedition 2019)"),
    ),
    Trench(
        "Peru-Chile (Atacama) Trench", -76.5, -31.0, -69.5, -17.5,
        PublishedDeep("Richards Deep", -23.3, -71.4, 8055,
                      "approximate"),
    ),
    Trench(
        "Puerto Rico Trench", -69.5, 17.5, -63.5, 21.0,
        PublishedDeep("Milwaukee Deep", 19.75, -66.9, 8408,
                      "approximate"),
    ),
    Trench(
        "South Sandwich Trench", -30.0, -61.5, -22.5, -54.5,
        PublishedDeep("Meteor Deep", -55.7, -26.2, 8265,
                      "approximate"),
    ),
    Trench(
        # Extended north + east to include the steep Oriente Fault scarp that
        # forms the wall along the south coast of Cuba (see POINTS_OF_INTEREST).
        "Cayman Trench", -82.5, 17.0, -73.5, 20.4,
        PublishedDeep("Cayman Trough deep", 19.0, -80.0, 7686,
                      "approximate"),
    ),
    Trench(
        "Romanche Trench", -22.5, -2.5, -13.5, 2.5,
        PublishedDeep("Romanche deep", 0.0, -18.0, 7760,
                      "approximate"),
    ),
    Trench(
        "Diamantina Trench", 97.5, -37.5, 108.5, -31.5,
        PublishedDeep("Diamantina deep", -35.0, 104.0, 7079,
                      "approximate"),
    ),
]


# --------------------------------------------------------------------------
# Points of interest -- specific steep features the user called out.
# Scanned for the steepest cliff only (no "deepest point" pin).
# --------------------------------------------------------------------------
POINTS_OF_INTEREST = [
    Trench(
        "Cayman Trough - South Cuba Wall (Oriente Scarp)",
        -78.5, 19.2, -74.0, 20.4,
        kind="feature",
        note="Steep transform-fault scarp forming the wall along the south "
             "coast of Cuba; northern edge of the Cayman Trough.",
    ),
    Trench(
        "Java Trench - Central Deep Wall",
        114.5, -11.5, 115.4, -10.7,
        kind="feature",
        note="Central Deep of the Java Trench. Victor Vescovo (Five Deeps "
             "Expedition, 2019) described the inner wall here as nearly vertical.",
    ),
    Trench(
        "Southern Ocean Seamount (53 41'S 25 05'E)",
        24.35, -54.30, 25.85, -53.05,
        kind="feature",
        note="Seamount with a large, very steep flank near "
             "53 deg 40'50\"S, 25 deg 04'56\"E (approx. -53.6807, 25.0821).",
    ),
]


ALL_TARGETS = TRENCHES + POINTS_OF_INTEREST
