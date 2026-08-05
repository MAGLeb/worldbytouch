#!/usr/bin/env python3
"""
Tactile map generator for blind users.
Simple, clean implementation.
"""

import numpy as np
import xarray as xr
import geopandas as gpd
from pathlib import Path
from scipy.ndimage import gaussian_filter

# Configuration
from config import MAP_BOUNDS
from constants import (
    LABEL_CLEARANCE_LADDER_MM,
    CARD_WIDTH_MM, CARD_HEIGHT_MM,
    FULL_WIDTH_MM, FULL_HEIGHT_MM,
    BASE_THICKNESS_MM,
    MAX_ELEVATION_MM, TERRAIN_LEVELS,
    BOUNDARY_HEIGHT_MM, BOUNDARY_WIDTH_MM, BOUNDARY_RELIEF_MM,
    RIBBON_BOTTOM_Z, RIBBON_TOP_Z,
    WAVE_HEIGHT_MM, WAVE_INTERVAL_MM,
    CAPITAL_HEIGHT_MM, CAPITAL_DIAMETER_MM,
    TAB_HEIGHT_MM, TAB_DEPTH_MM, TAB_WIDTH_MM, TAB_HEAD_WIDTH_MM,
    SLOT_CLEARANCE_MM, SLOT_Z_CLEARANCE_MM,
    BRAILLE_DOT_RADIUS_MM, BRAILLE_DOT_HEIGHT_MM, BRAILLE_DOT_PITCH_MM,
    BRAILLE_CELL_PITCH_MM, BRAILLE_SKIRT_MM,
    BRAILLE_ANCHOR_WIDTH_MM, BRAILLE_ANCHOR_GAP_MM,
)
from countries import COUNTRIES, name_en

# Capitals data: (name, lon, lat, country_area_approx)
# area > 1.0 = show number, smaller = just bump
CAPITALS = [
    # Large countries - with numbers
    ("Moscow", 37.62, 55.75, 50),        # 1 Russia
    ("Ankara", 32.87, 39.93, 20),         # 2 Turkey
    ("Tehran", 51.39, 35.69, 15),         # 3 Iran
    ("Riyadh", 46.72, 24.69, 20),         # 4 Saudi Arabia
    ("Cairo", 31.24, 30.04, 10),          # 5 Egypt
    ("Algiers", 3.06, 36.74, 10),         # 6 Algeria
    ("Kyiv", 30.52, 50.45, 8),            # 7 Ukraine
    ("Warsaw", 21.01, 52.23, 5),          # 8 Poland
    ("Bucharest", 26.10, 44.43, 4),       # 9 Romania
    ("Baghdad", 44.37, 33.31, 5),         # 10 Iraq
    ("Kabul", 69.17, 34.53, 5),           # 11 Afghanistan
    ("Tripoli", 13.19, 32.90, 8),         # 12 Libya
    ("Tunis", 10.17, 36.81, 2),           # 13 Tunisia
    ("Damascus", 36.29, 33.51, 2),        # 14 Syria
    ("Amman", 35.93, 31.95, 1.5),         # 15 Jordan
    ("Baku", 49.87, 40.41, 1.5),          # 16 Azerbaijan
    ("Tbilisi", 44.79, 41.72, 1.2),       # 17 Georgia
    ("Yerevan", 44.51, 40.18, 1),         # 18 Armenia
    ("Athens", 23.73, 37.98, 2),          # 19 Greece
    ("Sofia", 23.32, 42.70, 1.5),         # 20 Bulgaria
    ("Belgrade", 20.46, 44.82, 1.2),      # 21 Serbia
    ("Budapest", 19.04, 47.50, 1.5),      # 22 Hungary
    ("Vienna", 16.37, 48.21, 1.2),        # 23 Austria
    ("Rome", 12.50, 41.90, 3),            # 24 Italy
    ("Berlin", 13.40, 52.52, 4),          # 25 Germany
    ("Minsk", 27.57, 53.90, 3),           # 26 Belarus
    ("Rabat", 6.85, 34.02, 4),            # 27 Morocco (W edge)
    ("Khartoum", 32.53, 15.55, 5),        # 28 Sudan
    ("Sanaa", 44.21, 15.35, 2),           # 29 Yemen
    ("Muscat", 58.39, 23.59, 2),          # 30 Oman
    ("Abu Dhabi", 54.37, 24.45, 1.2),     # 31 UAE
    ("Doha", 51.53, 25.29, 0.8),          # 32 Qatar - small
    ("Kuwait City", 47.98, 29.37, 0.8),   # 33 Kuwait - small
    ("Manama", 50.58, 26.23, 0.5),        # 34 Bahrain - small
    ("Beirut", 35.50, 33.89, 0.5),        # 35 Lebanon - small
    ("Jerusalem", 35.21, 31.77, 0.5),     # 36 Israel - small
    ("Nicosia", 33.38, 35.19, 0.4),       # 37 Cyprus - small
    ("Tirana", 19.82, 41.33, 0.8),        # 38 Albania - small
    ("Skopje", 21.43, 42.00, 0.6),        # 39 N. Macedonia - small
    ("Podgorica", 19.26, 42.44, 0.4),     # 40 Montenegro - small
    ("Sarajevo", 18.41, 43.86, 0.7),      # 41 Bosnia - small
    ("Zagreb", 15.98, 45.81, 1),          # 42 Croatia
    ("Ljubljana", 14.51, 46.06, 0.5),     # 43 Slovenia - small
    ("Bratislava", 17.11, 48.15, 0.8),    # 44 Slovakia - small
    ("Prague", 14.42, 50.08, 1.2),        # 45 Czechia
]

MIN_AREA_FOR_NUMBER = 1.0  # Countries smaller than this get bump only

# Paths
BASE_DIR = Path(__file__).parent.parent
ELEVATION_FILE = BASE_DIR / "data" / "input" / "ETOPO1_Bed_g_gmt4.grd"
BOUNDARIES_FILE = BASE_DIR / "data" / "output" / "merged_countries.geojson"
OUTPUT_FILE = BASE_DIR / "data" / "output" / "tactile_map.stl"


def deg_to_mm(lon, lat):
    """Convert degrees to mm on the map."""
    min_lon, min_lat, max_lon, max_lat = MAP_BOUNDS
    x = (lon - min_lon) / (max_lon - min_lon) * FULL_WIDTH_MM
    y = (lat - min_lat) / (max_lat - min_lat) * FULL_HEIGHT_MM
    return x, y


def load_elevation():
    """Load and process elevation data."""
    print("Loading elevation data...")
    ds = xr.open_dataset(ELEVATION_FILE)

    # Find elevation variable
    for var in ['z', 'elevation', 'Band1', 'topo']:
        if var in ds.variables:
            elev_var = var
            break
    else:
        elev_var = list(ds.data_vars)[0]

    # Get coordinate names
    lon_var = 'x' if 'x' in ds.coords else 'lon'
    lat_var = 'y' if 'y' in ds.coords else 'lat'

    # Slice to map bounds
    min_lon, min_lat, max_lon, max_lat = MAP_BOUNDS
    ds = ds.sel({lon_var: slice(min_lon, max_lon), lat_var: slice(min_lat, max_lat)})

    # Subsample (every 10th point)
    step = 10
    ds = ds.isel({lon_var: slice(None, None, step), lat_var: slice(None, None, step)})

    lon = ds[lon_var].values
    lat = ds[lat_var].values
    elevation = ds[elev_var].values

    print(f"  Grid size: {elevation.shape}")
    print(f"  Elevation range: {elevation.min():.0f} to {elevation.max():.0f} m")

    # Create coordinate grids in mm
    lon_mm = np.array([deg_to_mm(l, 0)[0] for l in lon])
    lat_mm = np.array([deg_to_mm(0, l)[1] for l in lat])
    X, Y = np.meshgrid(lon_mm, lat_mm)

    # Keep original lon/lat grids for water mask
    lon_deg, lat_deg = np.meshgrid(lon, lat)

    # Normalize elevation to 0-MAX_ELEVATION_MM
    # Water (negative) = 0, land scaled to 0-MAX_ELEVATION_MM
    Z = elevation.copy().astype(float)
    land_mask = Z > 0
    if land_mask.any():
        Z[land_mask] = (Z[land_mask] / Z[land_mask].max()) * MAX_ELEVATION_MM
    Z[Z < 0] = 0

    # Smooth for tactile comfort (сглаживание выбросов ETOPO, чтобы квантование
    # не дало одиночных "соль-перец" пикселей на границах плато).
    Z = gaussian_filter(Z, sigma=1.5)

    # Квантование в TERRAIN_LEVELS плато: 0/1/2/3 мм при MAX=4, LEVELS=4.
    # Ступени >= 2 × MIN_TACTILE_DIFFERENCE_MM — читаемо пальцем.
    bin_edges = np.linspace(0, MAX_ELEVATION_MM, TERRAIN_LEVELS + 1)
    level_values = bin_edges[:-1]  # floor каждого бина: [0, 1, 2, 3]
    bin_idx = np.clip(np.digitize(Z, bin_edges) - 1, 0, TERRAIN_LEVELS - 1)
    Z = level_values[bin_idx]

    return X, Y, Z, lon_deg, lat_deg


def create_water_mask(lon_deg, lat_deg, gdf):
    """Create water mask based on country boundaries (not elevation)."""
    print("Creating water mask from boundaries...")
    from shapely.geometry import Point
    from shapely.ops import unary_union

    # Union all country geometries
    all_land = unary_union(gdf.geometry.tolist())

    # Create mask: True where point is NOT inside any country (= water)
    water_mask = np.zeros(lon_deg.shape, dtype=bool)

    ny, nx = lon_deg.shape
    for i in range(ny):
        if i % 50 == 0:
            print(f"  Row {i}/{ny}...")
        for j in range(nx):
            pt = Point(lon_deg[i, j], lat_deg[i, j])
            water_mask[i, j] = not all_land.contains(pt)

    print(f"  Water: {water_mask.sum() / water_mask.size * 100:.1f}%")
    return water_mask


def create_wave_pattern(X, Y, water_mask):
    """Create wave pattern for water areas."""
    print("Creating wave pattern...")
    from scipy.ndimage import binary_erosion

    waves = np.zeros_like(X)

    # Erode water mask to avoid waves near coastline
    # This creates a buffer zone where no waves appear
    eroded_water = binary_erosion(water_mask, iterations=3)

    # Horizontal waves (along Y axis)
    wave_phase = (Y / WAVE_INTERVAL_MM) * 2 * np.pi
    waves = WAVE_HEIGHT_MM * 0.5 * (1 + np.sin(wave_phase))
    waves[~eroded_water] = 0

    water_pct = water_mask.sum() / water_mask.size * 100
    waves_pct = eroded_water.sum() / eroded_water.size * 100
    print(f"  Water: {water_pct:.1f}%, Waves area: {waves_pct:.1f}%")

    return waves


