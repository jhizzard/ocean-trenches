# HANDOFF — Ocean Trenches → Google Earth Web

**Date:** 2026-05-15
**Repo:** https://github.com/jhizzard/ocean-trenches  ·  **Local:** `~/Documents/Trenches`
**Audience:** the next coding session — any model (Claude, Codex, etc.). **Read this whole file before changing anything.**

---

## STATUS: the Google Earth Web output is FAILED AND NOT SOLVED

The Python scanner (the science/data pipeline) **works and is correct**. The
**Google Earth deliverable does not work in Google Earth Web** and multiple
fix attempts this session FAILED. Every issue in the "UNSOLVED ISSUES"
section below is open.

---

## HARD CONSTRAINTS — do not violate

1. **Google Earth WEB only** (`https://earth.google.com`). The user's machine
   (Intel i7‑7700K Mac, macOS 13, intermittent loss of WebGL / hardware
   acceleration; cannot run Docker or other heavy local apps) **cannot run
   Google Earth Pro desktop.** Every solution MUST work in the browser.
   **Do not propose, suggest, or rely on the desktop app.**
2. KMZ size is **not** the limiting factor. Earth Web project storage is 1 GB;
   the 23 MB KMZ fit with room to spare. Do not "fix" by shrinking the file
   unless evidence shows size is the cause.
3. **Do not touch the scanner / data pipeline** — it is correct and verified
   (see "What works").

---

## WHAT WORKS — do not break this

The scanner is solid. Leave `trench_data.py`, `fetch.py`, `analyze.py`, and
the scanning logic in `trenches.py` alone unless a data bug is found.

- Scans ~19 trenches + 3 points of interest via the **GMRT GridServer**
  bathymetry API, with a local `cache/` of GeoTIFFs.
- Two-pass scan: coarse grid → high-res zoom. Finds the **deepest point**
  (seeded from both the coarse argmin and the published coordinate) and the
  **steepest cliff** (greatest sustained vertical relief, searched on the
  trench wall around the deepest point).
- Verified correct: Mariana scan lands ~1 km from Challenger Deep at
  ~10,931 m. Data-quality fixes that are correct and must be kept:
  coarse-grid smoothing of narrow deeps (dual-seed refinement), single-cell
  bathymetry artifacts (3×3 median despike), the Diamantina coordinate
  hemisphere typo, and the cliff search wandering onto off-trench seamounts
  (now constrained to a window around the deepest point).
- Findings the user values: Google Earth's own seafloor terrain is coarse and
  *under-represents* Challenger Deep by ~1,500 ft vs GMRT / published surveys.

---

## UNSOLVED ISSUES — Google Earth Web import

When the user imports `output/trench-pins.kmz` into `earth.google.com`, the
project imports in a **degraded mode**. Reproduced repeatedly via screenshots.

- **U1 — UNSOLVED: No folder tree.** The KMZ has 4 `<Folder>`s (Deepest
  Points, Steepest Cliffs & Walls, Trench Outlines, Topo Overlays). Earth Web
  shows the import as a single flat `trench-pins.kmz` item — no expandable,
  clickable sections.
- **U2 — UNSOLVED: Project not auto-titled.** Earth Web creates an "Untitled
  map" instead of titling the project from `<Document><name>`. The user
  reports a prior version *did* auto-title.
- **U3 — UNSOLVED: Pins render as gray plaques.** Deepest/cliff placemarks
  show as semi-opaque gray rectangles, not markers. Confirmed they ARE the
  placemarks: clicking one shows `KML name: Cayman Trench — 7,359 m /
  24,144 ft` (a deepest-pin name). Data is present; rendering is broken.
- **U4 — UNSOLVED: No information on click.** Clicking a feature shows
  `Selected feature —` (blank); the placemark `<description>` HTML (depth in
  m + ft, coordinates, published comparison) does not display.
- **U5 — UNSOLVED: Topo overlays.** The 22 depth-colored contour-map
  `GroundOverlay`s either render as gray boxes or are entangled with the
  degraded import. Their behavior in Earth Web was never cleanly isolated.

**Critical unknown:** the user states — firmly and repeatedly — that an
**earlier version rendered ALL of this correctly in Earth Web** (folder tree,
overlays, topo maps, double-click-to-fly, auto-title, fully online). The
regression point was **never empirically established** this session. If that
claim holds, a specific commit produces a working KMZ and the bug can be
bisected (see "Required next approach").

---

## WHAT THE USER WANTS — target end state

One file the user imports into **Google Earth Web** that delivers:

1. A properly **structured project** with an **auto-generated title**.
2. A **clickable folder tree**: Deepest Points, Steepest Cliffs & Walls,
   Trench Outlines, Topo Overlays.
3. **Real pin markers** for every deepest point and every steepest cliff.
4. Click a pin → an **information popup**: depth in **metres AND feet**,
   coordinates, and the published-deep comparison.
