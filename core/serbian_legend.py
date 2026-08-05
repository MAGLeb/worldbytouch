#!/usr/bin/env python3
"""
Serbian legend card: number -> Serbian country name in Serbian Latin Braille,
plus the texture samples (sea / border / city) with Serbian labels. Same clean
fuse-and-verify pipeline as the rest; one watertight print-ready manifold.
"""
from pathlib import Path

import numpy as np
import trimesh

from constants import (CARD_WIDTH_MM as W, CARD_HEIGHT_MM as H, BASE_THICKNESS_MM,
                       WAVE_HEIGHT_MM, BOUNDARY_RELIEF_MM, BOUNDARY_WIDTH_MM,
                       BRAILLE_CELL_PITCH_MM)
from generate import (create_segment_box, create_braille_anchor,
                      create_braille_cell_dots, braille_number_cells,
                      ANCHOR_LEAD_MM)
from constants import BRAILLE_DOT_RADIUS_MM, BRAILLE_DOT_PITCH_MM
from heal_mesh import EMBED_MM, prep_body as _prep
from clean_mesh import clean_arrays
from serbian_braille import tokenize, SERBIAN_DOTS
from countries import name_sr


def serbian_braille_text(text, x, y, z, max_graphemes=12):
    """Serbian Latin string -> braille dots (digraphs = 1 cell), standard
    Marburg cell pitch. (V, F)."""
    vs, fs, off, cx = [], [], 0, x
    for tok in tokenize(text)[:max_graphemes]:
        if tok == ' ':
            cx += BRAILLE_CELL_PITCH_MM
            continue
        dots = SERBIAN_DOTS.get(tok)
        if dots:
            v, f = create_braille_cell_dots(dots, cx, y, z)
            if len(v):
                vs.append(v)
                fs.append(f + off)
                off += len(v)
        cx += BRAILLE_CELL_PITCH_MM
    if vs:
        return np.vstack(vs), np.vstack(fs)
    return np.array([]), np.array([])


def build_serbian_legend(number_legend, out_path, embed=EMBED_MM, verbose=True):
    # Collect every primitive into ONE concatenated soup, then split into bodies.
    # Welding shared vertices across the soup (process=True) before the union
    # avoids the self-intersection storm that unioning hundreds of separate
    # overlapping wave-segment boxes produces.
    soup_v, soup_f, voff = [], [], 0

    def add(v, f):
        nonlocal voff
        if len(v):
            soup_v.append(np.asarray(v, dtype=float))
            soup_f.append(np.asarray(f) + voff)
            voff += len(v)

    base = trimesh.creation.box(extents=[W, H, BASE_THICKNESS_MM])
    base.apply_translation([W / 2, H / 2, -BASE_THICKNESS_MM / 2])
    add(base.vertices, base.faces)

    # 2 columns, braille number key + braille country name, standard Marburg
    # pitch (2026-08-04: keys match the braille labels on the map). Same
    # layout as the English legend in generate.create_legend_card.
    cols = 2
    rows = max(1, int(np.ceil(len(number_legend) / cols)))
    col_w = W / cols
    start_y = H - 16
    row_pitch = (start_y - 22) / max(1, rows - 1) if rows > 1 else 0

    for idx, (num, iso) in enumerate(number_legend):
        col, row = idx // rows, idx % rows
        x = col * col_w + 4
        y = start_y - row * row_pitch
        for i, dots in enumerate(braille_number_cells(str(num))):
            add(*create_braille_cell_dots(dots, x + i * BRAILLE_CELL_PITCH_MM, y, 0))
        name = name_sr(iso) or iso
        bv, bf = serbian_braille_text(name, x + 14, y, 0)
        add(bv, bf)

    # texture samples: one bottom strip, Serbian label to the RIGHT of each
    sample_y, sample_h, sample_w = 6, 10, 25
    label_y = sample_y + 1
    # sea (waves) -> "more"
    for wi in range(3):
        by = sample_y + wi * 3.5
        for s in range(20):
            x1 = 10 + s * (sample_w / 20)
            x2 = 10 + (s + 1) * (sample_w / 20)
            y1 = by + 0.8 * np.sin(s * 2 * np.pi / 5)
            y2 = by + 0.8 * np.sin((s + 1) * 2 * np.pi / 5)
            add(*create_segment_box(x1, y1, x2, y2, 0, WAVE_HEIGHT_MM, 0.8))
    add(*serbian_braille_text("more", 10 + sample_w + 3, label_y, 0))
    # border -> "granica"
    add(*create_segment_box(78, sample_y, 78,
                            sample_y + sample_h, 0, BOUNDARY_RELIEF_MM, BOUNDARY_WIDTH_MM))
    add(*serbian_braille_text("granica", 83, label_y, 0))
    # anchor ridge + one cell -> "broj" (number key); capital bumps were
    # removed from the map 2026-08-05, so the old "grad" sample went too
    key_x = 150
    add(*create_braille_anchor(key_x, sample_y + sample_h / 2, 0))
    add(*create_braille_cell_dots(
        (1, 2, 3), key_x + ANCHOR_LEAD_MM + BRAILLE_DOT_RADIUS_MM,
        sample_y + sample_h / 2 - BRAILLE_DOT_PITCH_MM, 0))
    add(*serbian_braille_text("broj", key_x + 14, label_y, 0))

    soup = trimesh.Trimesh(vertices=np.vstack(soup_v), faces=np.vstack(soup_f),
                           process=True)
    bodies = soup.split(only_watertight=False)
    if verbose:
        print(f"  serbian legend: {len(number_legend)} countries, {len(bodies)} bodies")

    # _prep embeds only surface features (min_z > -1); the base slab (min_z=-6)
    # is left in place automatically.
    prepped = [pb for b in bodies if (pb := _prep(b, embed=embed)) is not None]
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