def create_terrain_mesh(X, Y, Z):
    """Create terrain surface mesh with flat bottom."""
    print("Creating terrain mesh...")
    ny, nx = Z.shape

    # Top surface vertices
    top_verts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])

    # Bottom surface vertices
    bottom_z = np.full_like(Z, -BASE_THICKNESS_MM)
    bottom_verts = np.column_stack([X.ravel(), Y.ravel(), bottom_z.ravel()])

    vertices = np.vstack([top_verts, bottom_verts])
    n_top = len(top_verts)

    faces = []

    # Top surface faces
    for i in range(ny - 1):
        for j in range(nx - 1):
            p1, p2 = i * nx + j, i * nx + j + 1
            p3, p4 = (i + 1) * nx + j, (i + 1) * nx + j + 1
            faces.append([p1, p2, p4])
            faces.append([p1, p4, p3])

    # Bottom surface faces (reversed winding)
    for i in range(ny - 1):
        for j in range(nx - 1):
            p1, p2 = n_top + i * nx + j, n_top + i * nx + j + 1
            p3, p4 = n_top + (i + 1) * nx + j, n_top + (i + 1) * nx + j + 1
            faces.append([p1, p4, p2])
            faces.append([p1, p3, p4])

    # Side walls
    # Front (y=0)
    for j in range(nx - 1):
        t1, t2 = j, j + 1
        b1, b2 = n_top + j, n_top + j + 1
        faces.append([t1, b1, t2])
        faces.append([t2, b1, b2])

    # Back (y=max)
    for j in range(nx - 1):
        t1, t2 = (ny - 1) * nx + j, (ny - 1) * nx + j + 1
        b1, b2 = n_top + (ny - 1) * nx + j, n_top + (ny - 1) * nx + j + 1
        faces.append([t1, t2, b1])
        faces.append([t2, b2, b1])

    # Left (x=0)
    for i in range(ny - 1):
        t1, t2 = i * nx, (i + 1) * nx
        b1, b2 = n_top + i * nx, n_top + (i + 1) * nx
        faces.append([t1, t2, b1])
        faces.append([t2, b2, b1])

    # Right (x=max)
    for i in range(ny - 1):
        t1, t2 = i * nx + nx - 1, (i + 1) * nx + nx - 1
        b1, b2 = n_top + i * nx + nx - 1, n_top + (i + 1) * nx + nx - 1
        faces.append([t1, b1, t2])
        faces.append([t2, b1, b2])

    print(f"  Vertices: {len(vertices)}, Faces: {len(faces)}")
    return vertices, np.array(faces)


def load_boundaries_full():
    """Load all country boundaries (for water mask)."""
    print("Loading full boundaries (for water mask)...")
    from shapely.geometry import box

    gdf = gpd.read_file(BOUNDARIES_FILE)
    min_lon, min_lat, max_lon, max_lat = MAP_BOUNDS
    clip_box = box(min_lon, min_lat, max_lon, max_lat)
    gdf = gdf.clip(clip_box)

    print(f"  Total features: {len(gdf)}")
    return gdf


def load_boundaries_filtered():
    """Load country boundaries filtered (for walls, no small islands)."""
    print("Loading filtered boundaries (for walls)...")
    from shapely.geometry import box, MultiPolygon

    gdf = gpd.read_file(BOUNDARIES_FILE)
    min_lon, min_lat, max_lon, max_lat = MAP_BOUNDS
    clip_box = box(min_lon, min_lat, max_lon, max_lat)
    gdf = gdf.clip(clip_box)

    # Remove small islands (area < 0.5 square degrees)
    MIN_AREA = 0.5

    def filter_small_parts(geom):
        if geom is None or geom.is_empty:
            return None
        if geom.geom_type == 'Polygon':
            return geom if geom.area >= MIN_AREA else None
        elif geom.geom_type == 'MultiPolygon':
            large_parts = [p for p in geom.geoms if p.area >= MIN_AREA]
            if not large_parts:
                return None
            return MultiPolygon(large_parts) if len(large_parts) > 1 else large_parts[0]
        return geom

    gdf = gdf.copy()
    gdf['geometry'] = gdf['geometry'].apply(filter_small_parts)
    gdf = gdf[gdf['geometry'].notna()]
    gdf['geometry'] = gdf['geometry'].simplify(tolerance=0.1, preserve_topology=True)

    print(f"  Countries (filtered): {len(gdf)}")
    return gdf


# ============================================================================
# Block B — boundary walls via unified skeleton (no per-country duplicates)
# ============================================================================
# Подход:
#   1) unary_union всех полигонов стран → один merged shape
#   2) .boundary → MultiLineString, где общая граница соседей представлена
#      РОВНО одной линией (дубли #3.6 больше не возникают).
#   3) intersection(interior) отбрасывает прямые отрезки по рамке карты
#      (5°/70°/12°/55°), которые иначе превратились бы в фейковые границы.
#   4) Каждая линия строится как замкнутый 3D ribbon-solid от RIBBON_BOTTOM_Z
#      до RIBBON_TOP_Z — цельный столбик, вгрызающийся в плиту и рельеф.
#      Никаких щелей снизу (#3.1) и никаких висящих верхов по рельефу (#4.7.1).


def _extract_linestrings(geom):
    """Flatten any geometry into a list of LineStrings."""
    if geom is None or geom.is_empty:
        return []
    gt = geom.geom_type
    if gt == 'LineString':
        return [geom]
    if gt == 'MultiLineString':
        return list(geom.geoms)
    if gt == 'GeometryCollection':
        out = []
        for g in geom.geoms:
            out.extend(_extract_linestrings(g))
        return out
    return []  # Point, Polygon, etc. — irrelevant for boundary skeleton


def _build_ribbon_solid(coords_xy, z_bottom, z_top, width):
    """Build a watertight ribbon solid along a polyline.

    At each vertex we emit 4 corners (LB, RB, LT, RT) in the local frame
    (+perp = left, −perp = right, z_bottom / z_top). Corners are SHARED by
    adjacent segments → every interior joint is manifold without seams.
    Open-line endpoints get end caps; closed rings loop without caps.

    Interior perpendiculars use the bisector of adjacent segments
    (= half-mitre). Not a true mitre (sharp convex corners still flatten),
    but it eliminates the gap-and-fang artefacts of per-segment boxes
    — which is what #4.7.2 calls out. True mitre = future work.

    Winding is computed explicitly so that all face normals point outward;
    the mesh has positive volume without relying on trimesh.fix_normals.

    Args:
        coords_xy: iterable of (x_mm, y_mm) along the polyline
        z_bottom, z_top: ribbon top/bottom z (mm)
        width: ribbon cross-section width (mm)

    Returns:
        (vertices (n*4, 3), faces (k, 3)) numpy arrays, or (None, None) if
        the polyline degenerates to fewer than 2 usable points.
    """
    pts = np.asarray(list(coords_xy), dtype=float)
    if len(pts) < 2:
        return None, None

    # Drop consecutive duplicates (shapely.simplify can leave them)
    keep = [0]
    for i in range(1, len(pts)):
        if np.linalg.norm(pts[i] - pts[keep[-1]]) > 1e-6:
            keep.append(i)
    pts = pts[keep]
    if len(pts) < 2:
        return None, None

    is_closed = np.allclose(pts[0], pts[-1])
    if is_closed:
        pts = pts[:-1]  # drop redundant last point
        if len(pts) < 3:
            return None, None

    n = len(pts)
    half_w = width / 2.0

    # Perpendicular at each vertex (2D). For endpoints of open lines use the
    # single adjacent segment; for interior vertices (and all vertices of a
    # closed ring) use the normalised bisector of the two adjacent perps.
    perps = np.zeros((n, 2))
    for i in range(n):
        if is_closed:
            prev_i, next_i = (i - 1) % n, (i + 1) % n
            has_prev = has_next = True
        else:
            has_prev = i > 0
            has_next = i < n - 1
            prev_i, next_i = max(i - 1, 0), min(i + 1, n - 1)

        # Compute perpendicular vectors of incoming / outgoing segments
        p_prev = p_next = None
        if has_prev:
            d = pts[i] - pts[prev_i]
            L = np.linalg.norm(d)
            if L > 1e-6:
                p_prev = np.array([-d[1], d[0]]) / L  # CCW 90° (left of forward)
        if has_next:
            d = pts[next_i] - pts[i]
            L = np.linalg.norm(d)
            if L > 1e-6:
                p_next = np.array([-d[1], d[0]]) / L

        if p_prev is None and p_next is None:
            perps[i] = (0.0, half_w)  # pathological; should never happen
        elif p_prev is None:
            perps[i] = p_next * half_w
        elif p_next is None:
            perps[i] = p_prev * half_w
        else:
            avg = p_prev + p_next
            L = np.linalg.norm(avg)
            if L < 1e-6:
                # 180° turn — use one of them
                perps[i] = p_prev * half_w
            else:
                perps[i] = avg / L * half_w

    # Vertices: 4 per polyline vertex (LB, RB, LT, RT)
    verts = np.empty((n * 4, 3), dtype=float)
    for i in range(n):
        x, y = pts[i]
        px, py = perps[i]
        verts[i * 4 + 0] = (x + px, y + py, z_bottom)  # 0 LB  (left-bottom)
        verts[i * 4 + 1] = (x - px, y - py, z_bottom)  # 1 RB  (right-bottom)
        verts[i * 4 + 2] = (x + px, y + py, z_top)     # 2 LT  (left-top)
        verts[i * 4 + 3] = (x - px, y - py, z_top)     # 3 RT  (right-top)

    LB, RB, LT, RT = 0, 1, 2, 3

    def vi(i, kind):
        return i * 4 + kind

    # Segment iteration (closed ring wraps; open line stops at n-1)
    if is_closed:
        segs = [(i, (i + 1) % n) for i in range(n)]
    else:
        segs = [(i, i + 1) for i in range(n - 1)]

    faces = []
    for (i, j) in segs:
        # Top (normal +Z) — verified by cross product for the +X-tangent case
        faces.append([vi(i, LT), vi(j, RT), vi(j, LT)])
        faces.append([vi(i, LT), vi(i, RT), vi(j, RT)])
        # Bottom (normal −Z)
        faces.append([vi(i, LB), vi(j, LB), vi(j, RB)])
        faces.append([vi(i, LB), vi(j, RB), vi(i, RB)])
        # Left side (normal +perp)
        faces.append([vi(i, LB), vi(i, LT), vi(j, LT)])
        faces.append([vi(i, LB), vi(j, LT), vi(j, LB)])
        # Right side (normal −perp)
        faces.append([vi(i, RB), vi(j, RB), vi(j, RT)])
        faces.append([vi(i, RB), vi(j, RT), vi(i, RT)])

    # End caps for open lines (normals along ±tangent)
    if not is_closed:
        # Front cap at vertex 0 (normal = −tangent, points "back" out of line)
        faces.append([vi(0, LB), vi(0, RB), vi(0, RT)])
        faces.append([vi(0, LB), vi(0, RT), vi(0, LT)])
        # Back cap at vertex n-1 (normal = +tangent)
        last = n - 1
        faces.append([vi(last, LB), vi(last, RT), vi(last, RB)])
        faces.append([vi(last, LB), vi(last, LT), vi(last, RT)])

    return verts, np.array(faces, dtype=np.int64)


