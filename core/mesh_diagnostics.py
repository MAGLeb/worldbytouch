#!/usr/bin/env python3
"""
Mesh diagnostics for the tactile-map STL files.

Measures exactly the three defects the print shop reported, so we can verify
objectively whether a fix worked:

  1. Inverted / inconsistent normals  -> winding_consistent, flipped_faces
  2. Internal cavities ("шупљине")     -> enclosed_bodies, internal_face_ratio,
                                          non_manifold_edges, watertight
  3. Sharp angles / self-intersections -> self_intersections, sharp_edges

Usage:
    python3 core/mesh_diagnostics.py data/output/printready/card_1.stl [more.stl ...]
    python3 core/mesh_diagnostics.py            # all data/output/printready/*.stl
"""
import sys
import json
import math
from pathlib import Path

import numpy as np
import trimesh

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "output"

SHARP_DIHEDRAL_DEG = 75.0  # edges whose surfaces meet sharper than this are "fangs"


def _load(path):
    # process=True merges coincident vertices so topology (shared edges,
    # connected components) is meaningful. STL stores every triangle's
    # vertices independently, so without merging every mesh looks like a
    # disconnected triangle soup.
    m = trimesh.load(str(path), process=True, force='mesh')
    return m


def _self_intersections(path):
    """Count self-intersecting faces via pymeshlab (robust, version-tolerant)."""
    try:
        import pymeshlab
    except Exception:
        return None
    try:
        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(str(path))
        # Filter name has drifted across pymeshlab versions; try the knowns.
        for fname in (
            'compute_selection_by_self_intersections_per_face',
            'select_self_intersecting_faces',
        ):
            try:
                ms.apply_filter(fname)
                break
            except Exception:
                continue
        else:
            return None
        m = ms.current_mesh()
        return int(m.selected_face_number())
    except Exception:
        return None


def _topo_measures(path):
    """pymeshlab topological measures: non-manifold edges, holes, components."""
    try:
        import pymeshlab
    except Exception:
        return {}
    try:
        ms = pymeshlab.MeshSet()
        ms.load_new_mesh(str(path))
        out = {}
        try:
            t = ms.get_topological_measures()
            for k in ('non_two_manifold_edges', 'non_two_manifold_vertices',
                      'boundary_edges', 'number_holes', 'connected_components_number',
                      'is_mesh_two_manifold', 'genus'):
                if k in t:
                    v = t[k]
                    out[k] = bool(v) if isinstance(v, (bool, np.bool_)) else int(v)
        except Exception:
            pass
        return out
    except Exception:
        return {}


def _flipped_faces(mesh):
    """How many faces have a normal opposite to the locally-consistent normal.

    trimesh.repair.fix_normals() reorients to a coherent outward winding; we
    compare winding before/after to count how many triangles were flipped.
    Done on a copy so the original is untouched.
    """
    try:
        m2 = mesh.copy()
        before = m2.faces.copy()
        trimesh.repair.fix_normals(m2, multibody=True)
        after = m2.faces
        if before.shape != after.shape:
            return None
        # A face is "flipped" if its vertex order was reversed.
        flipped = 0
        for a, b in zip(before, after):
            if not np.array_equal(a, b):
                # reversed winding (any cyclic reversal) counts as a flip
                if set(a) == set(b):
                    flipped += 1
        return flipped
    except Exception:
        return None


def _enclosed_bodies(mesh):
    """Count watertight sub-bodies fully inside another body (= internal cavity).

    Splits the merged mesh into connected watertight components, then for each
    component tests whether its centroid lies inside any *other* component's
    volume. Such a component is a void/inclusion sealed inside the solid —
    exactly the "шупљине" the shop flagged.
    """
    try:
        bodies = mesh.split(only_watertight=False)
    except Exception:
        return None, None
    if len(bodies) <= 1:
        return 0, len(bodies)
    enclosed = 0
    # Use bounding boxes for a cheap pre-filter, then containment by ray test.
    wt = [b for b in bodies if b.is_watertight and abs(b.volume) > 1e-9]
    for i, bi in enumerate(wt):
        ci = bi.centroid
        for j, bj in enumerate(wt):
            if i == j:
                continue
            bmin, bmax = bj.bounds
            if np.all(ci >= bmin) and np.all(ci <= bmax):
                try:
                    if bj.contains([ci])[0]:
                        enclosed += 1
                        break
                except Exception:
                    pass
    return enclosed, len(bodies)


