# Roads-only map assets

This folder is reserved for generated road-map exports. Generated GeoJSON, SVG and Blender files are not committed until they have been built from the local OSM PBF and checked.

## Build
1. Put the Pakistan OSM extract at `data/pakistan-261125.osm.pbf`.
2. Install the Python dependency: `python -m pip install osmium`.
3. From the repository root run: `python scripts/extract_roads.py`.
4. Render the 2D preview: `python scripts/render_roads_preview.py`.
5. Open Blender, switch to **Scripting**, open `scripts/import_roads_to_blender.py`, and run it.

The extraction settings are in `config/road_map_config.json`. Small residential streets, service roads, paths and footways are excluded. The current bounds are an initial regional window and must be checked against the preview/data before treating every extracted road as final.

Source: © OpenStreetMap contributors, licensed under the Open Database License (ODbL): https://www.openstreetmap.org/copyright
