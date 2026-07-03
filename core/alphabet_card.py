#!/usr/bin/env python3
"""
Braille alphabet learning card: for every letter, the raised Latin letter next
to its Braille cell, so a learner can map print <-> Braille and read in future.
Works for any alphabet passed as [(display_glyph, dot_tuple), ...] — English
a-z by default, or Serbian Gajica (30 letters incl. Č Ć Dž Đ Lj Nj Š Ž).

Standalone reference card (200x160 mm), same clean pipeline as the map: fuse
all features into one watertight, print-ready manifold.
"""
import sys
import math
import string
from pathlib import Path

import numpy as np
import trimesh

from constants import CARD_WIDTH_MM as W, CARD_HEIGHT_MM as H, BASE_THICKNESS_MM
from generate import create_braille_dot, BRAILLE
from text_mesh import build_text
from heal_mesh import EMBED_MM, prep_body as _prep
from clean_mesh import clean_arrays

LETTER_MM = 11.0           # Latin cap height
LETTER_THICK = 1.5
BRAILLE_CW, BRAILLE_CH = 4.0, 6.0
LETTER_GAP = 4.0           # mm between letter and its braille cell


def braille_cell(dots, x, y, z, cw=BRAILLE_CW, ch=BRAILLE_CH):
    """Braille dots for an explicit dot tuple (1-6). Positions:  1 4 / 2 5 / 3 6."""
    pos = {1: (0, ch * 2 / 3), 2: (0, ch / 3), 3: (0, 0),
           4: (cw * 0.6, ch * 2 / 3), 5: (cw * 0.6, ch / 3), 6: (cw * 0.6, 0)}
    vs, fs, off = [], [], 0
    for d in dots:
        dx, dy = pos[d]
        v, f = create_braille_dot(x + dx, y + dy, z)
        vs.append(v)
        fs.append(f + off)
        off += len(v)
    if vs:
        return np.vstack(vs), np.vstack(fs)
    return np.array([]), np.array([])


def _tm(v, f):
    return trimesh.Trimesh(vertices=np.asarray(v, float), faces=np.asarray(f), process=True)


def build_alphabet_card(out_path, alphabet=None, cols=4, embed=EMBED_MM, verbose=True):
    if alphabet is None:
        alphabet = [(ch.upper(), BRAILLE[ch]) for ch in string.ascii_lowercase]
    rows = math.ceil(len(alphabet) / cols)

    base = trimesh.creation.box(extents=[W, H, BASE_THICKNESS_MM])
    base.apply_translation([W / 2, H / 2, -BASE_THICKNESS_MM / 2])  # top at z=0
    solids = [base]

    col_w = W / cols
    top_margin, bottom_margin = 12, 12
    row_h = (H - top_margin - bottom_margin) / max(1, rows - 1)
    start_y = H - top_margin

    for i, (disp, dots) in enumerate(alphabet):
        col, row = i % cols, i // cols
        cx = col * col_w + 5
        cy = start_y - row * row_h

        L = build_text(disp, size=LETTER_MM, thickness=LETTER_THICK,
                       origin=(cx, cy - LETTER_MM / 2))
        solids.append(L)

        # braille cell placed just past the letter's right edge
        bx = L.bounds[1][0] + LETTER_GAP
        bv, bf = braille_cell(dots, bx, cy - BRAILLE_CH / 2, 0)
        if len(bv):
            solids.append(_tm(bv, bf))

    if verbose:
        print(f"  alphabet card: {len(alphabet)} letters, {cols}x{rows} grid, "
              f"{len(solids)} primitives")

    prepped = []
    for k, b in enumerate(solids):
        pb = _prep(b, embed=0.0 if k == 0 else embed)  # don't sink the plate
        if pb is not None:
            prepped.append(pb)

    union = trimesh.boolean.union(prepped, engine='manifold')
    if isinstance(union, (list, tuple)):
        union = trimesh.util.concatenate(union)
    trimesh.repair.fix_normals(union)
    V, F = clean_arrays(union.vertices, union.faces, verbose=verbose)
    out = trimesh.Trimesh(vertices=V, faces=F, process=False)
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    out.export(str(out_path))
    if verbose:
        print(f"  -> {out_path}: F={len(out.faces)} watertight={out.is_watertight} "
              f"bodies={len(out.split(only_watertight=False))}")
    return out


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    if lang == "sr":
        from serbian_braille import SERBIAN_GAJICA
        build_alphabet_card("data/output/printready/card_alphabet_sr.stl",
                            alphabet=SERBIAN_GAJICA, cols=4)
    else:
        build_alphabet_card("data/output/printready/card_alphabet.stl", cols=4)