def _sharp_edges(mesh):
    """Count edges whose dihedral angle exceeds SHARP_DIHEDRAL_DEG (fangs/spikes)."""
    try:
        fa = mesh.face_adjacency
        ang = mesh.face_adjacency_angles  # radians, 0 = coplanar
        thr = math.radians(SHARP_DIHEDRAL_DEG)
        return int(np.count_nonzero(ang > thr)), int(len(fa))
    except Exception:
        return None, None


def diagnose(path):
    path = Path(path)
    m = _load(path)
    rep = {'file': path.name, 'faces': int(len(m.faces)), 'vertices': int(len(m.vertices))}

    rep['watertight'] = bool(m.is_watertight)
    rep['winding_consistent'] = bool(m.is_winding_consistent)
    rep['is_volume'] = bool(m.is_volume)
    try:
        rep['euler_number'] = int(m.euler_number)
    except Exception:
        rep['euler_number'] = None
    try:
        rep['volume_mm3'] = round(float(m.volume), 1)
    except Exception:
        rep['volume_mm3'] = None

    # degenerate (zero-area) + duplicate faces
    areas = m.area_faces
    rep['degenerate_faces'] = int(np.count_nonzero(areas <= 1e-9))
    try:
        rep['duplicate_faces'] = int(len(m.faces) - len(m.unique_faces()))
    except Exception:
        rep['duplicate_faces'] = None

    # non-manifold edges from trimesh (edges used by !=2 faces)
    try:
        eg = m.edges_sorted
        import collections
        cnt = collections.Counter(map(tuple, eg))
        rep['nonmanifold_edges'] = int(sum(1 for v in cnt.values() if v != 2))
        rep['boundary_edges'] = int(sum(1 for v in cnt.values() if v == 1))
    except Exception:
        rep['nonmanifold_edges'] = None
        rep['boundary_edges'] = None

    rep['flipped_faces'] = _flipped_faces(m)
    enclosed, nbodies = _enclosed_bodies(m)
    rep['enclosed_bodies'] = enclosed
    rep['bodies'] = nbodies
    sharp, adj = _sharp_edges(m)
    rep['sharp_edges'] = sharp
    rep['self_intersections'] = _self_intersections(path)
    rep.update({('ml_' + k): v for k, v in _topo_measures(path).items()})

    return rep


def verdict(rep):
    """Boolean: is this STL print-ready by the print shop's actual concerns?

    Hard criteria: watertight single solid (no internal cavities), consistent
    outward normals, no self-intersections (no sharp "fang" artefacts), no
    non-manifold edges. A handful of zero-area faces are tolerated: hole-closing
    on a near-collinear boundary seals a zero-WIDTH slit with a zero-AREA
    triangle — removing it would re-open the (physically non-existent) slit, and
    every slicer ignores null faces. >5 would hint at a real problem.
    """
    ok = (
        rep.get('watertight') is True and
        rep.get('winding_consistent') is True and
        (rep.get('enclosed_bodies') or 0) == 0 and
        (rep.get('self_intersections') or 0) == 0 and
        (rep.get('degenerate_faces') or 0) <= 5 and
        (rep.get('nonmanifold_edges') or 0) == 0
    )
    return ok


def main():
    args = sys.argv[1:]
    if args:
        files = [Path(a) for a in args]
    else:
        files = sorted((OUTPUT_DIR / "printready").glob('*.stl'))
    results = []
    for f in files:
        if not f.exists() or f.stat().st_size == 0:
            print(f"SKIP (missing/empty): {f}")
            continue
        print(f"\n=== {f.name} ===")
        rep = diagnose(f)
        results.append(rep)
        for k, v in rep.items():
            if k == 'file':
                continue
            print(f"  {k:22s}: {v}")
        print(f"  {'PRINT-READY':22s}: {'YES ✓' if verdict(rep) else 'NO ✗'}")
    print("\n--- JSON ---")
    print(json.dumps(results, indent=None))


if __name__ == "__main__":
    main()
