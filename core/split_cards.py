#!/usr/bin/env python3
"""
Split a CLEAN watertight full map into 4 interlocking puzzle cards by boolean
ops (not face-filtering). Each card stays a watertight two-manifold:

  card_i = (full_map  ∩  card_box_i)  ∪  tabs_i  −  slots_i

Puzzle scheme:
  card0 bottom-left, card1 bottom-right, card2 top-left, card3 top-right
  DOVETAIL tabs in the bottom half of the base (z ∈ [-6,-3]); slots are the
  mating trapezoid holes, open at the card bottom. Assembly: lay a card flat,
  lower its neighbour onto the tab from above — the dovetail then blocks any
  sideways pull (2026-08-04; rectangular tabs used to slide apart).
Cards are re-centred to local origin (0,0) on export, matching the originals.
"""
import sys
from pathlib import Path

import numpy as np
import trimesh

from constants import (CARD_WIDTH_MM as CW, CARD_HEIGHT_MM as CH,
                       BASE_THICKNESS_MM)
from generate import create_tab, create_slot_cutter

Z_LO, Z_HI = -BASE_THICKNESS_MM - 1.0, 12.0          # full vertical span + margin

# card_idx -> (origin_x, origin_y) of its 200x160 cell in the full map
ORIGINS = [(0, 0), (CW, 0), (0, CH), (CW, CH)]

# tabs per card, in CARD-LOCAL coords: (x, y, direction)  [from generate.py]
TABS = {
    0: [(CW, CH / 2, 'right'), (CW / 2, CH, 'up')],
    1: [(CW / 2, CH, 'up')],
    2: [(CW, CH / 2, 'right')],
    3: [],
}

# dovetail slots per card, in CARD-LOCAL coords: (x, y, direction) where
# direction is the way the NEIGHBOUR's tab points INTO this card.
# Mirrors TABS: card0.right@(CW,CH/2) -> card1 'right'@(0,CH/2), etc.
SLOTS = {
    0: [],
    1: [(0, CH / 2, 'right')],                       # from card 0
    2: [(CW / 2, 0, 'up')],                          # from card 0
    3: [(0, CH / 2, 'right'), (CW / 2, 0, 'up')],    # from cards 2 and 1
}


def _box(x0, x1, y0, y1, z0, z1):
    ext = [x1 - x0, y1 - y0, z1 - z0]
    b = trimesh.creation.box(extents=ext)
    b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    return b


def split_cards(full_map_path, out_dir, verbose=True):
    # process=True merges the STL's independent triangle vertices back into a
    # shared-vertex watertight volume (required by the boolean engine).
    full = trimesh.load(str(full_map_path), process=True, force='mesh')
    trimesh.repair.fix_normals(full)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for idx, (ox, oy) in enumerate(ORIGINS):
        box = _box(ox, ox + CW, oy, oy + CH, Z_LO, Z_HI)
        card = trimesh.boolean.intersection([full, box], engine='manifold')
        if isinstance(card, (list, tuple)):
            card = trimesh.util.concatenate(card)

        # tabs (local -> global, then union)
        for (lx, ly, d) in TABS[idx]:
            v, f = create_tab(lx, ly, d)
            tab = trimesh.Trimesh(vertices=np.asarray(v, float), faces=np.asarray(f), process=True)
            tab.apply_translation([ox, oy, 0])
            trimesh.repair.fix_normals(tab)
            card = trimesh.boolean.union([card, tab], engine='manifold')

        # dovetail slots (mating holes -> difference). The cutter is the tab
        # grown by the clearance and extended 1 mm past the card edge, so the
        # cut is clean through the wall.
        for (lx, ly, d) in SLOTS[idx]:
            v, f = create_slot_cutter(lx, ly, d)
            cutter = trimesh.Trimesh(vertices=np.asarray(v, float), faces=np.asarray(f), process=True)
            cutter.apply_translation([ox, oy, 0])
            trimesh.repair.fix_normals(cutter)
            card = trimesh.boolean.difference([card, cutter], engine='manifold')

        if isinstance(card, (list, tuple)):
            card = trimesh.util.concatenate(card)
        card.apply_translation([-ox, -oy, 0])        # re-centre to local origin
        trimesh.repair.fix_normals(card)

        out = out_dir / f"card_{idx + 1}.stl"
        card.export(str(out))
        wt = card.is_watertight
        nb = len(card.split(only_watertight=False))
        results.append((out.name, len(card.faces), wt, nb))
        if verbose:
            print(f"  {out.name}: F={len(card.faces)} watertight={wt} bodies={nb}")

    return results


if __name__ == "__main__":
    fm = sys.argv[1] if len(sys.argv) > 1 else "data/output/printready/tactile_map.stl"
    od = sys.argv[2] if len(sys.argv) > 2 else "data/output/printready"
    split_cards(fm, od)