def create_boundary_walls(gdf):
    """Build boundary walls as a single unified ribbon skeleton.

    Replaces per-country polygon iteration (which double-walled shared
    borders) with unary_union → .boundary → one ribbon per merged line.
    Also filters out the clip-box edges (5°/70°/12°/55°) so there are no
    fake "border" walls along the rectangular rim of the map.

    Each ribbon is a closed manifold solid from RIBBON_BOTTOM_Z (-5.99)
    to RIBBON_TOP_Z (+9). The bottom sits just above the plate floor to
    avoid coplanar faces (one of master's "шупљине" complaints); the top
    is a uniform plane above the highest terrain for easy finger-skim.
    """
    from shapely.ops import unary_union
    from shapely.geometry import box as shbox

    print("Creating boundary walls (unified skeleton)...")

    # 1. Collect boundary LINES from each polygon, then union the *lines*.
    #    Union of POLYGONS would merge adjacent countries into one land blob
    #    and its .boundary would be only the coastline — erasing all
    #    internal borders. Union of LINES merges shared segments between
    #    neighbours (dedup) but preserves every boundary segment as itself.
    polys = [g for g in gdf.geometry.tolist() if g is not None and not g.is_empty]
    if not polys:
        print("  No polygons — no walls")
        return np.array([]), np.array([])

    all_lines = []
    for poly in polys:
        if poly.geom_type == 'Polygon':
            polygons = [poly]
        elif poly.geom_type == 'MultiPolygon':
            polygons = list(poly.geoms)
        else:
            continue
        for p in polygons:
            b = p.boundary
            if b.geom_type == 'LineString':
                all_lines.append(b)
            elif b.geom_type == 'MultiLineString':
                all_lines.extend(b.geoms)

    if not all_lines:
        return np.array([]), np.array([])

    boundary = unary_union(all_lines)

    # 2. Filter out clip-box edges by intersecting with a slightly shrunk
    #    interior box. Segments that lie exactly on 5°/70°/12°/55° disappear;
    #    real borders touching the clip at a single vertex survive.
    clip_eps = 1e-3  # ≈ 100 m at these latitudes — well below geoboundary noise
    interior = shbox(
        MAP_BOUNDS[0] + clip_eps,
        MAP_BOUNDS[1] + clip_eps,
        MAP_BOUNDS[2] - clip_eps,
        MAP_BOUNDS[3] - clip_eps,
    )
    boundary = boundary.intersection(interior)

    # 3. Extract all LineStrings, simplify each (tolerance 0.15° ≈ 1 mm on map).
    lines_deg = _extract_linestrings(boundary)
    lines_deg = [ln.simplify(0.15, preserve_topology=True) for ln in lines_deg]

    print(f"  Skeleton: {len(lines_deg)} line(s) after union + clip filter")

    # 4. Build ribbon solid for each line.
    all_verts, all_faces = [], []
    vert_offset = 0
    built = 0
    skipped = 0
    total_pts = 0

    for ln in lines_deg:
        coords_mm = [deg_to_mm(lon, lat) for lon, lat in ln.coords]
        verts, faces = _build_ribbon_solid(
            coords_mm, RIBBON_BOTTOM_Z, RIBBON_TOP_Z, BOUNDARY_WIDTH_MM
        )
        if verts is None:
            skipped += 1
            continue
        all_verts.append(verts)
        all_faces.append(faces + vert_offset)
        vert_offset += len(verts)
        built += 1
        total_pts += len(verts) // 4

    if not all_verts:
        print("  No ribbons built")
        return np.array([]), np.array([])

    vertices = np.vstack(all_verts)
    faces = np.vstack(all_faces)
    print(
        f"  Built {built} ribbon(s), skipped {skipped}, "
        f"{total_pts} polyline points → "
        f"{len(vertices)} verts, {len(faces)} faces"
    )
    return vertices, faces


# 7-segment digit definitions (which segments are ON for each digit)
# Segments: top, top-right, bottom-right, bottom, bottom-left, top-left, middle
DIGIT_SEGMENTS = {
    '0': [1,1,1,1,1,1,0],
    '1': [0,1,1,0,0,0,0],
    '2': [1,1,0,1,1,0,1],
    '3': [1,1,1,1,0,0,1],
    '4': [0,1,1,0,0,1,1],
    '5': [1,0,1,1,0,1,1],
    '6': [1,0,1,1,1,1,1],
    '7': [1,1,1,0,0,0,0],
    '8': [1,1,1,1,1,1,1],
    '9': [1,1,1,1,0,1,1],
}


def get_digit_bbox(digit_str, x_mm, y_mm, digit_height=4.0, digit_width=2.5, padding=0.5):
    """Get bounding box of a number in mm coordinates."""
    total_width = len(digit_str) * (digit_width + 0.5) - 0.5
    half_height = digit_height / 2

    return (
        x_mm - total_width / 2 - padding,       # min_x
        y_mm - half_height - padding,            # min_y
        x_mm + total_width / 2 + padding,        # max_x
        y_mm + half_height + padding             # max_y
    )


def check_number_collision(x_mm, y_mm, digit_str, gdf, all_land, digit_height=4.0, digit_width=2.5):
    """Check if number at position collides with country boundaries or is on water."""
    from shapely.geometry import box as shapely_box, Point

    # Get bounding box in mm
    min_x, min_y, max_x, max_y = get_digit_bbox(digit_str, x_mm, y_mm, digit_height, digit_width)

    # Convert mm back to degrees for intersection check
    min_lon, min_lat, max_lon, max_lat = MAP_BOUNDS

    def mm_to_deg(x, y):
        lon = min_lon + (x / FULL_WIDTH_MM) * (max_lon - min_lon)
        lat = min_lat + (y / FULL_HEIGHT_MM) * (max_lat - min_lat)
        return lon, lat

    lon1, lat1 = mm_to_deg(min_x, min_y)
    lon2, lat2 = mm_to_deg(max_x, max_y)

    rect = shapely_box(lon1, lat1, lon2, lat2)

    # Check if center is on water (outside all countries)
    center_lon, center_lat = mm_to_deg(x_mm, y_mm)
    if not all_land.contains(Point(center_lon, center_lat)):
        return True  # On water = collision

    # Check intersection with any boundary line
    for _, row in gdf.iterrows():
        geom = row.geometry
        if geom is None:
            continue
        boundary = geom.boundary
        if rect.intersects(boundary):
            return True

    return False


def _mm_to_deg_pt(x, y):
    """mm -> (lon, lat) on the map."""
    min_lon, min_lat, max_lon, max_lat = MAP_BOUNDS
    lon = min_lon + (x / FULL_WIDTH_MM) * (max_lon - min_lon)
    lat = min_lat + (y / FULL_HEIGHT_MM) * (max_lat - min_lat)
    return lon, lat


def find_number_position(capital_x, capital_y, digit_str, country_geom):
    """Find an (x_mm, y_mm) near the capital where the BRAILLE number label
    lies fully INSIDE the country polygon — so it never crosses a border, sits
    on water, or lands in a neighbour. Expanding-ring search around the capital.

    Returns None if the country is too small to hold the label anywhere; that
    country then keeps just its bump and gets no number (design 2026-06-19:
    don't force numbers that don't fit). Because the search probes the whole
    interior (not just 4 spots by the capital), normal countries with a coastal
    capital — Greece, Tunisia, Oman… — still get numbered.
    """
    import math
    from shapely.geometry import box as shapely_box

    if country_geom is None or country_geom.is_empty:
        return None

    total_width, total_height = braille_label_size(digit_str)
    half_w, half_h = total_width / 2 + 0.5, total_height / 2 + 0.5  # +pad
    base = CAPITAL_DIAMETER_MM / 2 + max(total_width, total_height) / 2 + 1.0

    candidates = [(capital_x, capital_y)]
    for ring in range(1, 15):
        r = base + (ring - 1) * 2.5
        for k in range(8):
            ang = 2 * math.pi * k / 8
            candidates.append((capital_x + r * math.cos(ang),
                               capital_y + r * math.sin(ang)))

    # keep the label OFF the capital bump (review 2026-08-04: the first ring
    # candidate is the capital itself, and the grid fallback sorts nearest-
    # first — labels were landing right on the 2 mm bump dome).
    bump_r = CAPITAL_DIAMETER_MM / 2 + 0.5

    def _fits(x, y):
        # label rect must not overlap the capital bump footprint
        ddx = max(abs(x - capital_x) - half_w, 0.0)
        ddy = max(abs(y - capital_y) - half_h, 0.0)
        if ddx * ddx + ddy * ddy < bump_r * bump_r:
            return False
        lon1, lat1 = _mm_to_deg_pt(x - half_w, y - half_h)
        lon2, lat2 = _mm_to_deg_pt(x + half_w, y + half_h)
        rect = shapely_box(min(lon1, lon2), min(lat1, lat2),
                           max(lon1, lon2), max(lat1, lat2))
        return country_geom.contains(rect)

    for x, y in candidates:
        if _fits(x, y):
            return (x, y)

    # FALLBACK (2026-08-04): the ring probe samples only 8 directions and can
    # miss the one interior pocket of a narrow/crescent country (Croatia,
    # Slovakia, Georgia…). Walk a 3 mm grid over the country's bbox, nearest-
    # to-capital first, and take the first spot the label truly fits.
    from config import MAP_BOUNDS as _MB
    min_lon, min_lat, max_lon, max_lat = _MB
    g_lon1, g_lat1, g_lon2, g_lat2 = country_geom.bounds
    gx1 = max(0.0, (g_lon1 - min_lon) / (max_lon - min_lon) * FULL_WIDTH_MM)
    gx2 = min(FULL_WIDTH_MM, (g_lon2 - min_lon) / (max_lon - min_lon) * FULL_WIDTH_MM)
    gy1 = max(0.0, (g_lat1 - min_lat) / (max_lat - min_lat) * FULL_HEIGHT_MM)
    gy2 = min(FULL_HEIGHT_MM, (g_lat2 - min_lat) / (max_lat - min_lat) * FULL_HEIGHT_MM)
    step = 3.0
    grid = [(x, y)
            for x in np.arange(gx1 + half_w, gx2 - half_w + 1e-9, step)
            for y in np.arange(gy1 + half_h, gy2 - half_h + 1e-9, step)]
    grid.sort(key=lambda p: (p[0] - capital_x) ** 2 + (p[1] - capital_y) ** 2)
    for x, y in grid[:4000]:
        if _fits(x, y):
            return (x, y)
    return None


