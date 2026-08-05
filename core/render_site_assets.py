#!/usr/bin/env python3
"""
Build the render half of `site/assets/` from the current print-ready STLs.

The site makes one claim over and over: the photographs are the FIRST PRINT, the
renders are the files as they stand NOW. That only stays true if the renders are
re-made whenever the geometry changes, so every camera the site uses lives here
instead of in a throwaway script.

    python core/render_site_assets.py [printready_dir] [site_assets_dir]

Needs a display (X11) or vtk-osmesa; `xvfb-run -a` works headless.

The photographs in `site/assets/` are NOT produced here. They are hand-picked
crops of `data/photoes/` (gitignored, and two of them are pictures of people):

    hands_map.jpg           photo_1_2026-07-21   hero, hands on the assembled map
    reader.jpg              photo_2_2026-07-21   the friend reading it
    set.jpg                 photo_8_2026-07-21   all six printed pieces
    author.jpg              photo_13_2026-08-05  Gleb beside the wall-mounted map
    first_print_numbers.jpg photo_12_2026-08-05  crop (235, 200)-(765, 597),
                                                 the raised Arabic numerals
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import render_previews as R
from constants import CARD_WIDTH_MM as CW, CARD_HEIGHT_MM as CH

SHOT_SIZE = (1600, 1200)
# the backdrop, as RGB, so the content-crop probe knows what is not the object
BG = tuple(int(R.BG.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))


def _shot(meshes, center, direction, half_h, size=SHOT_SIZE):
    """Orthographic frame: `half_h` IS the visible half-height in mm."""
    p = R._plotter(size)
    for m in meshes:
        R._add(p, m)
    R._light(p)
    R._ssao(p)
    d = np.asarray(direction, float)
    d /= np.linalg.norm(d)
    c = np.asarray(center, float)
    p.enable_parallel_projection()
    p.camera.focal_point = tuple(c)
    p.camera.position = tuple(c + d * 500.0)
    p.camera.up = (0, 0, 1)
    p.camera.parallel_scale = half_h
    img = Image.fromarray(p.screenshot(return_img=True))
    p.close()
    return img


def _content_box(im, tol=7):
    a = np.asarray(im.convert("RGB")).astype(int)
    ys, xs = np.where(np.abs(a - np.array(BG)).max(axis=2) > tol)
    if len(xs) == 0:
        return (0, 0, im.width, im.height)
    return (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)


def _frame_43(box, w, h, pad=0.04):
    """Smallest 4:3 window inside (w, h) that holds `box` plus `pad` margin."""
    x0, y0, x1, y1 = box
    pw, ph = (x1 - x0) * pad, (y1 - y0) * pad
    x0, y0, x1, y1 = x0 - pw, y0 - ph, x1 + pw, y1 + ph
    cw, ch = max(x1 - x0, (y1 - y0) * 4 / 3), max(y1 - y0, (x1 - x0) * 3 / 4)
    cw, ch = min(cw, w), min(ch, h)
    cw, ch = min(cw, ch * 4 / 3), min(ch, cw * 3 / 4)
    cx = min(max((x0 + x1) / 2, cw / 2), w - cw / 2)
    cy = min(max((y0 + y1) / 2, ch / 2), h - ch / 2)
    return tuple(round(v) for v in (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2))


def _save(im, dest, size, quality=86):
    im.convert("RGB").resize(size, Image.LANCZOS).save(
        dest, "JPEG", quality=quality, optimize=True, progressive=True)
    print(f"  {dest.name:24s} {size[0]}x{size[1]}  {dest.stat().st_size // 1024} KB")


def build(src, out, verbose=True):
    src, out = Path(src), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    parts = R.assembled(src)

    def clipped(box):
        ms = [m.clip_box(box, invert=False) for m in parts]
        return [m for m in ms if m.n_points > 0]

    # 1. render_labels.jpg — the right-hand half of the "first print vs current
    #    files" pair. Central Europe and the Balkans, the same corner the
    #    first-print photograph shows, at a scale where a braille number label
    #    reads AS braille: anchor ridge, then cells of domed dots. The frame sits
    #    wholly inside the plate (cy below 253 keeps the north edge out of shot).
    _save(_shot(clipped((20, 240, 175, 320, -7, 8)),
                (120, 250, 1.0), (0.06, -0.38, 0.92), 52.0),
          out / "render_labels.jpg", (1200, 900))

    # 2. render_terrain.jpg — Black Sea, Caucasus, Caspian: stepped plateaus
    #    between two ribbed seas, at a raking angle so every step casts an edge.
    _save(_shot(clipped((188, 292, 188, 266, -7, 8)),
                (240, 227, 1.0), (0.12, -0.58, 0.81), 43.0),
          out / "render_terrain.jpg", (1400, 1050))

    # 3. render_macro.jpg — one label at dome scale, the evidence behind "domes,
    #    not points". The label is found from the geometry (see
    #    render_previews.find_braille_cluster); hand-picked coordinates missed.
    for idx in (3, 1, 2, 4):
        card = R.load(src, f"card_{idx}.stl")
        spot = R.find_braille_cluster(card)
        if spot is not None:
            break
    if spot is None:
        raise SystemExit("no braille cluster found — did the label geometry change?")
    cx, cy = spot
    if verbose:
        print(f"  (braille label found at {cx:.0f}, {cy:.0f} mm)")
    region = card.clip_box((cx - 14, cx + 14, cy - 11, cy + 11, -7, 8), invert=False)
    macro = _shot([region], (cx, cy, 1.2), (0.22, -0.62, 0.75), 8.0)
    _save(macro.crop((40, 285, 1180, 1140)), out / "render_macro.jpg", (1400, 1050))

    # 4/5. the two reference cards, tilted just enough to shade the dots
    for fname, stl in (("render_legend.jpg", "card_legend.stl"),
                       ("render_alphabet.jpg", "card_alphabet.stl")):
        im = _shot([R.load(src, stl)], (CW / 2, CH / 2, 0), (0.10, -0.30, 0.95), 98.0)
        _save(im.crop(_frame_43(_content_box(im), im.width, im.height)),
              out / fname, (1400, 1050), quality=87)

    # 6. render_files.jpg — everything in the download, laid out in two rows
    def eight():
        names = ["card_1.stl", "card_2.stl", "card_3.stl", "card_4.stl",
                 "card_legend.stl", "card_legend_sr.stl",
                 "card_alphabet.stl", "card_alphabet_sr.stl"]
        ms = []
        for i, n in enumerate(names):
            m = R.load(src, n)
            m.translate(((i % 4) * (CW + 18), -(i // 4) * (CH + 18), 0), inplace=True)
            ms.append(m)
        return ms
    im = _shot(eight(),
               (3 * (CW + 18) / 2 + CW / 2, -(CH + 18) / 2 + CH / 2, 0),
               (0.14, -0.46, 0.88), 335.0)
    _save(im.crop(_frame_43(_content_box(im), im.width, im.height)),
          out / "render_files.jpg", (1400, 1050))

    if verbose:
        print(f"-> 6 site renders in {out}/")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "data/output/printready",
          sys.argv[2] if len(sys.argv) > 2 else "site/assets")
