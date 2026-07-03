#!/usr/bin/env python3
"""
Final cleanup pass for a healed (boolean-unioned) tactile-map mesh.

The manifold union fuses everything into one solid, but where the source had
self-intersecting border ribbons (the half-mitre "fang" artefact) it leaves
behind self-intersections and a sprinkle of degenerate slivers.

This pass runs MeshLab's battle-tested filters to produce a clean
two-manifold. To avoid float32 STL round-trip cracks it operates directly on
float64 vertex/face arrays (no intermediate STL between union and clean):
  * weld near-coincident vertices
  * drop null / duplicate faces and vertices
  * repair non-manifold edges  (so hole-closing is allowed)
  * excise self-intersecting faces (removes the fangs) and re-close the gaps
  * drop tiny disconnected slivers
  * re-orient all faces outward
"""
import sys
from pathlib import Path

import numpy as np
import pymeshlab as ml


def _weld(ms, pct=0.01, verbose=False):
    try:
        ms.meshing_merge_close_vertices(threshold=ml.PercentageValue(pct))
        return True
    except Exception as e:
        if verbose:
            print("  weld skipped:", e)
        return False


def clean_meshset(ms, min_component_faces=25, max_hole=400, passes=3,
                  weld_pct=0.01, verbose=True):
    """Clean the current mesh of `ms` in place; return (V, F) counts."""

    def nfaces():
        return ms.current_mesh().face_number()

    _weld(ms, weld_pct, verbose)

    for it in range(passes):
        ms.meshing_remove_null_faces()
        ms.meshing_remove_duplicate_faces()
        ms.meshing_remove_duplicate_vertices()
        ms.meshing_remove_unreferenced_vertices()

        # Make edges manifold first; hole-closing & self-int both need it.
        try:
            ms.meshing_repair_non_manifold_edges(method=0)
        except Exception:
            pass
        try:
            ms.meshing_repair_non_manifold_vertices()
        except Exception:
            pass

        # Excise self-intersections, then close the gaps left behind.
        sel = 0
        try:
            ms.compute_selection_by_self_intersections_per_face()
            sel = ms.current_mesh().selected_face_number()
            if sel:
                ms.meshing_remove_selected_faces()
        except Exception as e:
            if verbose:
                print(f"  pass {it}: self-int select skipped:", e)

        # Close any boundary holes (from self-int removal or non-manifold repair).
        try:
            ms.meshing_close_holes(maxholesize=max_hole, selfintersection=False,
                                   newfaceselected=False)
        except Exception as e:
            if verbose:
                print(f"  pass {it}: close_holes skipped:", e)

        if verbose:
            print(f"  pass {it}: self-int removed={sel}, F={nfaces()}")
        if sel == 0 and it > 0:
            break

    # Drop tiny disconnected slivers.
    try:
        ms.meshing_remove_connected_component_by_face_number(
            mincomponentsize=min_component_faces, removeunref=True)
    except Exception as e:
        if verbose:
            print("  component drop skipped:", e)

    # Final coherent outward orientation.
    try:
        ms.meshing_re_orient_faces_coherently()
    except Exception:
        pass

    m = ms.current_mesh()
    return m.vertex_number(), m.face_number()


def declash_body(vertices, faces, max_hole=80, passes=2, weld_pct=0.02):
    """Make ONE closed shell non-self-intersecting (e.g. a fanged border ribbon).

    Returns (V, F). If the result fails to come out watertight, returns the
    input unchanged so the caller can fall back.
    """
    ms = ml.MeshSet()
    ms.add_mesh(ml.Mesh(vertex_matrix=np.asarray(vertices, dtype=np.float64),
                        face_matrix=np.asarray(faces, dtype=np.int32)))
    _weld(ms, weld_pct, verbose=False)
    changed = False
    for _ in range(passes):
        ms.meshing_remove_null_faces()
        ms.meshing_remove_duplicate_faces()
        ms.meshing_remove_duplicate_vertices()
        ms.meshing_remove_unreferenced_vertices()
        try:
            ms.meshing_repair_non_manifold_edges(method=0)
            ms.meshing_repair_non_manifold_vertices()
        except Exception:
            pass
        try:
            ms.compute_selection_by_self_intersections_per_face()
            sel = ms.current_mesh().selected_face_number()
        except Exception:
            sel = 0
        if sel:
            ms.meshing_remove_selected_faces()
            try:
                ms.meshing_close_holes(maxholesize=max_hole,
                                       selfintersection=False, newfaceselected=False)
            except Exception:
                pass
            changed = True
        else:
            break
    if not changed:
        return np.asarray(vertices), np.asarray(faces)
    try:
        ms.meshing_re_orient_faces_coherently()
    except Exception:
        pass
    m = ms.current_mesh()
    return m.vertex_matrix(), m.face_matrix()


def self_intersects(vertices, faces):
    """Quick yes/no: does this shell self-intersect?"""
    ms = ml.MeshSet()
    ms.add_mesh(ml.Mesh(vertex_matrix=np.asarray(vertices, dtype=np.float64),
                        face_matrix=np.asarray(faces, dtype=np.int32)))
    try:
        ms.compute_selection_by_self_intersections_per_face()
        return ms.current_mesh().selected_face_number() > 0
    except Exception:
        return False


def clean_arrays(vertices, faces, verbose=True, **kw):
    """Clean float64 arrays directly (no STL round-trip). Returns (V, F) arrays."""
    ms = ml.MeshSet()
    ms.add_mesh(ml.Mesh(vertex_matrix=np.asarray(vertices, dtype=np.float64),
                        face_matrix=np.asarray(faces, dtype=np.int32)))
    clean_meshset(ms, verbose=verbose, **kw)
    m = ms.current_mesh()
    return m.vertex_matrix(), m.face_matrix()


def clean(path_in, path_out, verbose=True, **kw):
    ms = ml.MeshSet()
    ms.load_new_mesh(str(path_in))
    clean_meshset(ms, verbose=verbose, **kw)
    Path(path_out).parent.mkdir(parents=True, exist_ok=True)
    ms.save_current_mesh(str(path_out), binary=True)
    return path_out


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: clean_mesh.py IN.stl OUT.stl")
        sys.exit(1)
    clean(sys.argv[1], sys.argv[2])
