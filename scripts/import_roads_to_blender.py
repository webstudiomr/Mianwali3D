"""Import data/mianwali_roads_only.geojson into Blender as road curves.

Run inside Blender's Scripting workspace. The script uses Blender's bundled Python
and needs no third-party packages. Roads are centered around the extracted area.
"""
import bpy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEOJSON = ROOT / "data" / "mianwali_roads_only.geojson"
COLLECTION_NAME = "Mianwali Roads Only"

WIDTHS = {
    "motorway": 12.0, "motorway_link": 7.0,
    "trunk": 10.0, "trunk_link": 6.0,
    "primary": 8.0, "primary_link": 5.5,
    "secondary": 6.5, "secondary_link": 5.0,
    "tertiary": 4.5, "tertiary_link": 4.0,
    "unclassified": 3.5
}


def main():
    if not GEOJSON.exists():
        raise RuntimeError("GeoJSON missing. Run scripts/extract_roads.py first.")

    data = json.loads(GEOJSON.read_text(encoding="utf-8"))
    coords_all = [
        c for f in data["features"]
        for c in f["geometry"]["coordinates"]
    ]
    if not coords_all:
        raise RuntimeError("GeoJSON contains no road coordinates.")

    lon0 = sum(c[0] for c in coords_all) / len(coords_all)
    lat0 = sum(c[1] for c in coords_all) / len(coords_all)
    cos_lat = math.cos(math.radians(lat0))

    old = bpy.data.collections.get(COLLECTION_NAME)
    if old:
        for obj in list(old.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)
    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)

    for feature in data["features"]:
        props = feature.get("properties", {})
        kind = props.get("highway", "unclassified")
        coords = feature["geometry"]["coordinates"]
        if len(coords) < 2:
            continue

        curve = bpy.data.curves.new(
            f'OSM way {props.get("osm_id", "unknown")} - {kind}', "CURVE"
        )
        curve.dimensions = "3D"
        curve.resolution_u = 1
        curve.bevel_depth = WIDTHS.get(kind, 3.5) / 2
        curve.bevel_resolution = 2
        spline = curve.splines.new("POLY")
        spline.points.add(len(coords) - 1)

        for point, (lon, lat) in zip(spline.points, coords):
            x = (lon - lon0) * 111320.0 * cos_lat
            y = (lat - lat0) * 110540.0
            point.co = (x, y, 0.15, 1.0)

        obj = bpy.data.objects.new(curve.name, curve)
        collection.objects.link(obj)
        obj["osm_id"] = props.get("osm_id")
        obj["highway"] = kind
        if props.get("name"):
            obj["road_name"] = props["name"]

    print(f"Imported {len(collection.objects)} road curves into '{COLLECTION_NAME}'.")


main()