def create_digit_mesh(digit_str, x_mm, y_mm, base_z, digit_height=4.0, digit_width=2.5, thickness=1.0, line_width=0.6, spacing=1.5):
    """Create 3D mesh for a number (one or two digits)."""
    all_verts = []
    all_faces = []
    vert_offset = 0

    # Offset for multi-digit numbers
    total_width = len(digit_str) * (digit_width + spacing) - spacing
    start_x = x_mm - total_width / 2

    for idx, digit in enumerate(digit_str):
        if digit not in DIGIT_SEGMENTS:
            continue

        dx = start_x + idx * (digit_width + spacing)
        segments = DIGIT_SEGMENTS[digit]

        # Segment positions (relative to digit origin)
        # Each segment: (x1, y1, x2, y2)
        h = digit_height / 2
        w = digit_width
        seg_coords = [
            (0, h, w, h),           # top
            (w, h, w, 0),           # top-right
            (w, 0, w, -h),          # bottom-right
            (0, -h, w, -h),         # bottom
            (0, -h, 0, 0),          # bottom-left
            (0, 0, 0, h),           # top-left
            (0, 0, w, 0),           # middle
        ]

        for seg_idx, on in enumerate(segments):
            if not on:
                continue

            sx1, sy1, sx2, sy2 = seg_coords[seg_idx]
            verts, faces = create_segment_box(
                dx + sx1, y_mm + sy1,
                dx + sx2, y_mm + sy2,
                base_z, thickness, line_width
            )

            if len(verts) > 0:
                all_verts.append(verts)
                all_faces.append(faces + vert_offset)
                vert_offset += len(verts)

    if all_verts:
        return np.vstack(all_verts), np.vstack(all_faces)
    return np.array([]), np.array([])


def create_segment_box(x1, y1, x2, y2, base_z, height, width):
    """Create a 3D box for one segment of a digit."""
    # Direction vector
    dx, dy = x2 - x1, y2 - y1
    length = np.sqrt(dx*dx + dy*dy)
    if length < 0.01:
        return np.array([]), np.array([])

    # Perpendicular for width
    px, py = -dy/length * width/2, dx/length * width/2

    # 8 vertices of the box
    vertices = [
        [x1+px, y1+py, base_z],          # 0: start, left, bottom
        [x1-px, y1-py, base_z],          # 1: start, right, bottom
        [x2+px, y2+py, base_z],          # 2: end, left, bottom
        [x2-px, y2-py, base_z],          # 3: end, right, bottom
        [x1+px, y1+py, base_z+height],   # 4: start, left, top
        [x1-px, y1-py, base_z+height],   # 5: start, right, top
        [x2+px, y2+py, base_z+height],   # 6: end, left, top
        [x2-px, y2-py, base_z+height],   # 7: end, right, top
    ]

    faces = [
        [0,2,1], [1,2,3],  # bottom
        [4,5,6], [5,7,6],  # top
        [0,1,4], [1,5,4],  # start cap
        [2,6,3], [3,6,7],  # end cap
        [0,4,2], [2,4,6],  # left side
        [1,3,5], [3,7,5],  # right side
    ]

    return np.array(vertices), np.array(faces)


def create_capital_bump(x_mm, y_mm, base_z, radius, height, segments=12):
    """Create a hemisphere bump for a capital city."""
    vertices = []
    faces = []

    # Center point at top
    top_idx = 0
    vertices.append([x_mm, y_mm, base_z + height])

    # Create rings from top to bottom
    n_rings = 6
    for ring in range(1, n_rings + 1):
        angle_v = (ring / n_rings) * (np.pi / 2)  # 0 to 90 degrees
        z = base_z + height * np.cos(angle_v)
        r = radius * np.sin(angle_v)

        for seg in range(segments):
            angle_h = (seg / segments) * 2 * np.pi
            vx = x_mm + r * np.cos(angle_h)
            vy = y_mm + r * np.sin(angle_h)
            vertices.append([vx, vy, z])

    # Top cap faces (connect to center)
    for seg in range(segments):
        next_seg = (seg + 1) % segments
        faces.append([0, 1 + seg, 1 + next_seg])

    # Ring faces
    for ring in range(n_rings - 1):
        ring_start = 1 + ring * segments
        next_ring_start = 1 + (ring + 1) * segments
        for seg in range(segments):
            next_seg = (seg + 1) % segments
            v1 = ring_start + seg
            v2 = ring_start + next_seg
            v3 = next_ring_start + seg
            v4 = next_ring_start + next_seg
            faces.append([v1, v3, v2])
            faces.append([v2, v3, v4])

    # Bottom cap (flat)
    bottom_center_idx = len(vertices)
    vertices.append([x_mm, y_mm, base_z])
    last_ring_start = 1 + (n_rings - 1) * segments
    for seg in range(segments):
        next_seg = (seg + 1) % segments
        faces.append([bottom_center_idx, last_ring_start + next_seg, last_ring_start + seg])

    return np.array(vertices), np.array(faces)


def create_country_labels_mesh(X, Y, Z, gdf, max_labels=32, verbose=True):
    """Braille number labels placed INSIDE each country polygon.

    Replaces the capital-driven version (2026-08-05). Three changes:
      * no capital bumps — the number alone points at the legend, which frees
        the space the 3 mm dome used to eat and removes a feature that was
        easily confused with a braille dot;
      * the label is keyed on the COUNTRY POLYGON, not on a capital
        coordinate. The old list had Rabat at +6.85 lon instead of -6.85, so
        its label landed inside ALGERIA and the legend called Algeria
        "Rabat/Maroko"; Moscow (lat 55.75) and Algiers (lon 3.06) fell outside
        the map frame, so Russia and Algeria got no label at all;
      * the position is the pole of inaccessibility (polylabel) — the most
        central point of the country — instead of a ring search around the
        capital, so the label sits where the country is widest.
    """
    from shapely.geometry import box as shapely_box, Point
    from shapely.ops import unary_union, polylabel

    print("Placing country number labels...")
    min_lon, min_lat, max_lon, max_lat = MAP_BOUNDS
    frame = shapely_box(min_lon, min_lat, max_lon, max_lat)
    lon_per_mm = (max_lon - min_lon) / FULL_WIDTH_MM
    lat_per_mm = (max_lat - min_lat) / FULL_HEIGHT_MM

    # The border ridge rides ON the polygon edge and eats BOUNDARY_WIDTH/2 of
    # the interior; on top of that the label wants a clear field. Rather than
    # one global value, walk the ladder per country: a big country gets the
    # full 3 mm the guidelines ask for, a small one gets the least that still
    # works instead of losing its label entirely.
    # The map is cut into 2x2 puzzle cards, so there is exactly one vertical
    # and one horizontal seam. A label straddling one is sliced in half and
    # unreadable on BOTH cards — the placement must refuse those spots.
    seam_lon = min_lon + CARD_WIDTH_MM * lon_per_mm
    seam_lat = min_lat + CARD_HEIGHT_MM * lat_per_mm

    def fits(geom, x, y, w_mm, h_mm, margin_mm):
        hw = (w_mm / 2 + margin_mm) * lon_per_mm
        hh = (h_mm / 2 + margin_mm) * lat_per_mm
        if (x - hw) < seam_lon < (x + hw) or (y - hh) < seam_lat < (y + hh):
            return False
        return geom.contains(shapely_box(x - hw, y - hh, x + hw, y + hh))

    def find_pos(geom, digits):
        """(x_deg, y_deg, clear_mm) at the most generous clearance that fits."""
        w_mm, h_mm = braille_label_size(digits)
        x0, y0, x1, y1 = geom.bounds
        edge = geom.boundary
        for clear in LABEL_CLEARANCE_LADDER_MM:
            margin_mm = BOUNDARY_WIDTH_MM / 2 + clear
            try:
                p = polylabel(geom, tolerance=0.02)
                if fits(geom, p.x, p.y, w_mm, h_mm, margin_mm):
                    return (p.x, p.y, clear)
            except Exception:
                pass
            # fallback: grid, keep the candidate with the most clearance
            best, best_clear = None, -1.0
            for i in range(26):
                x = x0 + (i + 0.5) * (x1 - x0) / 26
                for j in range(26):
                    y = y0 + (j + 0.5) * (y1 - y0) / 26
                    if not fits(geom, x, y, w_mm, h_mm, margin_mm):
                        continue
                    c = edge.distance(Point(x, y))
                    if c > best_clear:
                        best, best_clear = (x, y), c
            if best is not None:
                return (best[0], best[1], clear)
        return None

    # one geometry per ISO3, clipped to the map frame, largest part only
    parts = {}
    for _, row in gdf.iterrows():
        iso = str(row.get('source_file') or '')
        if iso in COUNTRIES:
            parts.setdefault(iso, []).append(row.geometry)

    cands, no_room = [], []
    for iso, geoms in parts.items():
        g = unary_union(geoms).intersection(frame)
        if g.is_empty:
            continue
        if g.geom_type == 'MultiPolygon':
            g = max(g.geoms, key=lambda p: p.area)
        pos2 = find_pos(g, '00')
        pos1 = None if pos2 else find_pos(g, '0')
        if pos2 is None and pos1 is None:
            no_room.append(iso)
            continue
        cands.append(dict(iso=iso, area=g.area, pos2=pos2, pos1=pos1))

    # The nine single-cell numbers are scarce: give them to the countries that
    # can ONLY hold a one-cell label, biggest first.
    tight = sorted([c for c in cands if c["pos2"] is None], key=lambda c: -c["area"])
    easy = sorted([c for c in cands if c["pos2"] is not None], key=lambda c: -c["area"])
    dropped = []
    if len(tight) > 9:
        dropped += tight[9:]
        tight = tight[:9]
    room = max(0, max_labels - len(tight))
    if len(easy) > room:
        dropped += easy[room:]
        easy = easy[:room]

    ordered = [(c["iso"], c["pos1"]) for c in tight] + \
              [(c["iso"], c["pos2"]) for c in easy]

    all_verts, all_faces, vert_offset = [], [], 0
    number_legend = []          # (number, iso3)
    placements = []             # (number, iso3, x_mm, y_mm) for verification

    for num, (iso, position) in enumerate(ordered, start=1):
        number_str = str(num)
        number_legend.append((num, iso))
        num_x, num_y = deg_to_mm(position[0], position[1])
        clear_mm = position[2]

        # Base height = MAX terrain over the label footprint, not the centre
        # sample: a label straddling a 1 mm plateau step had its 0.8 mm domes
        # drowned on the higher side. With the max, every dot APEX sits on one
        # flat plane; the 4.2 mm skirt still anchors dots over lower ground.
        lw, lh = braille_label_size(number_str)
        xm = (X[0, :] >= num_x - lw / 2) & (X[0, :] <= num_x + lw / 2)
        ym = (Y[:, 0] >= num_y - lh / 2) & (Y[:, 0] <= num_y + lh / 2)
        if xm.any() and ym.any():
            base_z = float(Z[np.ix_(ym, xm)].max())
        else:
            base_z = float(Z[np.argmin(np.abs(Y[:, 0] - num_y)),
                             np.argmin(np.abs(X[0, :] - num_x))])

        v, f = create_braille_number(number_str, num_x, num_y, base_z)
        if len(v) > 0:
            all_verts.append(v)
            all_faces.append(f + vert_offset)
            vert_offset += len(v)
        placements.append((num, iso, num_x, num_y, clear_mm))

    if verbose:
        print(f"  Labelled {len(number_legend)} countries:")
        for (num, iso), pl in zip(number_legend, placements):
            print(f"    {num:2d}. {iso}  {name_en(iso):<14} clear {pl[4]:.1f} mm")
        if dropped:
            print("  Over legend cap: " + ", ".join(c['iso'] for c in dropped))
        if no_room:
            print("  Too small for any label: " + ", ".join(sorted(no_room)))
        missing = [i for i in COUNTRIES if i not in parts]
        if missing:
            print("  Not on this map: " + ", ".join(sorted(missing)))

    if all_verts:
        return (np.vstack(all_verts), np.vstack(all_faces),
                number_legend, placements)
    return np.array([]), np.array([]), number_legend, placements


