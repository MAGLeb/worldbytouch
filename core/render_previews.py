#!/usr/bin/env python3
"""
Render preview images of the CURRENT print-ready STLs into
data/output/previews_v2/.

Needed because every image in the repo (assets/*.jpg renders and previews/)
predates the v2 geometry rebuild — braille number labels, dome braille dots and
dovetail tabs are not visible anywhere. These renders show what the published
files actually produce; the real printed photo stays the gallery cover.

Off-screen rendering via pyvista/VTK; needs a display (X11) or vtk-osmesa.
"""
import sys
from pathlib import Path

import numpy as np
import pyvista as pv

from constants import CARD_WIDTH_MM as CW, CARD_HEIGHT_MM as CH

PLA = "#d8cfc0"          # neutral warm filament tone
BG = "#f4f2ee"
SIZE_43 = (1600, 1200)
SIZE_34 = (1200, 1600)

# card index -> (origin_x, origin_y) in the assembled map
ORIGINS = [(0, 0), (CW, 0), (0, CH), (CW, CH)]


def _plotter(size, zoom=None):
    # lighting='none': the default light kit washes the relief out completely
    # (matte PLA + shallow 0.8-3 mm features need raking light, not flood).
    p = pv.Plotter(off_screen=True, window_size=size, lighting='none')
    p.set_background(BG)
    p.enable_anti_aliasing("ssaa")
    return p


def _add(p, mesh, color=PLA):
    # matte, PLA-like: almost no specular, so shape reads through shading only
    p.add_mesh(mesh, color=color, smooth_shading=False,
               specular=0.05, specular_power=8, ambient=0.30, diffuse=0.88)


def _light(p):
    # key: off-axis but still facing the surface — raking enough to shadow the
    # braille domes and terrain steps, bright enough to keep PLA looking light
    p.add_light(pv.Light(position=(-0.45, 0.30, 0.80), light_type='cameralight',
                         intensity=1.05))
    # fill: opposite side, weak, keeps the shadow sides from going black
    p.add_light(pv.Light(position=(0.65, -0.35, 0.45), light_type='cameralight',
                         intensity=0.35))


def load(src, name):
    return pv.read(str(Path(src) / name))


def find_braille_cluster(mesh, cell=9.0, min_hits=40):
    """(x, y) of the densest braille label on a card, derived from geometry.

    Braille domes are the only feature whose top sits 0.8 mm above a terrain
    plateau, and plateaus are quantised to whole millimetres — so dome-top
    vertices are the ones whose z has a fractional part near 0.8. Border ridges
    (+1.2 -> .2), capital bumps (+2.0 -> .0) and the terrain itself (.0) do not
    collide with that band. Cluster those vertices on a coarse grid and take
    the fullest cell.
    """
    z = mesh.points[:, 2]
    frac = z - np.floor(z)
    hit = mesh.points[(frac > 0.70) & (frac < 0.88) & (z > 0.3) & (z < 4.6)]
    if len(hit) < min_hits:
        return None
    keys = np.floor(hit[:, :2] / cell).astype(int)
    uniq, counts = np.unique(keys, axis=0, return_counts=True)
    if counts.max() < min_hits:
        return None
    best = uniq[counts.argmax()]
    sel = hit[(keys[:, 0] == best[0]) & (keys[:, 1] == best[1])]
    return float(sel[:, 0].mean()), float(sel[:, 1].mean())


def assembled(src):
    """The four cards snapped together, in map position."""
    parts = []
    for i, (ox, oy) in enumerate(ORIGINS):
        m = load(src, f"card_{i + 1}.stl")
        m.translate((ox, oy, 0), inplace=True)
        parts.append(m)
    return parts


