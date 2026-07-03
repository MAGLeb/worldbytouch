#!/usr/bin/env python3
"""
Clean border walls via 2-D buffer + extrusion (replaces the self-intersecting
half-mitre ribbon builder).

Why this is the root-cause fix for the print shop's complaints #1 (inverted
normals / "many sharp angles") and the residual self-intersections:

  * The old `_build_ribbon_solid` offset each polyline by hand. At sharp convex
    corners the left/right offsets cross over -> self-intersecting "fangs"
    (the code's own comment flags this as #4.7.2). 580 such ribbons also
    overlap each other at country tri-points, so their union spawns slivers.

  * Here every border line is thickened with shapely's `buffer()` using ROUND
    joins, then ALL of them are dissolved with `unary_union` into one planar
    multipolygon — no self-intersections, overlaps merged, corners rounded
    (no fangs). Extruding that planar region gives clean watertight prisms.

The wall footprint (deg->mm) is identical to the generator, so these walls
drop straight onto the existing terrain.
"""
import numpy as np
import trimesh
import manifold3d as m3
from shapely.geometry import box as shbox, LineString
from shapely.ops import unary_union

from config import MAP_BOUNDS
from constants import (BOUNDARY_WIDTH_MM, RIBBON_BOTTOM_Z, RIBBON_TOP_Z,
                       BOUNDARY_RELIEF_MM)
from generate import load_boundaries_filtered, deg_to_mm, _extract_linestrings


def manifold_to_trimesh(man):
    # manifold3d already emits a perfectly welded indexed mesh; trimesh's
    # process=True re-merges vertices at a coarse tolerance and FRACTURES it
    # (watertight->False). Keep process=False.
    mesh = man.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].copy()
    f = np.asarray(mesh.tri_verts).copy()
    return trimesh.Trimesh(vertices=v, faces=f, process=False)


def _rings(poly):
    """All rings (exterior + holes) of a shapely Polygon as Nx2 arrays."""
    out = [np.asarray(poly.exterior.coords)[:-1]]
    for r in poly.interiors:
        out.append(np.asarray(r.coords)[:-1])
    return out


def _boundary_lines_deg(gdf):
    """Replicate the generator's unified border skeleton (lines in degrees)."""
    polys = [g for g in gdf.geometry.tolist() if g is not None and not g.is_empty]
    all_lines = []
    for poly in polys:
        parts = [poly] if poly.geom_type == 'Polygon' else (
            list(poly.geoms) if poly.geom_type == 'MultiPolygon' else [])
        for p in parts:
            b = p.boundary
            if b.geom_type == 'LineString':
                all_lines.append(b)
            elif b.geom_type == 'MultiLineString':
                all_lines.extend(b.geoms)
    if not all_lines:
        return []
    boundary = unary_union(all_lines)

    # drop the rectangular clip-frame edges (5/70/12/55 deg)
    eps = 1e-3
    interior = shbox(MAP_BOUNDS[0] + eps, MAP_BOUNDS[1] + eps,
                     MAP_BOUNDS[2] - eps, MAP_BOUNDS[3] - eps)
    boundary = boundary.intersection(interior)

    lines = _extract_linestrings(boundary)
    return [ln.simplify(0.15, preserve_topology=True) for ln in lines]


def build_walls(gdf=None, width=BOUNDARY_WIDTH_MM,
                z_bottom=RIBBON_BOTTOM_Z, z_top=RIBBON_TOP_Z,
                quad_segs=6, verbose=True):
    """Return one trimesh of all border walls (clean, watertight prisms)."""
    if gdf is None:
        gdf = load_boundaries_filtered()
    lines_deg = _boundary_lines_deg(gdf)
    if verbose:
        print(f"  wall lines: {len(lines_deg)}")

    # Thicken each line in mm-space with round joins, then dissolve overlaps.
    buffers = []
    for ln in lines_deg:
        coords_mm = [deg_to_mm(lon, lat) for lon, lat in ln.coords]
        if len(coords_mm) < 2:
            continue
        strip = LineString(coords_mm).buffer(
            width / 2.0, cap_style=1, join_style=1, quad_segs=quad_segs)
        if not strip.is_empty:
            buffers.append(strip)
    if not buffers:
        return trimesh.Trimesh()

    merged = unary_union(buffers)  # one (multi)polygon, no self-intersections
    polys = list(merged.geoms) if merged.geom_type == 'MultiPolygon' else [merged]
    if verbose:
        print(f"  dissolved into {len(polys)} wall polygon(s)")

    # Feed every ring to a single Clipper2-backed CrossSection (EvenOdd handles
    # holes regardless of ring orientation) and extrude once -> one clean,
    # self-intersection-free watertight manifold.
    contours = []
    for poly in polys:
        if poly.is_empty or poly.area < 1e-6:
            continue
        contours.extend(_rings(poly))

    cs = m3.CrossSection(contours, fillrule=m3.FillRule.EvenOdd)
    man = cs.extrude(z_top - z_bottom)
    walls = manifold_to_trimesh(man)
    walls.apply_translation([0, 0, z_bottom])
    trimesh.repair.fix_normals(walls)
    if verbose:
        print(f"  walls: {len(walls.faces)} faces, "
              f"bodies={len(walls.split(only_watertight=False))}, "
              f"watertight={walls.is_watertight}")
    return walls


def build_terrain_following_walls(terrain, gdf=None, relief_h=BOUNDARY_RELIEF_MM,
                                  width=BOUNDARY_WIDTH_MM, verbose=True):
    """Border ridge that follows the relief: a thin strip raised `relief_h` mm
    above the LOCAL terrain everywhere (not a flat absolute plane).

    Built as: (border footprint extruded into tall columns) ∩ (terrain raised
    by relief_h). The intersection caps each column at terrain+relief_h on top
    and clips it to the terrain footprint — so over lowland the border is a low
    ridge instead of a tall wall, and stray walls beyond the plate vanish.
    """
    lo, hi = terrain.bounds
    columns = build_walls(gdf=gdf, width=width,
                          z_bottom=lo[2] - 1.0, z_top=hi[2] + relief_h + 1.0,
                          verbose=verbose)
    raised = terrain.copy()
    raised.apply_translation([0, 0, relief_h])
    trimesh.repair.fix_normals(raised)
    ridge = trimesh.boolean.intersection([columns, raised], engine='manifold')
    if isinstance(ridge, (list, tuple)):
        ridge = trimesh.util.concatenate(ridge)
    trimesh.repair.fix_normals(ridge)
    if verbose:
        print(f"  terrain-following walls: {len(ridge.faces)} faces, "
              f"+{relief_h} mm over local relief, watertight={ridge.is_watertight}")
    return ridge


if __name__ == "__main__":
    w = build_walls()
    w.export("data/output/_walls_test.stl")
    print("saved data/output/_walls_test.stl")
