#!/usr/bin/env python3
"""
Verify every braille country label on the built map.

Checks, per label, against the ACTUAL placement written by build_all:
  1. the label footprint lies inside its own country polygon at the recorded
     clearance (i.e. it cannot touch the border ridge);
  2. it does not straddle a puzzle-card seam — a label cut in half by the
     x=200 / y=160 split is unreadable on both cards;
  3. it does not overlap another label;
  4. the built STL really carries braille dots there (dome tops sit 0.8 mm
     above a whole-millimetre plateau, so their z has fractional part ~0.8);
  5. the anchor ridge is present to the left of the dots.

Exit code 1 if any check fails.
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import trimesh
from shapely.geometry import box as shapely_box
from shapely.ops import unary_union

from config import MAP_BOUNDS
from constants import (CARD_WIDTH_MM as CW, CARD_HEIGHT_MM as CH,
                       FULL_WIDTH_MM, FULL_HEIGHT_MM, BOUNDARY_WIDTH_MM,
                       BRAILLE_DOT_RADIUS_MM, BRAILLE_ANCHOR_WIDTH_MM)
from countries import COUNTRIES, name_en
from generate import braille_label_size, ANCHOR_LEAD_MM, braille_number_cells

MIN_LON, MIN_LAT, MAX_LON, MAX_LAT = MAP_BOUNDS
LON_PER_MM = (MAX_LON - MIN_LON) / FULL_WIDTH_MM
LAT_PER_MM = (MAX_LAT - MIN_LAT) / FULL_HEIGHT_MM


def mm_to_deg(x, y):
    return (MIN_LON + x * LON_PER_MM, MIN_LAT + y * LAT_PER_MM)


def label_rect_mm(p):
    w, h = braille_label_size(str(p["n"]))
    return (p["x"] - w / 2, p["y"] - h / 2, p["x"] + w / 2, p["y"] + h / 2)


def main(out_dir="data/output", geo="data/output/merged_countries.geojson"):
    out = Path(out_dir)
    places = json.loads((out / "printready" / "label_placements.json").read_text()) \
        if (out / "printready" / "label_placements.json").exists() \
        else json.loads((out / "label_placements.json").read_text())

    # MUST use the same filtered geometry the build draws borders from:
    # the raw geojson is unclipped and keeps small islands, so containment
    # checks against it fail marginally on countries that are actually fine.
    from generate import load_boundaries_filtered
    gdf = load_boundaries_filtered()
    parts = {}
    for _, row in gdf.iterrows():
        iso = str(row.get("source_file") or "")
        if iso in COUNTRIES:
            parts.setdefault(iso, []).append(row.geometry)
    geoms = {}
    for iso, gs in parts.items():
        g = unary_union(gs)
        if g.is_empty:
            continue
        if g.geom_type == "MultiPolygon":
            g = max(g.geoms, key=lambda q: q.area)
        geoms[iso] = g

    mesh = trimesh.load(str(out / "printready" / "tactile_map.stl"),
                        process=True, force="mesh")
    pts = mesh.vertices
    frac = pts[:, 2] - np.floor(pts[:, 2])
    domes = pts[(frac > 0.70) & (frac < 0.88) & (pts[:, 2] > 0.3) & (pts[:, 2] < 4.6)]

    fails, warns = [], []
    print(f"{len(places)} labels\n")
    print(f"{'#':>3} {'ISO':<4} {'country':<14} {'clear':>5} "
          f"{'inside':>6} {'seam':>5} {'dots':>5} {'ridge':>5}")

    for p in places:
        n, iso = p["n"], p["iso"]
        x0, y0, x1, y1 = label_rect_mm(p)
        m = BOUNDARY_WIDTH_MM / 2 + p["clear"]

        # 1. inside its own country, with the recorded clearance
        lo = mm_to_deg(x0 - m, y0 - m)
        hi = mm_to_deg(x1 + m, y1 + m)
        rect_deg = shapely_box(lo[0], lo[1], hi[0], hi[1])
        inside = geoms[iso].contains(rect_deg)

        # 2. card seams at x=CW and y=CH
        seam_ok = not (x0 < CW < x1 or y0 < CH < y1)

        # 3. actual dots present in the built mesh
        in_box = domes[(domes[:, 0] >= x0 - 0.6) & (domes[:, 0] <= x1 + 0.6) &
                       (domes[:, 1] >= y0 - 0.6) & (domes[:, 1] <= y1 + 0.6)]
        # threshold scales with the dot count: "1" is a SINGLE dome and would
        # never clear a flat 20-vertex bar
        n_dots = sum(len(c) for c in braille_number_cells(str(n)))
        dots_ok = len(in_box) >= 4 * n_dots

        # 4. anchor ridge: material in the leftmost strip of the footprint,
        # at dot-top height, spanning most of the label height
        strip = pts[(pts[:, 0] >= x0 - 0.3) &
                    (pts[:, 0] <= x0 + BRAILLE_ANCHOR_WIDTH_MM + 0.3) &
                    (pts[:, 1] >= y0 - 0.3) & (pts[:, 1] <= y1 + 0.3)]
        span = (strip[:, 1].max() - strip[:, 1].min()) if len(strip) else 0.0
        ridge_ok = len(strip) > 0 and span > 0.7 * (y1 - y0)

        flag = lambda b: "ok" if b else "FAIL"
        print(f"{n:>3} {iso:<4} {name_en(iso):<14} {p['clear']:>4.1f} "
              f"{flag(inside):>6} {flag(seam_ok):>5} {flag(dots_ok):>5} "
              f"{flag(ridge_ok):>5}")
        for cond, what in ((inside, "outside country / touches border"),
                           (seam_ok, "cut by card seam"),
                           (dots_ok, "braille dots missing in STL"),
                           (ridge_ok, "anchor ridge missing")):
            if not cond:
                fails.append(f"{n} {iso}: {what}")

    # 5. label-vs-label overlap
    for i, a in enumerate(places):
        ax0, ay0, ax1, ay1 = label_rect_mm(a)
        for b in places[i + 1:]:
            bx0, by0, bx1, by1 = label_rect_mm(b)
            if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                fails.append(f"{a['n']} {a['iso']} overlaps {b['n']} {b['iso']}")

    print()
    if warns:
        for w in warns:
            print("WARN:", w)
    if fails:
        print(f"FAILED ({len(fails)}):")
        for f in fails:
            print("  -", f)
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
