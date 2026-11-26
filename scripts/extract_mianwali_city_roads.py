#!/usr/bin/env python3
"""Extract Mianwali city general roads from a Pakistan OSM PBF.

This is a provisional city-centre crop, not an official municipal boundary.
It keeps main/connecting road classes and excludes residential streets and services.
"""
import json
import sys
from pathlib import Path

import osmium

# Approximate Mianwali city-centre working extent (WGS84).
# Review the generated preview before treating this as the final city limit.
MIN_LAT, MAX_LAT = 32.565, 32.605
MIN_LON, MAX_LON = 71.515, 71.565

DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "data" / "pakistan-261125.osm.pbf"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "mianwali_city_general_roads.geojson"

ROAD_TYPES = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "motorway_link", "trunk_link", "primary_link", "secondary_link",
    "tertiary_link", "unclassified", "road"
}

def clip_segment(a, b):
    """Liang-Barsky clip of a lon/lat segment to the working rectangle."""
    x0, y0 = a
    x1, y1 = b
    dx, dy = x1 - x0, y1 - y0
    p = (-dx, dx, -dy, dy)
    q = (x0 - MIN_LON, MAX_LON - x0, y0 - MIN_LAT, MAX_LAT - y0)
    u0, u1 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return None
        else:
            t = qi / pi
            if pi < 0:
                u0 = max(u0, t)
            else:
                u1 = min(u1, t)
            if u0 > u1:
                return None
    return ([x0 + u0 * dx, y0 + u0 * dy],
            [x0 + u1 * dx, y0 + u1 * dy])

def clipped_parts(coords):
    parts, current = [], []
    for a, b in zip(coords, coords[1:]):
        clipped = clip_segment(a, b)
        if clipped is None:
            if len(current) >= 2:
                parts.append(current)
            current = []
            continue
        ca, cb = clipped
        if current and abs(current[-1][0] - ca[0]) < 1e-10 and abs(current[-1][1] - ca[1]) < 1e-10:
            current.append(cb)
        else:
            if len(current) >= 2:
                parts.append(current)
            current = [ca, cb]
    if len(current) >= 2:
        parts.append(current)
    return parts

class RoadExtractor(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.features = []
        self.ways_seen = 0

    def way(self, way):
        highway = way.tags.get("highway")
        if highway not in ROAD_TYPES:
            return
        coords = []
        try:
            for node in way.nodes:
                if not node.location.valid():
                    return
                coords.append([node.location.lon, node.location.lat])
        except (osmium.InvalidLocationError, RuntimeError):
            return
        if len(coords) < 2:
            return

        parts = clipped_parts(coords)
        if not parts:
            return

        props = {"osm_way_id": way.id, "highway": highway}
        for key in ("name", "ref", "surface", "lanes", "maxspeed", "bridge", "tunnel", "layer", "oneway"):
            value = way.tags.get(key)
            if value is not None:
                props[key] = value

        for index, part in enumerate(parts):
            self.features.append({
                "type": "Feature",
                "properties": {**props, "part": index + 1},
                "geometry": {"type": "LineString", "coordinates": part},
            })
        self.ways_seen += 1

def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT
    if not source.is_file():
        raise SystemExit(f"Input PBF not found: {source}")

    print(f"Reading: {source}")
    print("Extracting main and connecting roads inside the Mianwali city working crop...")
    handler = RoadExtractor()
    handler.apply_file(str(source), locations=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    collection = {
        "type": "FeatureCollection",
        "name": "Mianwali city general roads",
        "source": "© OpenStreetMap contributors",
        "extent_note": "Provisional city-centre crop; not an official municipal boundary.",
        "bbox_wgs84": [MIN_LON, MIN_LAT, MAX_LON, MAX_LAT],
        "features": handler.features,
    }
    output.write_text(json.dumps(collection, ensure_ascii=False), encoding="utf-8")
    print(f"OSM ways exported: {handler.ways_seen}")
    print(f"Line features exported: {len(handler.features)}")
    print(f"Output: {output}")
    print("Road classes: " + ", ".join(sorted(ROAD_TYPES)))
    print("Residential streets and service roads excluded.")
    print("Review the map preview; the crop is provisional, not a surveyed city boundary.")

if __name__ == "__main__":
    main()