# Braille alphabet (dots 1-6 positions: 1,4 top; 2,5 middle; 3,6 bottom)
# Each letter is a tuple of active dot positions (1-6)
BRAILLE = {
    'a': (1,), 'b': (1,2), 'c': (1,4), 'd': (1,4,5), 'e': (1,5),
    'f': (1,2,4), 'g': (1,2,4,5), 'h': (1,2,5), 'i': (2,4), 'j': (2,4,5),
    'k': (1,3), 'l': (1,2,3), 'm': (1,3,4), 'n': (1,3,4,5), 'o': (1,3,5),
    'p': (1,2,3,4), 'q': (1,2,3,4,5), 'r': (1,2,3,5), 's': (2,3,4), 't': (2,3,4,5),
    'u': (1,3,6), 'v': (1,2,3,6), 'w': (2,4,5,6), 'x': (1,3,4,6), 'y': (1,3,4,5,6),
    'z': (1,3,5,6), ' ': (),
}


def create_braille_dot(x, y, z,
                       radius=BRAILLE_DOT_RADIUS_MM,
                       height=BRAILLE_DOT_HEIGHT_MM,
                       skirt=BRAILLE_SKIRT_MM):
    """Create a single braille dot: a smooth DOME on a buried cylinder skirt.

    The dome (spherical cap) is what the finger feels — rounded, never sharp.
    The skirt extends `skirt` mm BELOW z so the boolean union always fuses the
    dot into the plate/terrain even after embed shifts or a relief step; it is
    invisible in the print. (The old dot was an 8-segment CONE with an apex
    point — felt tiny and sharp — and lost height to embedding.)
    """
    segments = 12
    rings = 4  # latitude rings of the dome (excluding apex)
    vertices = []
    faces = []

    # Skirt bottom ring
    for seg in range(segments):
        a = (seg / segments) * 2 * np.pi
        vertices.append([x + radius * np.cos(a), y + radius * np.sin(a), z - skirt])
    # Skirt top ring == dome base ring (at z)
    for seg in range(segments):
        a = (seg / segments) * 2 * np.pi
        vertices.append([x + radius * np.cos(a), y + radius * np.sin(a), z])

    # Skirt walls
    for seg in range(segments):
        n = (seg + 1) % segments
        faces.append([seg, n, segments + seg])
        faces.append([n, segments + n, segments + seg])

    # Dome rings: spherical cap, sphere radius R through base circle and apex
    R = (radius * radius + height * height) / (2.0 * height)
    zc = z + height - R          # sphere centre
    # arccos is correct on BOTH branches (height <=> radius); arcsin would
    # silently fold caps taller than a hemisphere back under 90°.
    a0 = np.arccos(np.clip((R - height) / R, -1.0, 1.0))  # polar angle of base ring
    ring_start = segments        # dome base ring index
    for r_i in range(1, rings):
        ang = a0 * (1 - r_i / rings)
        rr = R * np.sin(ang)
        zz = zc + R * np.cos(ang)
        idx0 = len(vertices)
        for seg in range(segments):
            a = (seg / segments) * 2 * np.pi
            vertices.append([x + rr * np.cos(a), y + rr * np.sin(a), zz])
        prev = ring_start if r_i == 1 else idx0 - segments
        for seg in range(segments):
            n = (seg + 1) % segments
            faces.append([prev + seg, prev + n, idx0 + seg])
            faces.append([prev + n, idx0 + n, idx0 + seg])

    # Apex
    apex = len(vertices)
    vertices.append([x, y, z + height])
    last = apex - segments
    for seg in range(segments):
        n = (seg + 1) % segments
        faces.append([last + seg, last + n, apex])

    # Bottom cap (fan on skirt bottom ring)
    center = len(vertices)
    vertices.append([x, y, z - skirt])
    for seg in range(segments):
        n = (seg + 1) % segments
        faces.append([center, n, seg])

    return np.array(vertices), np.array(faces)


# Braille digits (French/UEB and Serbian alike): letters a-j stand for 1-90.
# On the map the label is a compact 1-2 cell KEY (no number sign — tactile
# graphics practice for space-constrained keys; the legend pairs each key
# with its name, which teaches the convention). Flip NUMBER_SIGN to True to
# prefix every number with the ⠼ indicator (braille-канонично, но шире —
# часть маленьких стран потеряет номер, не влезет).
NUMBER_SIGN = False
NUMBER_SIGN_DOTS = (3, 4, 5, 6)
BRAILLE_DIGITS = {
    '1': (1,), '2': (1, 2), '3': (1, 4), '4': (1, 4, 5), '5': (1, 5),
    '6': (1, 2, 4), '7': (1, 2, 4, 5), '8': (1, 2, 5), '9': (2, 4),
    '0': (2, 4, 5),
}


def braille_dot_positions(pitch=BRAILLE_DOT_PITCH_MM):
    """Dot offsets (1-6) within a cell, standard 2x3 grid at `pitch`.
       1 4
       2 5      (x, y) is the CENTRE of dot 3 (bottom-left).
       3 6
    """
    return {
        1: (0, pitch * 2), 2: (0, pitch), 3: (0, 0),
        4: (pitch, pitch * 2), 5: (pitch, pitch), 6: (pitch, 0),
    }


def create_braille_cell_dots(dots, x, y, z):
    """Braille dots for an explicit dot tuple (1-6) at standard pitch."""
    pos = braille_dot_positions()
    all_verts, all_faces, vert_offset = [], [], 0
    for dot in dots:
        dx, dy = pos[dot]
        dot_verts, dot_faces = create_braille_dot(x + dx, y + dy, z)
        if len(dot_verts) > 0:
            all_verts.append(dot_verts)
            all_faces.append(dot_faces + vert_offset)
            vert_offset += len(dot_verts)
    if all_verts:
        return np.vstack(all_verts), np.vstack(all_faces)
    return np.array([]), np.array([])


def create_braille_char(char, x, y, z):
    """Create braille character at position (standard Marburg Medium cell)."""
    char = char.lower()
    if char not in BRAILLE:
        return np.array([]), np.array([])
    dots = BRAILLE[char]
    if not dots:
        return np.array([]), np.array([])
    return create_braille_cell_dots(dots, x, y, z)


def create_braille_text(text, x, y, z):
    """Create braille text string at standard cell pitch (6.0 mm)."""
    all_verts = []
    all_faces = []
    vert_offset = 0

    for i, char in enumerate(text):
        char_x = x + i * BRAILLE_CELL_PITCH_MM
        char_verts, char_faces = create_braille_char(char, char_x, y, z)
        if len(char_verts) > 0:
            all_verts.append(char_verts)
            all_faces.append(char_faces + vert_offset)
            vert_offset += len(char_verts)

    if all_verts:
        return np.vstack(all_verts), np.vstack(all_faces)
    return np.array([]), np.array([])


def braille_number_cells(number_str):
    """Dot tuples for a number label (optionally prefixed with ⠼)."""
    cells = [NUMBER_SIGN_DOTS] if NUMBER_SIGN else []
    cells += [BRAILLE_DIGITS[d] for d in number_str if d in BRAILLE_DIGITS]
    return cells


# Extra width the anchor ridge adds to the LEFT of the dot field: the ridge
# itself plus the clear gap between it and the nearest dot edge.
ANCHOR_LEAD_MM = BRAILLE_ANCHOR_WIDTH_MM + BRAILLE_ANCHOR_GAP_MM


def braille_label_size(number_str):
    """(width, height) in mm of a braille number label incl. anchor + dots."""
    n = len(braille_number_cells(number_str))
    dots_w = (n - 1) * BRAILLE_CELL_PITCH_MM + BRAILLE_DOT_PITCH_MM \
        + 2 * BRAILLE_DOT_RADIUS_MM
    height = 2 * BRAILLE_DOT_PITCH_MM + 2 * BRAILLE_DOT_RADIUS_MM
    return dots_w + ANCHOR_LEAD_MM, height


def create_braille_anchor(x_right, cy, base_z):
    """Anchor ridge whose RIGHT face is at x_right, vertically centred on cy.

    Spans the full dot-row extent so its ends mark the top and bottom rows.
    Sits on the same skirt trick as the dots so heal_mesh does not sink it.
    """
    half_h = BRAILLE_DOT_PITCH_MM + BRAILLE_DOT_RADIUS_MM
    x = x_right - BRAILLE_ANCHOR_WIDTH_MM / 2
    return create_segment_box(
        x, cy - half_h, x, cy + half_h,
        base_z - BRAILLE_SKIRT_MM,
        BRAILLE_SKIRT_MM + BRAILLE_DOT_HEIGHT_MM,
        BRAILLE_ANCHOR_WIDTH_MM,
    )


def create_braille_number(number_str, cx, cy, base_z):
    """Braille number label CENTRED at (cx, cy), dots on top of base_z.

    Layout, left to right: anchor ridge, gap, then the braille cells.
    """
    cells = braille_number_cells(number_str)
    if not cells:
        return np.array([]), np.array([])
    n = len(cells)
    total_w, _ = braille_label_size(number_str)
    left = cx - total_w / 2                       # left edge of the whole label
    # dot-column centres start one dot radius in from the dot field's left edge
    x0 = left + ANCHOR_LEAD_MM + BRAILLE_DOT_RADIUS_MM
    y0 = cy - BRAILLE_DOT_PITCH_MM                # dot rows at cy-2.5, cy, cy+2.5

    all_verts, all_faces, vert_offset = [], [], 0

    def add(v, f):
        nonlocal vert_offset
        if len(v) > 0:
            all_verts.append(v)
            all_faces.append(f + vert_offset)
            vert_offset += len(v)

    add(*create_braille_anchor(left + BRAILLE_ANCHOR_WIDTH_MM, cy, base_z))
    for i, dots in enumerate(cells):
        add(*create_braille_cell_dots(dots, x0 + i * BRAILLE_CELL_PITCH_MM, y0, base_z))

    if all_verts:
        return np.vstack(all_verts), np.vstack(all_faces)
    return np.array([]), np.array([])


