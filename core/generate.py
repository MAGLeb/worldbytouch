#!/usr/bin/env python3
"""
Mesh building blocks for the tactile map: elevation, water mask and waves,
terrain, braille number labels, braille text, legend card, dovetail tabs.

Not an entry point — build_all.py drives the print-ready build and calls into
this module.
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
    BOUNDARY_WIDTH_MM, BOUNDARY_RELIEF_MM,
    WAVE_HEIGHT_MM, WAVE_INTERVAL_MM,
    TAB_HEIGHT_MM, TAB_DEPTH_MM, TAB_WIDTH_MM, TAB_HEAD_WIDTH_MM,
    SLOT_CLEARANCE_MM, SLOT_Z_CLEARANCE_MM,
    BRAILLE_DOT_RADIUS_MM, BRAILLE_DOT_HEIGHT_MM, BRAILLE_DOT_PITCH_MM,
    BRAILLE_CELL_PITCH_MM, BRAILLE_SKIRT_MM,
    BRAILLE_ANCHOR_WIDTH_MM, BRAILLE_ANCHOR_GAP_MM,
)
from countries import COUNTRIES, name_en


# Paths
BASE_DIR = Path(__file__).parent.parent
ELEVATION_FILE = BASE_DIR / "data" / "input" / "ETOPO1_Bed_g_gmt4.grd"
BOUNDARIES_FILE = BASE_DIR / "data" / "output" / "merged_countries.geojson"


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
# Границы стран — скелет линий
# ============================================================================
# Сами гребни строит walls_buffer (buffer + manifold extrude по рельефу);
# отсюда он берёт только развёртку геометрии в плоские LineString'и.


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


def create_segment_box(x1, y1, x2, y2, base_z, height, width):
    """Create a 3D box along the (x1,y1)->(x2,y2) segment.

    Used by the legend cards for the wave and border texture samples."""
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
