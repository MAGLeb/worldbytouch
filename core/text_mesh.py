#!/usr/bin/env python3
"""
Raised Latin text as a clean watertight manifold.

Glyph outlines come from a font (matplotlib TextPath) -> shapely-style polygon
rings -> manifold3d CrossSection (Clipper2, EvenOdd handles the holes in A/O/B)
-> extrude. Same robust pipeline as the border walls, so letters come out
watertight and self-intersection-free.
"""
import numpy as np
import trimesh
import manifold3d as m3
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

from walls_buffer import manifold_to_trimesh

_FONT = FontProperties(family="DejaVu Sans", weight="bold")


def text_contours(s, size):
    tp = TextPath((0, 0), s, size=size, prop=_FONT)
    return [np.asarray(p, dtype=float) for p in tp.to_polygons() if len(p) >= 3]


def text_bounds(s, size):
    cs = text_contours(s, size)
    if not cs:
        return (0.0, 0.0, 0.0, 0.0)
    allp = np.vstack(cs)
    return (allp[:, 0].min(), allp[:, 1].min(), allp[:, 0].max(), allp[:, 1].max())


def build_text(s, size=10.0, thickness=1.5, z0=0.0, origin=None):
    """Raised text mesh. `size` ~ cap height in mm. If origin=(x,y) is given the
    text's bottom-left bbox corner is placed there (else left on the baseline)."""
    contours = text_contours(s, size)
    if not contours:
        return trimesh.Trimesh()
    cs = m3.CrossSection(contours, fillrule=m3.FillRule.EvenOdd)
    man = cs.extrude(thickness)
    m = manifold_to_trimesh(man)
    if origin is not None:
        lo = m.bounds[0]
        m.apply_translation([origin[0] - lo[0], origin[1] - lo[1], z0 - lo[2]])
    else:
        m.apply_translation([0, 0, z0])
    trimesh.repair.fix_normals(m)
    return m


if __name__ == "__main__":
    import pymeshlab as ml

    def si(v, f):
        ms = ml.MeshSet()
        ms.add_mesh(ml.Mesh(vertex_matrix=np.asarray(v, float),
                            face_matrix=np.asarray(f, np.int32)))
        ms.compute_selection_by_self_intersections_per_face()
        return ms.current_mesh().selected_face_number()

    for s in ["A", "O", "B", "ABO"]:
        m = build_text(s, size=10, thickness=1.5)
        print(f"{s!r}: faces={len(m.faces)} watertight={m.is_watertight} "
              f"self-int={si(m.vertices, m.faces)} bounds={np.round(m.bounds,1).tolist()}")
