#!/usr/bin/env python3
"""Extract a filtered roads-only GeoJSON from the local Pakistan OSM PBF.

Run from the repository root:
  python -m pip install osmium
  python scripts/extract_roads.py

Bounds and road-class filtering are controlled by config/road_map_config.json.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

try:
    import osmium
except ImportError as exc:
    raise SystemExit("Missing dependency. Install it with: python -m pip install osmium") from exc

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "road_map_config.json"


def haversine_m(a, b):
    lon1, lat1 = map(math.radians, a)
    lon2, lat2 = map(math.radians, b)
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371008.8 * 2 * math.asin(math.sqrt(h))


def line_length(coords):
    return sum(haversine_m(a, b) for a, b in zip(coords, coords[1:]))


class RoadHandler(osmium.SimpleHandler):
    def __init__(self, bounds, allowed, min_lengths):
        super().__init__()
        self.bounds = bounds
        self.allowed = set(allowed)
        self.min_lengths = min_lengths
        self.features = []
        self.seen = set()

    def in_bounds(self, lon, lat):
        return (self.bounds["west"] <= lon <= self.bounds["east"] and
                self.bounds["south"] <= lat <= self.bounds["north"])

    def way(self, way):
        highway = way.tags.get("highway")
        if highway not in self.allowed or way.id in self.seen:
            return
        coords = []
        try:
            for node in way.nodes:
                if not node.location.valid():
                    return
                coords.append([node.location.lon, node.location.lat])
        except (RuntimeError, ValueError):
            return
        if len(coords) < 2 or not any(self.in_bounds(lon, lat) for lon, lat in coords):
            return
        length = line_length(coords)
        if length < float(self.min_lengths.get(highway, 100)):
            return

        self.seen.add(way.id)
        tags = way.tags
        props = {
            "osm_id": int(way.id),
            "highway": highway,
            "name": tags.get("name"),
            "ref": tags.get("ref"),
            "oneway": tags.get("oneway"),
            "lanes": tags.get("lanes"),
            "surface": tags.get("surface"),
            "width": tags.get("width"),
            "bridge": tags.get("bridge"),
            "tunnel": tags.get("tunnel"),
            "length_m_approx": round(length, 1)
        }
        self.features.append({
            "type": "Feature",
            "id": f"way/{way.id}",
            "properties": props,
            "geometry": {"type": "LineString", "coordinates": coords}
        })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=None, help="Path to the Pakistan OSM PBF")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Road map JSON config")
    parser.add_argument("--output", default=None, help="Output GeoJSON path")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    source = Path(args.input or config["source_pbf"])
    if not source.is_absolute():
        source = ROOT / source
    output = Path(args.output or config["output_geojson"])
    if not output.is_absolute():
        output = ROOT / output
    if not source.exists():
        raise SystemExit(f"OSM PBF not found: {source}")

    handler = RoadHandler(
        config["bounds_wgs84"],
        config["included_highway_values"],
        config["minimum_way_length_m"]
    )
    print(f"Reading OSM roads from: {source}")
    handler.apply_file(str(source), locations=True)
    handler.features.sort(key=lambda f: (f["properties"]["highway"], f["properties"]["osm_id"]))

    output.parent.mkdir(parents=True, exist_ok=True)
    collection = {
        "type": "FeatureCollection",
        "name": "Mianwali3D roads only",
        "metadata": {
            "source": "OpenStreetMap contributors",
            "license": "ODbL",
            "bounds_wgs84": config["bounds_wgs84"],
            "feature_count": len(handler.features)
        },
        "features": handler.features
    }
    output.write_text(json.dumps(collection, ensure_ascii=False), encoding="utf-8")
    counts = {}
    for feature in handler.features:
        kind = feature["properties"]["highway"]
        counts[kind] = counts.get(kind, 0) + 1
    print(f"Saved {len(handler.features)} road ways to {output}")
    for kind, count in sorted(counts.items()):
        print(f"  {kind}: {count}")


if __name__ == "__main__":
    main()