def render(src, out_dir, verbose=True):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    made = []

    def shot(fname, size, build, cpos=None, zoom=None, view=None):
        p = _plotter(size)
        build(p)
        _light(p)
        if view:
            # Deterministic orthographic framing: parallel_scale IS the visible
            # half-height in mm, so the crop is exact. reset_camera()+zoom kept
            # throwing close-ups out of frame.
            center, direction, half_h = view
            d = np.asarray(direction, float)
            d /= np.linalg.norm(d)
            c = np.asarray(center, float)
            p.enable_parallel_projection()
            p.camera.focal_point = tuple(c)
            p.camera.position = tuple(c + d * 400.0)
            p.camera.up = (0, 0, 1)
            p.camera.parallel_scale = half_h
        elif cpos:
            p.camera_position = cpos
            if zoom:
                p.camera.zoom(zoom)
        else:
            p.view_isometric()
            if zoom:
                p.camera.zoom(zoom)
        f = out / fname
        p.screenshot(str(f))
        p.close()
        made.append(fname)
        if verbose:
            print(f"  {fname}")

    parts = assembled(src)

    # 1. assembled map, 3/4 view — the hero shot
    shot("01_assembled_iso.png", SIZE_43,
         lambda p: [_add(p, m) for m in parts], zoom=1.35)

    # 2. assembled map, near-top view (slight tilt so the relief still shades)
    shot("02_assembled_top.png", SIZE_43,
         lambda p: [_add(p, m) for m in parts],
         view=((CW, CH, 1), (0.06, -0.26, 0.96), 172.0))

    # 3. vertical cover (3:4, prioritised in the app): low 3/4 angle puts the
    # landscape map on a diagonal so it actually fills a portrait frame
    shot("03_assembled_portrait.png", SIZE_34,
         lambda p: [_add(p, m) for m in parts],
         view=((CW, CH, 1), (0.52, -0.76, 0.38), 178.0))

    # 4. macro: a braille number label on the map, found from the geometry
    # rather than guessed — hand-picked camera coordinates missed every time.
    for idx in (3, 1, 2, 4):
        card = load(src, f"card_{idx}.stl")
        spot = find_braille_cluster(card)
        if spot is not None:
            break
    if spot is not None:
        cx, cy = spot
        region = card.clip_box((cx - 24, cx + 24, cy - 20, cy + 20, -7, 8),
                               invert=False)
        shot("04_braille_macro.png", SIZE_43,
             lambda p: _add(p, region),
             view=((cx, cy, 1.5), (0.30, -0.80, 0.52), 13.0))
        if verbose:
            print(f"     (braille label found at {cx:.0f}, {cy:.0f} mm)")

    # 5. dovetail joint: the tab of card 1 and the mating slot of card 2,
    # cropped to the joint and viewed from slightly BELOW — the dovetail lives
    # in the bottom half of the base (z -6..-3) and is invisible from above.
    a = load(src, "card_1.stl").clip_box((170, 206, 56, 104, -7, 1), invert=False)
    b = load(src, "card_2.stl").clip_box((0, 30, 56, 104, -7, 1), invert=False)
    b.translate((CW + 22, 0, 0), inplace=True)
    # flip both underside-up: the dovetail sits at z -6..-3 and is invisible
    # from above; shooting from below leaves it unlit and unreadable.
    for m in (a, b):
        m.rotate_x(180, point=(CW, 80, -3), inplace=True)
    shot("05_dovetail_joint.png", SIZE_43,
         lambda p: [_add(p, a), _add(p, b)],
         view=((CW + 11, 80, -3), (0.28, -0.78, 0.56), 33.0))

    # 6/7. the reference cards, whole and slightly tilted so the dots shade
    for fname, stl in (("06_legend_en.png", "card_legend.stl"),
                       ("07_alphabet_en.png", "card_alphabet.stl")):
        shot(fname, SIZE_43,
             lambda p, s=stl: _add(p, load(src, s)),
             view=((CW / 2, CH / 2, 0), (0.16, -0.42, 0.89), 88.0))

    # 8. everything that is in the download, laid out
    def all_eight(p):
        names = ["card_1.stl", "card_2.stl", "card_3.stl", "card_4.stl",
                 "card_legend.stl", "card_legend_sr.stl",
                 "card_alphabet.stl", "card_alphabet_sr.stl"]
        for i, n in enumerate(names):
            m = load(src, n)
            col, row = i % 4, i // 4
            m.translate((col * (CW + 18), -row * (CH + 18), 0), inplace=True)
            _add(p, m)
    shot("08_all_files.png", SIZE_43, all_eight,
         view=((3 * (CW + 18) / 2 + CW / 2, -(CH + 18) / 2 + CH / 2, 0),
               (0.14, -0.46, 0.88), 335.0))

    if verbose:
        print(f"-> {len(made)} renders in {out}/")
    return made


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data/output/printready"
    out = sys.argv[2] if len(sys.argv) > 2 else "data/output/previews_v2"
    render(src, out)