def create_legend_card(number_legend):
    """Create a legend card with numbers, country names in Braille, and texture samples."""
    from constants import CARD_WIDTH_MM, CARD_HEIGHT_MM

    print("Creating legend card...")

    all_verts = []
    all_faces = []
    vert_offset = 0

    # Card dimensions
    width = CARD_WIDTH_MM   # 200 mm
    height = CARD_HEIGHT_MM  # 160 mm
    base_z = 0

    # Create base plate
    base_verts = [
        [0, 0, -BASE_THICKNESS_MM],
        [width, 0, -BASE_THICKNESS_MM],
        [width, height, -BASE_THICKNESS_MM],
        [0, height, -BASE_THICKNESS_MM],
        [0, 0, base_z],
        [width, 0, base_z],
        [width, height, base_z],
        [0, height, base_z],
    ]
    base_faces = [
        [0, 2, 1], [0, 3, 2],  # bottom
        [4, 5, 6], [4, 6, 7],  # top
        [0, 1, 5], [0, 5, 4],  # front
        [2, 3, 7], [2, 7, 6],  # back
        [0, 4, 7], [0, 7, 3],  # left
        [1, 2, 6], [1, 6, 5],  # right
    ]
    all_verts.append(np.array(base_verts))
    all_faces.append(np.array(base_faces))
    vert_offset += len(base_verts)

    # Layout: 2 columns, braille number key + braille name, standard Marburg
    # cell pitch (2026-08-04: 7-segment numbers replaced by braille keys —
    # they must match the braille labels now used on the map itself).
    # rows is DYNAMIC = ceil(N / cols) so every numbered country fits on the
    # plate (FIXES #4.12). Line pitch ~8 mm is below the 10 mm book standard —
    # 16 rows simply don't fit a 160 mm card at 10 mm — but rows are short,
    # left-aligned and separated by >3 mm of flat plate.
    cols = 2
    rows = max(1, int(np.ceil(len(number_legend) / cols)))
    col_width = width / cols
    start_y = height - 16            # first row: bottom dot-row centre
    row_pitch = (start_y - 22) / max(1, rows - 1) if rows > 1 else 0
    max_chars = 12

    for idx, (num, iso) in enumerate(number_legend):
        name = name_en(iso) or iso
        col = idx // rows
        row = idx % rows

        x = col * col_width + 4
        y = start_y - row * row_pitch

        # Number key in braille (same cells as on the map)
        for i, dots in enumerate(braille_number_cells(str(num))):
            kv, kf = create_braille_cell_dots(
                dots, x + i * BRAILLE_CELL_PITCH_MM, y, base_z)
            if len(kv) > 0:
                all_verts.append(kv)
                all_faces.append(kf + vert_offset)
                vert_offset += len(kv)

        # Country name in Braille (truncate to fit)
        braille_x = x + 14
        short_name = name[:max_chars].lower()

        braille_verts, braille_faces = create_braille_text(
            short_name, braille_x, y, base_z
        )
        if len(braille_verts) > 0:
            all_verts.append(braille_verts)
            all_faces.append(braille_faces + vert_offset)
            vert_offset += len(braille_verts)

    # Texture samples: ONE bottom strip, braille label to the RIGHT of each
    # sample (frees vertical space for the standard-pitch rows above).
    sample_y = 6
    sample_height = 10
    sample_width = 25
    label_y = sample_y + 1

    # 1. Water sample (sinusoidal waves like on map) + label "sea"
    water_x = 10
    wave_segments = 20
    for wave_i in range(3):
        wave_base_y = sample_y + wave_i * 3.5
        for seg in range(wave_segments):
            x1 = water_x + seg * (sample_width / wave_segments)
            x2 = water_x + (seg + 1) * (sample_width / wave_segments)
            y1 = wave_base_y + 0.8 * np.sin(seg * 2 * np.pi / 5)
            y2 = wave_base_y + 0.8 * np.sin((seg + 1) * 2 * np.pi / 5)
            wave_verts, wave_faces = create_segment_box(
                x1, y1, x2, y2,
                base_z, WAVE_HEIGHT_MM, 0.8
            )
            if len(wave_verts) > 0:
                all_verts.append(wave_verts)
                all_faces.append(wave_faces + vert_offset)
                vert_offset += len(wave_verts)
    lbl_verts, lbl_faces = create_braille_text("sea", water_x + sample_width + 3,
                                               label_y, base_z)
    if len(lbl_verts) > 0:
        all_verts.append(lbl_verts)
        all_faces.append(lbl_faces + vert_offset)
        vert_offset += len(lbl_verts)

    # 2. Border sample (ridge) + label "border".
    # Height = BOUNDARY_RELIEF_MM so the sample feels like the ACTUAL map
    # border (a low ridge over local relief), not the legacy 4.5 mm wall.
    border_x = 78
    border_verts, border_faces = create_segment_box(
        border_x, sample_y, border_x, sample_y + sample_height,
        base_z, BOUNDARY_RELIEF_MM, BOUNDARY_WIDTH_MM
    )
    if len(border_verts) > 0:
        all_verts.append(border_verts)
        all_faces.append(border_faces + vert_offset)
        vert_offset += len(border_verts)
    lbl_verts, lbl_faces = create_braille_text("border", border_x + 5,
                                               label_y, base_z)
    if len(lbl_verts) > 0:
        all_verts.append(lbl_verts)
        all_faces.append(lbl_faces + vert_offset)
        vert_offset += len(lbl_verts)

    # 3. Anchor-ridge sample + label "key": the ridge that marks the left edge
    # and row extent of every number label on the map (capital bumps were
    # removed 2026-08-05, so the old "city" sample went with them).
    key_x = 150
    kv, kf = create_braille_anchor(key_x, sample_y + sample_height / 2, base_z)
    if len(kv) > 0:
        all_verts.append(kv)
        all_faces.append(kf + vert_offset)
        vert_offset += len(kv)
    kv, kf = create_braille_cell_dots(
        (1, 2, 3), key_x + ANCHOR_LEAD_MM + BRAILLE_DOT_RADIUS_MM,
        sample_y + sample_height / 2 - BRAILLE_DOT_PITCH_MM, base_z)
    if len(kv) > 0:
        all_verts.append(kv)
        all_faces.append(kf + vert_offset)
        vert_offset += len(kv)
    lbl_verts, lbl_faces = create_braille_text("key", key_x + 14, label_y, base_z)
    if len(lbl_verts) > 0:
        all_verts.append(lbl_verts)
        all_faces.append(lbl_faces + vert_offset)
        vert_offset += len(lbl_verts)

    vertices = np.vstack(all_verts)
    faces = np.vstack(all_faces)
    print(f"  Legend: {len(faces)} triangles")

    return vertices, faces


def _trapezoid_prism(x, y, direction, neck_hw, head_hw, depth, z_bottom, z_top,
                     back=0.0):
    """Prism whose XY section is a symmetric trapezoid: neck (width 2*neck_hw)
    at the card edge (x, y), head (width 2*head_hw) `depth` mm outward along
    `direction`. `back` extends the neck side INWARD past the edge (used by the
    slot cutter for a clean boolean cut through the wall)."""
    if direction == 'right':    # outward = +x
        base = [(x - back, y - neck_hw), (x + depth, y - head_hw),
                (x + depth, y + head_hw), (x - back, y + neck_hw)]
    elif direction == 'left':   # outward = -x
        base = [(x - depth, y - head_hw), (x + back, y - neck_hw),
                (x + back, y + neck_hw), (x - depth, y + head_hw)]
    elif direction == 'up':     # outward = +y
        base = [(x - neck_hw, y - back), (x + neck_hw, y - back),
                (x + head_hw, y + depth), (x - head_hw, y + depth)]
    elif direction == 'down':   # outward = -y
        base = [(x - head_hw, y - depth), (x + head_hw, y - depth),
                (x + neck_hw, y + back), (x - neck_hw, y + back)]
    else:
        return np.array([]), np.array([])

    verts = [[px, py, z_bottom] for px, py in base] + \
            [[px, py, z_top] for px, py in base]
    faces = [
        [0, 2, 1], [0, 3, 2],  # bottom
        [4, 5, 6], [4, 6, 7],  # top
        [0, 1, 5], [0, 5, 4],
        [1, 2, 6], [1, 6, 5],
        [2, 3, 7], [2, 7, 6],
        [3, 0, 4], [3, 4, 7],
    ]
    return np.array(verts, dtype=float), np.array(faces)


def create_tab(x, y, direction):
    """Create a DOVETAIL puzzle tab extending from the side wall of the base.

    Trapezoid in plan: neck TAB_WIDTH_MM at the card edge, head
    TAB_HEAD_WIDTH_MM at the tip — the mating card is lowered onto it from
    above and then cannot slide apart sideways (2026-08-04; the old
    rectangular tabs let the assembled map drift apart).
    Tab occupies the BOTTOM part of base (z from -BASE to -BASE+TAB_HEIGHT).
    """
    z_bottom = -BASE_THICKNESS_MM                      # -6
    z_top = -BASE_THICKNESS_MM + TAB_HEIGHT_MM         # -3
    return _trapezoid_prism(x, y, direction,
                            neck_hw=TAB_WIDTH_MM / 2,
                            head_hw=TAB_HEAD_WIDTH_MM / 2,
                            depth=TAB_DEPTH_MM,
                            z_bottom=z_bottom, z_top=z_top)


def create_slot_cutter(x, y, direction):
    """Mesh to boolean-SUBTRACT from the receiving card: the dovetail tab
    offset so every face clears the tab by SLOT_CLEARANCE_MM/2 measured
    PERPENDICULAR to that face, extended 1 mm inward past the card edge for a
    clean through-wall cut.

    The slot's slanted flanks are kept PARALLEL to the tab's flanks: a naive
    "+clearance/2 on each half-width" pivots the flank around the back plane
    and the gap collapses to ~0.12 mm at the head corner — the load-bearing
    dovetail face — which jams on FDM over-extrusion (review 2026-08-04).

    `direction` is where the mating tab points INTO this card: a card whose
    LEFT edge receives a neighbour's 'right' tab gets a 'right' cutter at
    (0, y). The slot stays open at the card bottom, so assembly is: lay one
    card flat, lower the neighbour onto the tab from above.
    """
    import math
    z_bottom = -BASE_THICKNESS_MM - 0.01
    z_top = -BASE_THICKNESS_MM + TAB_HEIGHT_MM + SLOT_Z_CLEARANCE_MM
    back = 1.0
    m = (TAB_HEAD_WIDTH_MM - TAB_WIDTH_MM) / 2 / TAB_DEPTH_MM  # flank slope
    c_perp = (SLOT_CLEARANCE_MM / 2) / math.cos(math.atan(m))  # width offset
    depth = TAB_DEPTH_MM + SLOT_CLEARANCE_MM / 2
    # tab flank: hw(t) = TAB_WIDTH/2 + m*t; cutter flank = parallel + c_perp,
    # evaluated at the cutter's own end planes t=-back and t=depth.
    return _trapezoid_prism(x, y, direction,
                            neck_hw=TAB_WIDTH_MM / 2 - m * back + c_perp,
                            head_hw=TAB_WIDTH_MM / 2 + m * depth + c_perp,
                            depth=depth,
                            z_bottom=z_bottom, z_top=z_top,
                            back=back)


def get_slot_bounds(x, y, direction):
    """Get bounding box for a slot (hole) to receive a tab.

    Returns (x_min, x_max, y_min, y_max) of the slot area.
    Slot is slightly larger than tab for clearance.
    """
    hw = (TAB_WIDTH_MM + SLOT_CLEARANCE_MM) / 2
    td = TAB_DEPTH_MM + SLOT_CLEARANCE_MM

    if direction == 'left':
        return (0, td, y - hw, y + hw)
    elif direction == 'bottom':
        return (x - hw, x + hw, 0, td)
    elif direction == 'right':
        return (200 - td, 200, y - hw, y + hw)
    elif direction == 'top':
        return (x - hw, x + hw, 160 - td, 160)

    return None


