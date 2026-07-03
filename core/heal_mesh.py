#!/usr/bin/env python3
"""
Heal a tactile-map STL into a single print-ready watertight manifold.

The generator emits a *soup* of overlapping closed shells (terrain slab +
hundreds of bumps / digits / braille dots / border ribbons), concatenated
without a boolean union. That soup has: inverted normals on some shells,
internal walls where shells overlap (the print shop's "шупљине"), and
mutual self-intersections.

Fix = boolean UNION of all the closed sub-shells. The union of closed solids
is, by construction, a single watertight manifold whose faces all point
outward and which contains no internal walls.

Two robustness details learned from the data:
  * The soup also contains thousands of degenerate <4-face slivers (from
    coincident overlapping triangles). They carry ~no area and are dropped.
  * Surface features (bumps, digits, braille) sit with their flat bottom
    *coplanar* with the surface they rest on, so a plain union leaves them as
    separate floating bodies. We sink each top-surface body EMBED_MM into
    whatever is beneath it so the union truly fuses them into one solid.
"""
import sys
import time
from pathlib import Path

import numpy as np
import trimesh

EMBED_MM = 0.4        # how deep to sink surface features so the union fuses them.
                      # Kept small: sinking lowers the feature TOP too, and
                      # tactile heights must stay readable. 0.4 mm is the
                      # threshold that reliably fuses every feature (incl. the
                      # legend's flat-plate samples) while leaving braille at
                      # ~0.8 mm (standard braille dots are only ~0.5 mm tall).
BASE_TOP_GUARD = -1.0  # bodies whose lowest point is above this are "surface
                       # features" sitting on top; bodies reaching below it
                       # (terrain slab, border ribbons) already interpenetrate
                       # and must NOT be nudged (would poke out the base).


def prep_body(b, embed):
    """Prep one closed body for boolean union: outward normals, watertight
    (or None), surface features sunk by `embed`, self-intersections declashed."""
    if len(b.faces) < 4:
        return None
    b.merge_vertices()
    trimesh.repair.fix_normals(b)
    if not b.is_watertight:
        trimesh.repair.fill_holes(b)
        trimesh.repair.fix_normals(b)
        if not b.is_watertight:
            return None
    if b.volume < 0:
        b.invert()
    if embed and b.bounds[0][2] > BASE_TOP_GUARD:
        b.apply_translation([0.0, 0.0, -embed])
    from clean_mesh import self_intersects, declash_body
    if self_intersects(b.vertices, b.faces):
        V, F = declash_body(b.vertices, b.faces)
        b2 = trimesh.Trimesh(vertices=V, faces=F, process=True)
        trimesh.repair.fix_normals(b2)
        if b2.is_watertight and len(b2.faces) >= 4:
            if b2.volume < 0:
                b2.invert()
            b = b2
    return b


def load_solids(path, embed_mm=EMBED_MM, declash=True, verbose=True):
    """Return (solids, stats): list of outward, watertight, embedded sub-solids.

    If declash=True, any sub-shell that self-intersects (border ribbons with
    half-mitre "fangs") is repaired BEFORE the union, so the union of clean
    shells stays clean instead of spawning sliver artefacts to chase later.
    """
    m = trimesh.load(str(path), process=True, force='mesh')
    bodies = m.split(only_watertight=False)

    solids = []
    n_tiny = n_open = n_open_repaired = n_declashed = 0
    open_face_total = 0
    for b in bodies:
        if len(b.faces) < 4:
            n_tiny += 1
            continue
        b.merge_vertices()
        trimesh.repair.fix_normals(b)
        if not b.is_watertight:
            # last-ditch hole fill; many "open" bodies are just T-junctions
            trimesh.repair.fill_holes(b)
            trimesh.repair.fix_normals(b)
            if not b.is_watertight:
                n_open += 1
                open_face_total += len(b.faces)
                continue
            n_open_repaired += 1
        if b.volume < 0:
            b.invert()
        # embed surface features so the union fuses them to the base
        if b.bounds[0][2] > BASE_TOP_GUARD:
            b.apply_translation([0.0, 0.0, -embed_mm])
        # repair self-intersecting shells (border-ribbon fangs) before union
        if declash and len(b.faces) > 24:
            from clean_mesh import self_intersects, declash_body
            if self_intersects(b.vertices, b.faces):
                V, F = declash_body(b.vertices, b.faces)
                b2 = trimesh.Trimesh(vertices=V, faces=F, process=True)
                trimesh.repair.fix_normals(b2)
                if b2.is_watertight and len(b2.faces) >= 4:
                    if b2.volume < 0:
                        b2.invert()
                    b = b2
                    n_declashed += 1
        solids.append(b)

    stats = dict(bodies=len(bodies), solids=len(solids), tiny=n_tiny,
                 open_dropped=n_open, open_repaired=n_open_repaired,
                 declashed=n_declashed, open_faces_lost=open_face_total)
    if verbose:
        print(f"  bodies={stats['bodies']} -> solids={stats['solids']} "
              f"(tiny dropped={stats['tiny']}, open repaired={stats['open_repaired']}, "
              f"open dropped={stats['open_dropped']}, declashed={n_declashed})")
    return solids, stats


def union_solids(solids, verbose=True):
    union = trimesh.boolean.union(solids, engine='manifold')
    if isinstance(union, (list, tuple)):
        union = trimesh.util.concatenate(union)
    trimesh.repair.fix_normals(union)
    return union


def heal_union(path_in, path_out, embed_mm=EMBED_MM, verbose=True):
    t0 = time.time()
    if verbose:
        print(f"heal {Path(path_in).name} -> {Path(path_out).name}")
    solids, stats = load_solids(path_in, embed_mm, verbose)
    union = union_solids(solids, verbose)
    Path(path_out).parent.mkdir(parents=True, exist_ok=True)
    union.export(str(path_out))
    if verbose:
        print(f"  -> {len(union.faces)} faces, watertight={union.is_watertight}, "
              f"bodies={len(union.split(only_watertight=False))}, "
              f"vol={union.volume:.0f} mm^3  ({time.time()-t0:.1f}s)")
    return union


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: heal_mesh.py IN.stl OUT.stl [embed_mm]")
        sys.exit(1)
    emb = float(sys.argv[3]) if len(sys.argv) > 3 else EMBED_MM
    heal_union(sys.argv[1], sys.argv[2], emb)
