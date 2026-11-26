#!/usr/bin/env python3
"""Extract OSM road ways around the M.M. Road study area from a Pakistan PBF.

Usage:
  python extract_roads.py [input.pbf] [output.geojson]

The output is a local working dataset; do not commit the large source PBF.
"""
import json
import sys
from pathlib import Path

import osmium

# Study endpoints: Mianwali Toll Plaza and Watta Khel Chowk.
TOLL = (32.51905049886542, 71.55638679942773)  # latitude, longitude
WATTA_KHEL = (32.57907342118, 71.54745917152697)

# A small buffer around the endpoint bounding box, enough to capture the
# connecting road network for inspection before tracing the exact corridor.
BUFFER_DEGREES = 0.006
MIN_LAT = min(TOLL[0], WATTA_KHEL[0]) - BUFFER_DEGREES
MAX_LAT = max(TOLL[0], WATTA_KHEL[0]) + BUFFER_DEGREES
MIN_LON = min(TOLL[1], WATTA_KHEL[1]) - BUFFER_DEGREES
MAX_LON = max(TOLL[1], WATTA_KHEL[1]) + BUFFER_DEGREES

DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "data" / "pakistan-261125.osm.pbf"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "mianwali_roads.geojson"

ROAD_TYPES = {
    "motorway", "trunk", "primary", "secondary", "tertiary",
    "unclassified", "residential", "service", "living_street",
    "motorway_link", "trunk_link", "primary_link", "secondary_link",
    "tertiary_link", "road"
}


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
                lon = node.location.lon
                lat = node.location.lat
                coords.append([lon, lat])
        except (osmium.InvalidLocationError, RuntimeError):
            return

        if len(coords) < 2:
            return

        # Keep ways intersecting the buffered study-area bounding box.
        if not any(MIN_LON <= p[0] <= MAX_LON and MIN_LAT <= p[1] <= MAX_LAT for p in coords):
            return

        props = {
            "osm_way_id": way.id,
            "highway": highway,
        }
        for key in ("name", "ref", "surface", "lanes", "maxspeed", "bridge", "tunnel", "layer", "oneway"):
            value = way.tags.get(key)
            if value is not None:
                props[key] = value

        self.features.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "LineString", "coordinates": coords},
        })
        self.ways_seen += 1


def main():
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT
    output = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUTPUT

    if not source.is_file():
        raise SystemExit(f"Input PBF not found: {source}")

    print(f"Reading: {source}")
    print("Extracting mapped roads around Mianwali study area...")
    handler = RoadExtractor()
    handler.apply_file(str(source), locations=True)

    output.parent.mkdir(parents=True, exist_ok=True)
    collection = {
        "type": "FeatureCollection",
        "name": "Mianwali roads - OSM extract",
        "source": "© OpenStreetMap contributors",
        "bbox_wgs84": [MIN_LON, MIN_LAT, MAX_LON, MAX_LAT],
        "features": handler.features,
    }
    output.write_text(json.dumps(collection, ensure_ascii=False), encoding="utf-8")

    print(f"Road features exported: {handler.ways_seen}")
    print(f"Output: {output}")
    print("Note: this is the surrounding road network, not yet the final 100 m corridor.")


if __name__ == "__main__":
    main()
