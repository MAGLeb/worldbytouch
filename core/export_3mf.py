#!/usr/bin/env python3
"""
Build the MakerWorld upload bundle into data/output/makerworld/:
  * ONE Bambu Studio / OrcaSlicer project .3mf with every card pre-arranged on
    its own plate and named,
  * the same cards as STLs renamed to human-readable names (MakerWorld shows
    file names to visitors).
Both are generated artefacts, so they live under data/ with the rest of the
build output (gitignored) — the upload copy text lives in docs/MAKERWORLD.md.

Format taken from the BambuStudio source (src/libslic3r/Format/bbs_3mf.cpp and
PartPlate.cpp), not from guesswork:
  * plate grid:  cols = compute_colum_count(n) = round(sqrt(n)) (+1 if sqrt >
    round), origin_x = col * bed_w * 1.2, origin_y = -row * bed_d * 1.2
    (LOGICAL_PART_PLATE_GAP = 1/5).
  * Metadata/model_settings.config carries object names and the
    plate -> model_instance (object_id/instance_id) assignment.

Deliberately NO Metadata/project_settings.config: it would pin a printer and
filament profile we cannot know, and Bambu would then load presets for a
machine the user may not own. Opening without it keeps the user's own selected
printer/process presets; the recommended 0.2 mm / 15-20 % PLA settings live in
makerworld/LISTING.md instead.
"""
import shutil
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
import trimesh

BED_W = BED_D = 256.0          # Bambu A1 / P1S / X1C build plate
PLATE_GAP = 1.0 / 5.0          # LOGICAL_PART_PLATE_GAP