def get_slot_regions_for_card(card_idx, card_width, card_height):
    """Get list of slot regions (holes) for a card.

    Returns list of (x_min, x_max, y_min, y_max) bounds in card-local coordinates.
    """
    h_center = card_height / 2
    v_center = card_width / 2
    slots = []

    # Card 1 (bottom-right): receives tab from card 0 on left edge
    if card_idx == 1:
        slots.append(get_slot_bounds(0, h_center, 'left'))

    # Card 2 (top-left): receives tab from card 0 on bottom edge
    elif card_idx == 2:
        slots.append(get_slot_bounds(v_center, 0, 'bottom'))

    # Card 3 (top-right): receives tabs from card 1 (bottom) and card 2 (left)
    elif card_idx == 3:
        slots.append(get_slot_bounds(0, h_center, 'left'))  # from card 2
        slots.append(get_slot_bounds(v_center, 0, 'bottom'))  # from card 1

    return slots


def create_slot_walls(slots):
    """Create walls around slot openings to make the mesh watertight.

    For each slot, creates the 3 internal walls (back and two sides).
    The open side faces the edge of the card where the tab enters.
    Slot is only in the BOTTOM part of base (same height as tab).
    """
    all_verts = []
    all_faces = []
    offset = 0

    # Slot is in the bottom part of base, same as tab
    z_bottom = -BASE_THICKNESS_MM                      # -6
    z_top = -BASE_THICKNESS_MM + TAB_HEIGHT_MM         # -3

    for slot in slots:
        if slot is None:
            continue

        x_min, x_max, y_min, y_max = slot

        # Determine which edge the slot is on
        is_left_edge = x_min < 0.1  # slot on left edge
        is_bottom_edge = y_min < 0.1  # slot on bottom edge

        if is_left_edge:
            # Back wall (at x = x_max)
            verts = [
                [x_max, y_min, z_bottom], [x_max, y_max, z_bottom],
                [x_max, y_max, z_top], [x_max, y_min, z_top],
            ]
            faces = [[0, 1, 2], [0, 2, 3]]  # facing -X
            all_verts.append(np.array(verts))
            all_faces.append(np.array(faces) + offset)
            offset += 4

            # Top wall of slot (y = y_max)
            verts = [
                [0, y_max, z_bottom], [x_max, y_max, z_bottom],
                [x_max, y_max, z_top], [0, y_max, z_top],
            ]
            faces = [[0, 2, 1], [0, 3, 2]]  # facing +Y
            all_verts.append(np.array(verts))
            all_faces.append(np.array(faces) + offset)
            offset += 4

            # Bottom wall of slot (y = y_min)
            verts = [
                [0, y_min, z_bottom], [x_max, y_min, z_bottom],
                [x_max, y_min, z_top], [0, y_min, z_top],
            ]
            faces = [[0, 1, 2], [0, 2, 3]]  # facing -Y
            all_verts.append(np.array(verts))
            all_faces.append(np.array(faces) + offset)
            offset += 4

            # Floor of slot (z = z_bottom) - NO, keep open for tab

        elif is_bottom_edge:
            # Back wall (at y = y_max)
            verts = [
                [x_min, y_max, z_bottom], [x_max, y_max, z_bottom],
                [x_max, y_max, z_top], [x_min, y_max, z_top],
            ]
            faces = [[0, 2, 1], [0, 3, 2]]  # facing +Y
            all_verts.append(np.array(verts))
            all_faces.append(np.array(faces) + offset)
            offset += 4

            # Left wall of slot (x = x_min)
            verts = [
                [x_min, 0, z_bottom], [x_min, y_max, z_bottom],
                [x_min, y_max, z_top], [x_min, 0, z_top],
            ]
            faces = [[0, 1, 2], [0, 2, 3]]  # facing -X
            all_verts.append(np.array(verts))
            all_faces.append(np.array(faces) + offset)
            offset += 4

            # Right wall of slot (x = x_max)
            verts = [
                [x_max, 0, z_bottom], [x_max, y_max, z_bottom],
                [x_max, y_max, z_top], [x_max, 0, z_top],
            ]
            faces = [[0, 2, 1], [0, 3, 2]]  # facing +X
            all_verts.append(np.array(verts))
            all_faces.append(np.array(faces) + offset)
            offset += 4

    if not all_verts:
        return np.array([]), np.array([])

    return np.vstack(all_verts), np.vstack(all_faces)


def point_in_slot(x, y, z, slots):
    """Check if point (x, y, z) is inside any slot region.

    Only removes geometry in the BOTTOM part of base (z < slot_z_top).
    This leaves terrain and upper base intact.
    """
    # Slot occupies z from -BASE_THICKNESS to -BASE_THICKNESS + TAB_HEIGHT
    # i.e. from -6 to -3
    slot_z_top = -BASE_THICKNESS_MM + TAB_HEIGHT_MM  # -3

    # Only affect the bottom part of base where slot is
    if z > slot_z_top:
        return False

    for slot in slots:
        if slot is None:
            continue
        x_min, x_max, y_min, y_max = slot
        if x_min <= x <= x_max and y_min <= y <= y_max:
            return True
    return False


def create_inner_side_wall(card_verts, edge, card_width, card_height, slots=None):
    """Create side wall for inner edge of card (where it meets other cards).

    edge: 'right', 'left', 'top', 'bottom'
    Returns vertices and faces for the wall.

    For edges with slots:
    - Upper part (terrain to slot_z_top): solid wall
    - Lower part (slot_z_top to bottom): wall with hole for slot
    """
    z_bottom = -BASE_THICKNESS_MM
    slot_z_top = -BASE_THICKNESS_MM + TAB_HEIGHT_MM  # -3

    # Find terrain surface vertices on the edge.
    # Tolerance must be tight: grid spacing is ~1 mm, so vertices on the
    # card boundary sit within ~0.5 mm of it. Larger tolerance (e.g. 3 mm)
    # catches off-edge wall vertices and produces chaotic inner walls.
    tolerance = 0.5

    if edge == 'right':
        x = card_width
        edge_verts = [(v[1], v[2]) for v in card_verts if abs(v[0] - x) < tolerance and v[2] > 0]
    elif edge == 'left':
        x = 0
        edge_verts = [(v[1], v[2]) for v in card_verts if abs(v[0]) < tolerance and v[2] > 0]
    elif edge == 'top':
        y = card_height
        edge_verts = [(v[0], v[2]) for v in card_verts if abs(v[1] - y) < tolerance and v[2] > 0]
    elif edge == 'bottom':
        y = 0
        edge_verts = [(v[0], v[2]) for v in card_verts if abs(v[1]) < tolerance and v[2] > 0]
    else:
        return np.array([]), np.array([])

    # If no terrain verts found, create simple wall at z=0
    if not edge_verts:
        # Create uniform wall along edge
        n_segments = 20
        if edge in ['right', 'left']:
            positions = np.linspace(0, card_height, n_segments + 1)
        else:
            positions = np.linspace(0, card_width, n_segments + 1)
        edge_verts = [(p, 0.0) for p in positions]
    else:
        edge_verts = sorted(set(edge_verts), key=lambda p: p[0])

    if len(edge_verts) < 2:
        return np.array([]), np.array([])

    # Get slot range for this edge
    slot_range = None
    if slots:
        for slot in slots:
            if slot is None:
                continue
            sx_min, sx_max, sy_min, sy_max = slot
            if edge in ['right', 'left']:
                slot_range = (sy_min, sy_max)
            else:
                slot_range = (sx_min, sx_max)
            break

    all_wall_verts = []
    all_wall_faces = []
    vert_offset = 0

    for i in range(len(edge_verts) - 1):
        pos1, z1 = edge_verts[i]
        pos2, z2 = edge_verts[i + 1]

        # Skip zero-length segments. Duplicates in edge_verts can arise when
        # two vertices share the same along-edge coordinate but differ in z
        # (e.g. terrain sample + boundary-wall vertex at the same y). Without
        # this guard we emit a degenerate quad with two coincident vertices,
        # producing zero-area triangles that pollute the mesh (FIXES.md #2.2).
        if abs(pos2 - pos1) < 0.01:
            continue

        # Check if this segment overlaps with slot
        in_slot = False
        if slot_range:
            s_min, s_max = slot_range
            if not (pos2 <= s_min or pos1 >= s_max):
                in_slot = True

        if in_slot:
            z_wall_bottom = slot_z_top
        else:
            z_wall_bottom = z_bottom

        if edge == 'right':
            verts = [
                [x, pos1, z1], [x, pos2, z2],
                [x, pos2, z_wall_bottom], [x, pos1, z_wall_bottom],
            ]
        elif edge == 'left':
            verts = [
                [0, pos1, z1], [0, pos2, z2],
                [0, pos2, z_wall_bottom], [0, pos1, z_wall_bottom],
            ]
        elif edge == 'top':
            verts = [
                [pos1, y, z1], [pos2, y, z2],
                [pos2, y, z_wall_bottom], [pos1, y, z_wall_bottom],
            ]
        else:  # bottom
            verts = [
                [pos1, 0, z1], [pos2, 0, z2],
                [pos2, 0, z_wall_bottom], [pos1, 0, z_wall_bottom],
            ]

        # Winding must give an outward-pointing normal (away from card interior).
        # Verts laid out as: v0=(edge, pos1, z_top1), v1=(edge, pos2, z_top2),
        #                    v2=(edge, pos2, z_bot),  v3=(edge, pos1, z_bot).
        # cross((v1-v0), (v2-v0)) for [[0,1,2],[0,2,3]] yields:
        #   - x=const planes (left/right): normal in -X direction
        #   - y=const planes (top/bottom): normal in +Y direction
        # Outward directions per edge (card interior is always on the other side):
        #   right  -> +X (need flip)    left   -> -X (keep)
        #   top    -> +Y (keep)         bottom -> -Y (need flip)
        # So 'top' pairs with 'left', 'bottom' pairs with 'right'.
        if edge in ['top', 'left']:
            faces = [[0, 1, 2], [0, 2, 3]]
        else:  # 'bottom', 'right'
            faces = [[0, 2, 1], [0, 3, 2]]

        all_wall_verts.append(np.array(verts))
        all_wall_faces.append(np.array(faces) + vert_offset)
        vert_offset += 4

    if not all_wall_verts:
        return np.array([]), np.array([])

    return np.vstack(all_wall_verts), np.vstack(all_wall_faces)