5. Click / double-click → the **camera flies** to that location.
6. The **depth-colored topo-map overlays** (Five Deeps / Victor Vescovo
   cliff-ascent-map style: violet deep → red shallow, white depth contours)
   **visible and correct**.
7. **Fully shareable online** (no desktop app, no downloads required to view).

Earlier explicit feature requests already implemented in the data and to be
preserved: 18 trenches + Sirena Deep; points of interest = Cayman/South-Cuba
Wall (Oriente Scarp), Java Trench Central Deep Wall, Southern Ocean Seamount
(53°41′S 25°05′E); depths shown in feet everywhere; cliffs defined as the
steepest sustained drop.

---

## COMMITS & CHANGES THIS SESSION

`main` branch (current): `4a9055c` → `d9eb302` → `9a3dc53`

| Commit | Summary | Notes |
|--------|---------|-------|
| `4a9055c` | Initial commit: full scanner + KMZ builder + overlays + feet + Sirena Deep | The whole working project (943 lines, 9 files). |
| `d9eb302` | Fix steepest-cliff search wandering onto off-trench seamounts | Good fix — keep. Cliff now searched around the deepest point; land masked. |
| `9a3dc53` | Attempt: fix pins rendering as gray plaques | Removed `http://` icon URLs (mixed-content theory); ASCII document name; smaller overlay images. **DID NOT FIX the Earth Web issues.** |

Orphaned on branch `backup-rolledback-2a94eb3` (rolled back, not on `main`):
`7533d5b` (added icon `<hotSpot>`s), `6a22ac0` (split into two KMZs — wrong),
`2a94eb3` (revert of the split). `main` was hard-reset from `2a94eb3` back to
`d9eb302` mid-session, then `9a3dc53` was added.

Current `output/trench-pins.kmz`: 15 MB, 63 placemarks, 22 GroundOverlays,
4 folders, no `<IconStyle>`, valid XML — and still broken in Earth Web.

---

## THEORIES TRIED THIS SESSION — all unconfirmed or wrong; do NOT just repeat

| Theory | Action taken | Result |
|--------|--------------|--------|
| Earth Web can't render KMZ-embedded GroundOverlays | Split into a pins-only + an overlays KMZ | WRONG — user corrected; reverted |
| KMZ too large (23 MB) | Downscaled overlay images | No effect on the symptoms |
| Icon `<hotSpot>` elements broke it | Rolled back the hotSpot commit | Still broken — not the cause |
| Pin icons used `http://` URLs (mixed content) | Removed external icons → default markers | Still broken — not the (whole) cause |

None of these was established with evidence first. That is the core process
failure (see below).

---

## REQUIRED NEXT APPROACH — empirical bisection, NOT theory

Do **not** guess a cause and ship a change. Establish ground truth first.

1. **Reproduce + capture.** Have the user import the current
   `output/trench-pins.kmz` and confirm the exact symptoms (screenshot).
2. **Minimal baseline.** Build the smallest possible KMZ — ONE placemark, one
   folder, a title, no overlays, no styling. Have the user import it into
   Earth Web. Confirm it imports as a *structured, titled* project. This
   establishes that Earth Web works at all and how a good import looks.
3. **Add one variable at a time** and have the user test each in Earth Web:
   a second folder → more placemarks → a `<description>` with HTML → an
   `<IconStyle>` → a polygon → ONE `GroundOverlay` (embedded image) → many.
   The first build that degrades the import isolates the culprit **with
   evidence**.
4. **Use the git history.** The user insists a prior build worked. Generate
   the KMZ from `4a9055c` (and earlier WIP if recoverable) and from each
   later commit; have the user import each; binary-search last-good →
   first-bad. The user explicitly asked for this ("diff the files").
5. Also test the **import path** in Earth Web itself: "New project → import
   KML" vs adding a layer to a blank map may produce different results
   (titled project vs "Untitled map"). This may be UI behavior, not a file
   bug — confirm before changing code.
6. Only after a cause is **proven** should code change. Then verify with the
   user in Earth Web before committing.

Useful facts: a KMZ is a zip of `doc.kml` + a `files/` folder. simplekml
`savekmz()` builds it. The KML is valid XML (verified). The data is all
present (clicking a gray plaque proves the placemark loaded).

---

## PROCESS FAILURE THIS SESSION — the root cause of this mess

The scanner was built well. Then, when the user reported the Earth Web output
was broken, the session **debugged by theory instead of by evidence**:
guessed a cause, shipped a change, was wrong, repeated — forcing the user
through multiple rollbacks. It also asserted a false platform limitation and
recommended a desktop app the user had already made clear (and memory
recorded) they cannot run.

The fix for the next session is mechanical: **reproduce → diff/bisect →
isolate one variable → prove the cause → only then change code.** Never ship
a speculative fix to something that was working.