# (source stl, plate name / object name)
CARDS = [
    ("card_1.stl", "Tactile Map - Card 1 of 4 - South-West (North Africa)"),
    ("card_2.stl", "Tactile Map - Card 2 of 4 - South-East (Arabia)"),
    ("card_3.stl", "Tactile Map - Card 3 of 4 - North-West (Europe)"),
    ("card_4.stl", "Tactile Map - Card 4 of 4 - North-East (Caucasus)"),
    ("card_legend.stl", "Braille Legend - English"),
    ("card_legend_sr.stl", "Braille Legend - Serbian"),
    ("card_alphabet.stl", "Braille Alphabet Card - English"),
    ("card_alphabet_sr.stl", "Braille Alphabet Card - Serbian"),
]

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
 <Default Extension="png" ContentType="image/png"/>
 <Default Extension="gcode" ContentType="text/x.gcode"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>"""


def compute_colum_count(count):
    """Verbatim port of PartPlate.hpp compute_colum_count."""
    value = np.sqrt(float(count))
    round_value = np.round(value)
    return int(round_value + 1) if value > round_value else int(round_value)


def plate_origin(index, cols):
    """Lower-left corner of plate `index` in global coords (PartPlate.cpp)."""
    row, col = divmod(index, cols)
    return col * BED_W * (1.0 + PLATE_GAP), -row * BED_D * (1.0 + PLATE_GAP)


def mesh_xml(mesh):
    """<mesh> body: vertices centred in XY on the object origin, sitting on z=0."""
    v = np.asarray(mesh.vertices, dtype=float)
    lo, hi = v.min(axis=0), v.max(axis=0)
    v = v - np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])

    out = ["   <mesh>\n    <vertices>\n"]
    out.extend("     <vertex x=\"%.4f\" y=\"%.4f\" z=\"%.4f\"/>\n" % tuple(p) for p in v)
    out.append("    </vertices>\n    <triangles>\n")
    out.extend("     <triangle v1=\"%d\" v2=\"%d\" v3=\"%d\"/>\n" % tuple(t)
               for t in np.asarray(mesh.faces))
    out.append("    </triangles>\n   </mesh>\n")
    return "".join(out), (hi - lo)


def build(src_dir, out_dir, verbose=True):
    src_dir = Path(src_dir)
    out_dir = Path(out_dir)
    out_path = out_dir / "Blind Map - 8 plates.3mf"
    cards = []
    for fname, name in CARDS:
        p = src_dir / fname
        if not p.exists():
            raise SystemExit(f"missing {p} — run core/build_all.py first")
        m = trimesh.load(str(p), process=True, force='mesh')
        trimesh.repair.fix_normals(m)
        cards.append((m, name, fname))

    cols = compute_colum_count(len(cards))
    if verbose:
        print(f"{len(cards)} plates, {cols} columns, stride "
              f"{BED_W * (1 + PLATE_GAP):.1f} mm")

    objects, items, settings = [], [], []
    for i, (m, name, fname) in enumerate(cards):
        oid = i + 1
        body, size = mesh_xml(m)
        objects.append(f'  <object id="{oid}" type="model">\n{body}  </object>\n')

        ox, oy = plate_origin(i, cols)
        tx, ty = ox + BED_W / 2, oy + BED_D / 2
        items.append(f'  <item objectid="{oid}" transform="1 0 0 0 1 0 0 0 1 '
                     f'{tx:.4f} {ty:.4f} 0" printable="1"/>\n')

        settings.append(
            f'  <object id="{oid}">\n'
            f'    <metadata key="name" value="{escape(name, {chr(34): "&quot;"})}"/>\n'
            f'    <metadata key="extruder" value="1"/>\n'
            f'  </object>\n')
        if verbose:
            print(f"  plate {oid}: {name}  ({size[0]:.1f}x{size[1]:.1f}x{size[2]:.1f} mm) "
                  f"@ ({tx:.0f}, {ty:.0f})  {len(m.faces)} tris")

    plates = []
    for i, (_m, name, _f) in enumerate(cards):
        plates.append(
            f'  <plate>\n'
            f'    <metadata key="plater_id" value="{i + 1}"/>\n'
            f'    <metadata key="plater_name" value="{escape(name, {chr(34): "&quot;"})}"/>\n'
            f'    <metadata key="locked" value="false"/>\n'
            f'    <model_instance>\n'
            f'      <metadata key="object_id" value="{i + 1}"/>\n'
            f'      <metadata key="instance_id" value="0"/>\n'
            f'    </model_instance>\n'
            f'  </plate>\n')

    model = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US"'
        ' xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"'
        ' xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">\n'
        ' <metadata name="Application">worldbytouch export_3mf.py</metadata>\n'
        ' <metadata name="Title">Tactile Braille Map for the Blind:'
        ' Europe &amp; Arabia</metadata>\n'
        ' <metadata name="Designer">Gleb Maksimov</metadata>\n'
        ' <metadata name="Description">3D-printed tactile map with braille labels,'
        ' terrain relief and snap-together puzzle cards</metadata>\n'
        ' <metadata name="License">MIT</metadata>\n'
        ' <resources>\n' + "".join(objects) + ' </resources>\n'
        ' <build>\n' + "".join(items) + ' </build>\n'
        '</model>\n')

    model_settings = ('<?xml version="1.0" encoding="UTF-8"?>\n<config>\n'
                      + "".join(settings) + "".join(plates) + '</config>\n')

    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr('[Content_Types].xml', CONTENT_TYPES)
        z.writestr('_rels/.rels', RELS)
        z.writestr('3D/3dmodel.model', model)
        z.writestr('Metadata/model_settings.config', model_settings)
    if verbose:
        print(f"-> {out_path.name}  ({out_path.stat().st_size / 1048576:.1f} MB)")

    # STLs under upload-friendly names, for people who don't use the project file
    for fname, name in CARDS:
        shutil.copyfile(src_dir / fname, out_dir / f"{name}.stl")
    if verbose:
        print(f"-> {len(CARDS)} STLs renamed for upload")
        print(f"bundle: {out_dir}/  (copy text: docs/MAKERWORLD.md)")
    return out_path


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "data/output/printready"
    out = sys.argv[2] if len(sys.argv) > 2 else "data/output/makerworld"
    build(src, out)
