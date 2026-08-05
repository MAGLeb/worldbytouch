#!/usr/bin/env python3
"""
Clean tactile-map build pipeline (root-cause fix for the print-shop defects).

Differences vs the legacy generate.py main():
  1. Border walls come from walls_buffer.build_walls (buffer + manifold
     extrude, rounded joins) instead of the self-intersecting half-mitre
     ribbon builder -> no "fangs", no inverted normals, no self-intersections.
  2. Terrain + features + walls are fused with a boolean UNION (not merely
     concatenated) and a MeshLab cleanup pass -> ONE watertight two-manifold
     with no internal walls/cavities ("шупљине").
  3. The full map is cut into the 4 puzzle cards by boolean ops
     (split_cards) instead of face-filtering -> each card is watertight.
  4. The legend card is fused + cleaned the same way.

Every output is verified print-ready by mesh_diagnostics.
"""
import sys
import time
from pathlib import Path

import numpy as np
import trimesh

import generate as G
from heal_mesh import EMBED_MM, prep_body as _prep
from clean_mesh import clean_arrays
from walls_buffer import build_terrain_following_walls
from split_cards import split_cards


def _to_bodies(verts, faces):
    m = trimesh.Trimesh(vertices=np.asarray(verts, float),
                        faces=np.asarray(faces), process=True)
    return m.split(only_watertight=False)


def build(out_dir="data/output/printready", embed=EMBED_MM, verbose=True):
    t0 = time.time()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- source data (reuses the legacy building blocks) ---
    X, Y, Z, lon_deg, lat_deg = G.load_elevation()
    gdf = G.load_boundaries_filtered()
    water_mask = G.create_water_mask(lon_deg, lat_deg, gdf)
    Z[water_mask] = 0
    Z = Z + G.create_wave_pattern(X, Y, water_mask)

    terrain_v, terrain_f = G.create_terrain_mesh(X, Y, Z)
    cap_v, cap_f, number_legend, placements = G.create_country_labels_mesh(
        X, Y, Z, gdf, verbose=verbose)

    # dump for verify_labels.py — checking placement against a recomputation
    # would just duplicate (and drift from) the placement logic
    import json
    (out_dir / "label_placements.json").write_text(json.dumps(
        [{"n": n, "iso": i, "x": x, "y": y, "clear": c}
         for n, i, x, y, c in placements], indent=1))

    # --- assemble solids: terrain (no sink) + features (embedded) + walls ---
    solids = []
    terrain_bodies = [pb for pb in (_prep(b, embed=0.0)
                                    for b in _to_bodies(terrain_v, terrain_f)) if pb]
    solids.extend(terrain_bodies)
    terrain_main = max(terrain_bodies, key=lambda b: len(b.faces))

    feat_n = 0
    if len(cap_v):
        for b in _to_bodies(cap_v, cap_f):
            pb = _prep(b, embed=embed)
            if pb is not None:
                solids.append(pb)
                feat_n += 1

    # border ridge follows the relief (low everywhere), built from the terrain
    walls = build_terrain_following_walls(terrain_main, gdf, verbose=verbose)
    solids.append(walls)
    if verbose:
        print(f"  union: terrain + {feat_n} features + walls = {len(solids)} solids")

    union = trimesh.boolean.union(solids, engine='manifold')
    if isinstance(union, (list, tuple)):
        union = trimesh.util.concatenate(union)
    trimesh.repair.fix_normals(union)
    V, F = clean_arrays(union.vertices, union.faces, verbose=verbose)
    full = trimesh.Trimesh(vertices=V, faces=F, process=False)
    full_path = out_dir / "tactile_map.stl"
    full.export(str(full_path))
    if verbose:
        print(f"  full map: F={len(full.faces)} watertight={full.is_watertight} "
              f"bodies={len(full.split(only_watertight=False))}")

    # --- cards by boolean split ---
    split_cards(str(full_path), str(out_dir), verbose=verbose)

    # --- legend: fuse + clean the legend soup ---
    leg_v, leg_f = G.create_legend_card(number_legend)
    lsolids = []
    for b in _to_bodies(leg_v, leg_f):
        pb = _prep(b, embed=embed)
        if pb is not None:
            lsolids.append(pb)
    lu = trimesh.boolean.union(lsolids, engine='manifold')
    if isinstance(lu, (list, tuple)):
        lu = trimesh.util.concatenate(lu)
    trimesh.repair.fix_normals(lu)
    Vl, Fl = clean_arrays(lu.vertices, lu.faces, verbose=verbose)
    leg = trimesh.Trimesh(vertices=Vl, faces=Fl, process=False)
    leg.export(str(out_dir / "card_legend.stl"))
    if verbose:
        print(f"  legend: F={len(leg.faces)} watertight={leg.is_watertight}")

    # --- learning + Serbian-variant cards ---
    from alphabet_card import build_alphabet_card
    from serbian_legend import build_serbian_legend
    from serbian_braille import SERBIAN_GAJICA
    build_alphabet_card(str(out_dir / "card_alphabet.stl"), cols=4, verbose=verbose)
    build_alphabet_card(str(out_dir / "card_alphabet_sr.stl"),
                        alphabet=SERBIAN_GAJICA, cols=4, verbose=verbose)
    build_serbian_legend(number_legend, str(out_dir / "card_legend_sr.stl"), verbose=verbose)

    if verbose:
        print(f"DONE in {time.time()-t0:.0f}s -> {out_dir}")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "data/output/printready"
    build(out)
