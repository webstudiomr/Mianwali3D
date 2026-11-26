# Mianwali3D

A roads-only real-world map project focused on Mianwali, Pakistan, plus the regional road corridors requested for exploration.

## Map scope
- Harnoli Morr to Essa Khel Interchange (M-14)
- Watta Khel Chowk to Gulberg Chowk and the PAF Gate side
- Kundian Morr to Chashma
- Sargodha Morr to Sargodha
- Mianwali city main roads and their important connecting roads, including the west side of Jahaz Chowk

Small residential streets, narrow alleys, footpaths and service roads are excluded. Main and secondary roads, selected tertiary connectors, and major highway links are retained.

## Tools
- Blender 5.3
- OpenStreetMap data
- Osmium Tool / Python `osmium`
- VS Code

## Project structure
- `config/` - road extraction bounds and filtering rules
- `data/` - geographic source and generated GeoJSON (large source files excluded from Git)
- `scripts/` - OSM extraction, SVG preview and Blender import scripts
- `assets/roads/` - notes for generated road-map assets
- `blender/` - Blender project files
- `exports/` - exported previews

## Build
See [assets/roads/README.md](assets/roads/README.md). The Pakistan OSM PBF is required locally and is intentionally not stored in GitHub.

## Data attribution
© OpenStreetMap contributors. Data is available under the Open Database License (ODbL).
https://www.openstreetmap.org/copyright

The current extraction window is an initial regional rectangle. Review the generated preview and verify each corridor before treating the result as the final road alignment.