def add_connectors_to_card(card_verts, card_faces, card_idx, card_width, card_height):
    """Add puzzle tabs, slot walls, and inner side walls to cards.

    card_idx: 0=bottom-left, 1=bottom-right, 2=top-left, 3=top-right

    Cards 0, 1, 2 get tabs. Cards 1, 2, 3 get slot walls.
    All cards get inner side walls where they meet other cards.
    """
    all_verts = [card_verts]
    all_faces = [card_faces]
    offset = len(card_verts)

    h_center = card_height / 2
    v_center = card_width / 2

    # Add tabs
    if card_idx == 0:
        # Tab on right edge (→card 1)
        v, f = create_tab(card_width, h_center, 'right')
        if len(v) > 0:
            all_verts.append(v)
            all_faces.append(f + offset)
            offset += len(v)
        # Tab on top edge (↑card 2)
        v, f = create_tab(v_center, card_height, 'up')
        if len(v) > 0:
            all_verts.append(v)
            all_faces.append(f + offset)
            offset += len(v)
    elif card_idx == 1:
        # Tab on top edge (↑card 3)
        v, f = create_tab(v_center, card_height, 'up')
        if len(v) > 0:
            all_verts.append(v)
            all_faces.append(f + offset)
            offset += len(v)
    elif card_idx == 2:
        # Tab on right edge (→card 3)
        v, f = create_tab(card_width, h_center, 'right')
        if len(v) > 0:
            all_verts.append(v)
            all_faces.append(f + offset)
            offset += len(v)

    # Add slot walls
    slots = get_slot_regions_for_card(card_idx, card_width, card_height)
    if slots:
        v, f = create_slot_walls(slots)
        if len(v) > 0:
            all_verts.append(v)
            all_faces.append(f + offset)
            offset += len(v)

    # Add inner side walls (where card meets other cards)
    # Card 0: right, top; Card 1: left, top; Card 2: right, bottom; Card 3: left, bottom
    inner_edges = {
        0: ['right', 'top'],
        1: ['left', 'top'],
        2: ['right', 'bottom'],
        3: ['left', 'bottom'],
    }

    for edge in inner_edges.get(card_idx, []):
        # Get slots that affect this edge
        edge_slots = None
        if slots:
            if edge == 'left' and card_idx in [1, 3]:
                edge_slots = [s for s in slots if s and s[0] < 1]  # slot on left
            elif edge == 'bottom' and card_idx in [2, 3]:
                edge_slots = [s for s in slots if s and s[2] < 1]  # slot on bottom

        v, f = create_inner_side_wall(card_verts, edge, card_width, card_height, edge_slots)
        if len(v) > 0:
            all_verts.append(v)
            all_faces.append(f + offset)
            offset += len(v)

    return np.vstack(all_verts), np.vstack(all_faces)


def split_mesh_to_cards(vertices, faces):
    """Split mesh into 4 cards (2x2 grid) with puzzle connectors."""
    from constants import CARD_WIDTH_MM, CARD_HEIGHT_MM

    print("Splitting into 4 cards with puzzle connectors...")

    # Card boundaries:
    # card_0: bottom-left  (0, 0) to (200, 160)
    # card_1: bottom-right (200, 0) to (400, 160)
    # card_2: top-left     (0, 160) to (200, 320)
    # card_3: top-right    (200, 160) to (400, 320)

    cards = []
    card_bounds = [
        (0, 0, CARD_WIDTH_MM, CARD_HEIGHT_MM),                              # card 0
        (CARD_WIDTH_MM, 0, CARD_WIDTH_MM * 2, CARD_HEIGHT_MM),              # card 1
        (0, CARD_HEIGHT_MM, CARD_WIDTH_MM, CARD_HEIGHT_MM * 2),             # card 2
        (CARD_WIDTH_MM, CARD_HEIGHT_MM, CARD_WIDTH_MM * 2, CARD_HEIGHT_MM * 2),  # card 3
    ]

    for card_idx, (x_min, y_min, x_max, y_max) in enumerate(card_bounds):
        # Get slot regions for this card (in card-local coordinates)
        slots = get_slot_regions_for_card(card_idx, CARD_WIDTH_MM, CARD_HEIGHT_MM)

        # Find faces where all 3 vertices are within card bounds
        card_faces_list = []
        used_verts = set()

        tol = 0.1

        for face in faces:
            v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]

            # Check if ALL vertices are within card bounds
            v0_in = (x_min - tol <= v0[0] <= x_max + tol) and (y_min - tol <= v0[1] <= y_max + tol)
            v1_in = (x_min - tol <= v1[0] <= x_max + tol) and (y_min - tol <= v1[1] <= y_max + tol)
            v2_in = (x_min - tol <= v2[0] <= x_max + tol) and (y_min - tol <= v2[1] <= y_max + tol)

            if not (v0_in and v1_in and v2_in):
                continue

            # Convert to card-local coordinates for slot check
            local_v0 = (v0[0] - x_min, v0[1] - y_min, v0[2])
            local_v1 = (v1[0] - x_min, v1[1] - y_min, v1[2])
            local_v2 = (v2[0] - x_min, v2[1] - y_min, v2[2])

            # Skip faces where ANY vertex is in a slot region (only side walls, not bottom)
            if slots:
                # Check if this is a bottom face (all vertices at z=-BASE_THICKNESS)
                # Bottom faces should NOT be removed
                bottom_z = -BASE_THICKNESS_MM
                all_at_bottom = (
                    abs(v0[2] - bottom_z) < 0.1 and
                    abs(v1[2] - bottom_z) < 0.1 and
                    abs(v2[2] - bottom_z) < 0.1
                )
                if not all_at_bottom:
                    # Only check slot for side wall faces
                    in_slot = (
                        point_in_slot(local_v0[0], local_v0[1], local_v0[2], slots) or
                        point_in_slot(local_v1[0], local_v1[1], local_v1[2], slots) or
                        point_in_slot(local_v2[0], local_v2[1], local_v2[2], slots)
                    )
                    if in_slot:
                        continue

            card_faces_list.append(face)
            used_verts.update(face)

        if not card_faces_list:
            cards.append((np.array([]), np.array([])))
            continue

        # Remap vertices
        old_to_new = {}
        new_verts = []
        for old_idx in sorted(used_verts):
            old_to_new[old_idx] = len(new_verts)
            v = vertices[old_idx].copy()
            v[0] -= x_min
            v[1] -= y_min
            new_verts.append(v)

        # Remap faces
        new_faces = []
        for face in card_faces_list:
            new_faces.append([old_to_new[face[0]], old_to_new[face[1]], old_to_new[face[2]]])

        # Add puzzle connectors (tabs)
        card_verts_arr = np.array(new_verts)
        card_faces_arr = np.array(new_faces)
        card_verts_arr, card_faces_arr = add_connectors_to_card(
            card_verts_arr, card_faces_arr, card_idx, CARD_WIDTH_MM, CARD_HEIGHT_MM
        )

        cards.append((card_verts_arr, card_faces_arr))
        slot_info = f" (slots: {len(slots)})" if slots else ""
        print(f"  Card {card_idx + 1}: {len(card_faces_arr)} triangles{slot_info}")

    return cards


def save_stl(vertices, faces, filename):
    """Save mesh to binary STL file."""
    print(f"Saving STL to {filename}...")

    with open(filename, 'wb') as f:
        # Header (80 bytes)
        f.write(b'\x00' * 80)

        # Number of triangles
        f.write(np.uint32(len(faces)).tobytes())

        # Triangles
        for face in faces:
            v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]

            # Normal (not computed, set to 0)
            f.write(np.float32([0, 0, 0]).tobytes())

            # Vertices
            f.write(np.float32(v0).tobytes())
            f.write(np.float32(v1).tobytes())
            f.write(np.float32(v2).tobytes())

            # Attribute byte count
            f.write(np.uint16(0).tobytes())

    print(f"  Saved {len(faces)} triangles")


def main():
    print("=" * 50)
    print("TACTILE MAP GENERATOR")
    print("=" * 50)
    print(f"Map bounds: {MAP_BOUNDS}")
    print(f"Output size: {FULL_WIDTH_MM} x {FULL_HEIGHT_MM} mm")
    print()

    # Check input files
    if not ELEVATION_FILE.exists():
        print(f"ERROR: Elevation file not found: {ELEVATION_FILE}")
        return
    if not BOUNDARIES_FILE.exists():
        print(f"ERROR: Boundaries file not found: {BOUNDARIES_FILE}")
        return

    # Load elevation
    X, Y, Z, lon_deg, lat_deg = load_elevation()

    # Load filtered boundaries (no small islands) - use for both water mask and walls
    gdf_filtered = load_boundaries_filtered()

    # Create water mask from filtered boundaries
    # Small islands will be treated as water (get waves)
    water_mask = create_water_mask(lon_deg, lat_deg, gdf_filtered)

    # Flatten water areas (remove island elevation bumps)
    Z[water_mask] = 0

    # Add wave pattern to water
    waves = create_wave_pattern(X, Y, water_mask)
    Z = Z + waves

    # Create terrain mesh
    terrain_verts, terrain_faces = create_terrain_mesh(X, Y, Z)
    boundary_verts, boundary_faces = create_boundary_walls(gdf_filtered)
    capital_verts, capital_faces, number_legend = create_capitals_mesh(X, Y, Z, gdf_filtered)

    # Combine meshes
    all_verts = terrain_verts
    all_faces = terrain_faces

    if len(boundary_verts) > 0:
        boundary_faces_shifted = boundary_faces + len(all_verts)
        all_verts = np.vstack([all_verts, boundary_verts])
        all_faces = np.vstack([all_faces, boundary_faces_shifted])

    if len(capital_verts) > 0:
        capital_faces_shifted = capital_faces + len(all_verts)
        all_verts = np.vstack([all_verts, capital_verts])
        all_faces = np.vstack([all_faces, capital_faces_shifted])

    # Save full map
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    save_stl(all_verts, all_faces, OUTPUT_FILE)

    # Split into 4 cards
    cards = split_mesh_to_cards(all_verts, all_faces)
    for i, (card_verts, card_faces) in enumerate(cards):
        if len(card_faces) > 0:
            card_file = OUTPUT_FILE.parent / f"card_{i + 1}.stl"
            save_stl(card_verts, card_faces, card_file)

    # Create legend card
    legend_verts, legend_faces = create_legend_card(number_legend)
    legend_file = OUTPUT_FILE.parent / "card_legend.stl"
    save_stl(legend_verts, legend_faces, legend_file)

    # Save text legend
    legend_txt = OUTPUT_FILE.parent / "legend.txt"
    with open(legend_txt, 'w', encoding='utf-8') as f:
        f.write("ТАКТИЛЬНАЯ КАРТА — ЛЕГЕНДА\n")
        f.write("=" * 40 + "\n\n")
        for num, name in number_legend:
            f.write(f"{num:2d}. {name}\n")
        f.write("\n" + "=" * 40 + "\n")
        f.write("ТЕКСТУРЫ:\n")
        f.write("  Волны     = вода (море)\n")
        f.write("  Плоское   = суша\n")
        f.write("  Стенка    = граница страны\n")
        f.write("  Бугорок   = столица\n")
    print(f"Saved legend: {legend_txt}")

    print()
    print("=" * 50)
    print("DONE!")
    print(f"Full map: {OUTPUT_FILE}")
    print(f"Cards: card_1.stl ... card_4.stl + card_legend.stl")
    print(f"Card size: 200 x 160 mm")
    print(f"Legend: legend.txt")
    print("=" * 50)


if __name__ == "__main__":
    # Legacy path DISABLED (2026-08-04): it pairs the new 13 mm dovetail tabs
    # with the old 8.5 mm rectangular slots (get_slot_bounds/create_slot_walls)
    # — the printed cards physically cannot be assembled. The supported
    # pipeline is build_all.py, which cuts cards with boolean split_cards +
    # create_slot_cutter.
    print("This legacy entry point is disabled: it produces cards whose")
    print("dovetail tabs do not match its old rectangular slots.")
    print("Use:  python core/build_all.py   (run from the repo root)")
