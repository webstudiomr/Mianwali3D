#!/usr/bin/env python3
"""Inspect continuity of candidate M.M. Road OSM ways without changing source data.

Run from project root:
  python scripts/check_route_connections.py
"""
import json
from math import radians, sin, cos, asin, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "mianwali_roads.geojson"
REPORT = ROOT / "data" / "route_connection_report.txt"

# Candidate ways identified from the endpoint and name checks.
CANDIDATE_IDS = {170335647, 1223551053, 1223551051, 170335640, 1223553790}
ENDPOINT_TOLERANCE_M = 35

def haversine(a, b):
    lon1, lat1 = a
    lon2, lat2 = b
    lat1, lat2 = radians(lat1), radians(lat2)
    dlat, dlon = lat2 - lat1, radians(lon2 - lon1)
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 6371000 * 2 * asin(sqrt(h))

def main():
    if not SOURCE.exists():
        raise SystemExit(f"Missing {SOURCE}. Run extract_roads.py first.")

    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    features = data.get("features", [])
    candidates = []
    for feature in features:
        props = feature.get("properties", {})
        if props.get("osm_way_id") not in CANDIDATE_IDS:
            continue
        coords = feature.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            continue
        candidates.append({
            "id": props["osm_way_id"],
            "name": props.get("name", "unnamed"),
            "coords": coords,
        })

    lines = [
        "M.M. ROAD CANDIDATE CONNECTION CHECK",
        "Distances are approximate straight-line endpoint distances.",
        "This is a diagnostic, not proof of the legally/physically correct carriageway.",
        "",
    ]

    for way in candidates:
        lines.append(f"WAY {way['id']} | {way['name']} | {len(way['coords'])} points")
        for label, point in (("START", way["coords"][0]), ("END", way["coords"][-1])):
            matches = []
            for other in candidates:
                if other["id"] == way["id"]:
                    continue
                for other_label, other_point in (("START", other["coords"][0]), ("END", other["coords"][-1])):
                    matches.append((haversine(point, other_point), other["id"], other_label))
            matches.sort()
            if matches:
                d, other_id, other_end = matches[0]
                status = "POSSIBLE JOIN" if d <= ENDPOINT_TOLERANCE_M else "GAP / NEEDS REVIEW"
                lines.append(f"  {label} nearest candidate endpoint: {d:.1f} m -> way {other_id} {other_end} [{status}]")
        lines.append("")

    lines.append("ALL CANDIDATE ENDPOINT PAIRS WITHIN 100 m")
    endpoints = [(w["id"], label, p) for w in candidates for label, p in (("START", w["coords"][0]), ("END", w["coords"][-1]))]
    pairs = []
    for i, (id1, end1, p1) in enumerate(endpoints):
        for id2, end2, p2 in endpoints[i + 1:]:
            if id1 == id2:
                continue
            d = haversine(p1, p2)
            if d <= 100:
                pairs.append((d, id1, end1, id2, end2))
    for d, id1, end1, id2, end2 in sorted(pairs):
        lines.append(f"  {d:.1f} m: way {id1} {end1} <-> way {id2} {end2}")
    if not pairs:
        lines.append("  No endpoint pairs found within 100 m.")

    lines.extend([
        "",
        "NOTE: Ways 170335640 and 1223553790 may be parallel/overlapping mapped lines.",
        "Do not merge them automatically. Inspect their geometry before choosing a centreline.",
    ])

    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nReport saved: {REPORT}")

if __name__ == "__main__":
    main()
