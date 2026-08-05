# Blind Map — Tactile Map for the Visually Impaired

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![3D Printing](https://img.shields.io/badge/3D%20Printing-PLA-orange.svg)
![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)

A 3D-printable tactile map that helps blind people learn geography by touch.

If you are interested in a custom tactile map, an educational 3D model,
collaboration, or supporting future work on accessible 3D-printed materials,
[get in touch](#custom-maps-collaboration-support).

![The printed tactile map with the braille legend and alphabet cards](assets/photo_map.jpg)

## What is this?

This project generates STL files for 3D printing a tactile map. The map is
designed so a blind person can:

| What | How it feels |
|------|--------------|
| Country borders | Raised ridge (1.2 mm) that follows the terrain under the finger |
| Terrain | 4 tactile plateaus: sea / lowland / plateau / mountains (0/1/2/3 mm) |
| Sea | Wavy texture |
| Country numbers | Braille number labels (Marburg Medium: ⌀1.6 mm dome dots, 2.5 mm dot pitch) with an anchor ridge that marks the cell frame |
| Legend | Braille country list + texture samples (sea, border, number key) |
| Alphabet cards | Raised Latin letter next to its braille cell, for learning braille |

The map splits into 4 puzzle pieces (200×160 mm each) that lock together with
dovetail tabs: lay one card flat, lower its neighbour onto the tab from above —
assembled, the map cannot slide apart. Legends and alphabet cards come in two languages: English and
Serbian (Gajica braille, 30 letters including Č Ć Dž Đ Lj Nj Š Ž).

![The printed puzzle cards, braille legend and alphabet cards](assets/photo_cards.jpg)

## What You Get

9 print-ready STL files in `data/output/printready/`:

| File | Contents |
|------|----------|
| `tactile_map.stl` | The full 400×320 mm map in one piece |
| `card_1.stl` … `card_4.stl` | The same map split into 4 puzzle cards |
| `card_legend.stl` | Braille numbers → country names in English braille |
| `card_legend_sr.stl` | Braille numbers → country names in Serbian braille |
| `card_alphabet.stl` | English braille alphabet learning card (26 letters) |
| `card_alphabet_sr.stl` | Serbian braille alphabet learning card (30 letters) |

![All nine deliverables](assets/deliverables.png)

Every output is a single watertight two-manifold, verified by
`mesh_diagnostics.py` — no inverted normals, internal cavities, or
self-intersections.

## Region Covered

Europe, Middle East, North Africa, Caucasus: 5°–70° E, 12°–55° N.
27 countries get a braille number label, placed at the country's pole of
inaccessibility. Countries too small to hold a standard braille cell at a
readable clearance are left unlabelled — a braille cell is far larger than an
embossed digit, so fewer countries can carry one.

![Serbian braille legend](assets/legend.png)
![Serbian braille alphabet card](assets/alphabet.png)

## How to Build

### 0. Install dependencies

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 1. Get the data

```bash
# Country borders (automatic, ~80 countries from geoBoundaries)
python core/prepare_data/download_geojson.py
python core/prepare_data/merge_geojson.py

# Elevation data (manual)
# Go to: https://www.ngdc.noaa.gov/mgg/global/
# Download ETOPO1_Bed_g_gmt4.grd
# Place in: data/input/
```

| Data | What for | Source |
|------|----------|--------|
| Country borders | Ridges between countries | [geoBoundaries](https://www.geoboundaries.org/) |
| Elevation | Terrain (mountains, plains) | [NOAA ETOPO1](https://www.ngdc.noaa.gov/mgg/global/) |

### 2. Generate STL files

```bash
python core/build_all.py
```

Output: `data/output/printready/` — the 9 STL files listed above.

### 3. Verify (optional)

```bash
python core/mesh_diagnostics.py
```

Prints a print-readiness report (watertight, normals, cavities,
self-intersections) for every STL.

### 4. Print

| Setting | Value | Note |
|---------|-------|------|
| Material | PLA | Common, cheap, safe |
| Infill | 15–20% | How solid inside (lower = faster) |
| Layer height | 0.2 mm | Each terrain plateau is exactly 5 layers |

![Print tiles, top view](assets/assembly.png)

## Project Structure

```
blind_map/
├── assets/                    # Images for this README
├── core/
│   ├── config.py              # Map region (bounding box)
│   ├── constants.py           # All tactile/physical parameters
│   ├── generate.py            # Mesh building blocks: terrain, water, borders,
│   │                          #   braille number labels, legend cards
│   ├── countries.py           # ISO3 -> country name table (EN/SR) for the labels
│   ├── build_all.py           # ENTRY POINT: full print-ready build
│   ├── walls_buffer.py        # Border ridges (buffer + manifold extrude)
│   ├── split_cards.py         # Boolean split into 4 puzzle cards
│   ├── heal_mesh.py           # Solid prep + boolean union helpers
│   ├── clean_mesh.py          # Topology cleanup -> watertight manifold
│   ├── text_mesh.py           # Raised Latin letters for alphabet cards
│   ├── alphabet_card.py       # Braille alphabet learning cards (EN/SR)
│   ├── serbian_braille.py     # Serbian Latin (Gajica) braille tables
│   ├── serbian_legend.py      # Serbian legend card
│   ├── mesh_diagnostics.py    # Print-readiness verification
│   ├── render_previews.py     # Preview renders of the print-ready STLs
│   ├── render_site_assets.py  # The renders published on worldbytouch.com
│   └── prepare_data/          # Data download & merge scripts
├── data/                      # Not in repo (too large)
│   ├── input/                 # ETOPO1 elevation grid
│   ├── countries/             # Downloaded border GeoJSONs
│   └── output/                # Generated files (printready/, previews/)
├── requirements.txt
└── README.md
```

## Tactile Design

![Assembled tactile map, 3D render](assets/map_3d.png)

| Parameter | Value |
|-----------|-------|
| Full map size | 400×320 mm |
| Single card | 200×160 mm |
| Base thickness | 6 mm |
| Terrain plateaus | 0 / 1 / 2 / 3 mm (sea, lowland, plateau, mountains) |
| Border ridge | +1.2 mm above local terrain, 1.5 mm wide |
| Water waves | 2 mm high, every 4 mm |
| Braille dots | Dome ⌀1.6 mm × 0.8 mm; 2.5 mm dot pitch, 6.0 mm cell pitch (Marburg Medium) |
| Label anchor ridge | 1.0 mm wide, full cell height, 1.4 mm clear of the dots |
| Puzzle connectors | Dovetail tabs 8→13 mm wide × 4 × 3 mm, 0.5 mm clearance, drop-in from above |

Key design decision: the border is a low ridge riding **on top of the local
terrain**, not a tall wall at a fixed height. A finger can trace a border
continuously and still read the relief on both sides of it; tall walls used to
bury small lowland countries entirely.

## Custom maps, collaboration, support

This project started as a birthday gift for my blind friend. I would be glad if
it turns out to be useful to other people too.

Get in touch if you want to:

- adapt this map for another region
- have a custom tactile map made
- create an educational tactile 3D model
- use this idea for a school, a museum, an accessibility project, or a gift

I am open to collaborations, custom orders, and paid work around tactile maps
and educational 3D models. For anything technical — printing problems, build
errors, ideas — [open an issue](../../issues).

If you would like to support future work on accessible 3D-printed materials,
[sponsorship](https://github.com/sponsors/MAGLeb) is welcome.

## License

MIT — see [LICENSE](LICENSE). The STL files it generates are yours to print,
adapt, and give away.
