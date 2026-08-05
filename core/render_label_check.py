#!/usr/bin/env python3
"""
Contact sheet of every braille country label, for eyeballing how the label
actually sits inside its country.

verify_labels.py proves the footprint is geometrically inside the polygon at
the recorded clearance; this shows whether it LOOKS right — crowded against a
border, sitting on a terrain step, colliding with sea hatching.

Writes data/output/previews_v2/label_check.png (and one tile per label).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pyvista as pv
from PIL import Image, ImageDraw

from countries import name_en
from render_previews import _plotter, _add, _light

TILE = (460, 360)
HALF_MM = 11.5          # visible half-height around the label
COLS = 5


def render(out_dir="data/output", verbose=True):
    out = Path(out_dir)
    places = json.loads((out / "printready" / "label_placements.json").read_text())
    dst = out / "previews_v2"
    dst.mkdir(parents=True, exist_ok=True)

    full = pv.read(str(out / "printready" / "tactile_map.stl"))
    tiles = []

    for p in places:
        x, y = p["x"], p["y"]
        region = full.clip_box((x - 20, x + 20, y - 15, y + 15, -7, 9),
                               invert=False)
        pl = _plotter(TILE)
        _add(pl, region)
        _light(pl)
        d = np.array([0.10, -0.30, 0.95], float)   # near top-down: judge placement, not relief
        d /= np.linalg.norm(d)
        c = np.array([x, y, 1.5], float)
        pl.enable_parallel_projection()
        pl.camera.focal_point = tuple(c)
        pl.camera.position = tuple(c + d * 400.0)
        pl.camera.up = (0, 0, 1)
        pl.camera.parallel_scale = HALF_MM
        f = dst / f"label_{p['n']:02d}_{p['iso']}.png"
        pl.screenshot(str(f))
        pl.close()
        tiles.append((f, p))
        if verbose:
            print(f"  {p['n']:2d} {p['iso']}")

    rows = (len(tiles) + COLS - 1) // COLS
    sheet = Image.new("RGB", (COLS * TILE[0], rows * (TILE[1] + 24)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (f, p) in enumerate(tiles):
        col, row = i % COLS, i // COLS
        ox, oy = col * TILE[0], row * (TILE[1] + 24)
        sheet.paste(Image.open(f), (ox, oy))
        draw.text((ox + 8, oy + TILE[1] + 6),
                  f"{p['n']}. {p['iso']} {name_en(p['iso'])}  "
                  f"clear {p['clear']:.1f} mm", fill="black")
    sheet_path = dst / "label_check.png"
    sheet.save(sheet_path)
    if verbose:
        print(f"-> {sheet_path}")
    return sheet_path


if __name__ == "__main__":
    render(*sys.argv[1:])
