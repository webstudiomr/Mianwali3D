#!/usr/bin/env python3
"""Create an offline SVG preview of the Mianwali road network and M.M. Road candidates.

Run from the project root:
  python scripts/make_route_preview.py
"""
import json
from pathlib import Path
from html import escape

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "mianwali_roads.geojson"
OUTPUT = ROOT / "data" / "mianwali_route_preview.svg"

TOLL = (71.55638679942773, 32.51905049886542)  # longitude, latitude
WATTA_KHEL = (71.54745917152697, 32.57907342118)
CANDIDATE_WAYS = {170335647, 1223551053, 1223551051, 170335640, 1223553790}

WIDTH, HEIGHT = 1400, 1050
MARGIN = 85

def main():
    if not INPUT.exists():
        raise SystemExit(f"GeoJSON not found: {INPUT}. Run extract_roads.py first.")

    data = json.loads(INPUT.read_text(encoding="utf-8"))
    features = data.get("features", [])
    all_points = [
        point
        for feature in features
        for point in feature.get("geometry", {}).get("coordinates", [])
    ]
    all_points.extend([TOLL, WATTA_KHEL])
    if not all_points:
        raise SystemExit("No road coordinates found.")

    min_lon = min(p[0] for p in all_points)
    max_lon = max(p[0] for p in all_points)
    min_lat = min(p[1] for p in all_points)
    max_lat = max(p[1] for p in all_points)
    lon_span = max(max_lon - min_lon, 0.0001)
    lat_span = max(max_lat - min_lat, 0.0001)

    # Fit the geographic extent while preserving approximate map proportions.
    usable_w, usable_h = WIDTH - 2 * MARGIN, HEIGHT - 2 * MARGIN
    scale = min(usable_w / lon_span, usable_h / lat_span)
    draw_w, draw_h = lon_span * scale, lat_span * scale
    offset_x = (WIDTH - draw_w) / 2
    offset_y = (HEIGHT - draw_h) / 2

    def xy(point):
        lon, lat = point
        x = offset_x + (lon - min_lon) * scale
        y = HEIGHT - offset_y - (lat - min_lat) * scale
        return x, y

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="#fbfaf6"/>',
        '<text x="42" y="42" font-family="Arial,sans-serif" font-size="25" font-weight="bold" fill="#202820">Mianwali road network — offline preview</text>',
        '<text x="42" y="68" font-family="Arial,sans-serif" font-size="14" fill="#59645b">Grey: other mapped roads | Gold: candidate M.M. Road OSM ways | Not yet an approved final route</text>',
    ]

    # Draw background roads first.
    for feature in features:
        coords = feature.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            continue
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in map(xy, coords))
        parts.append(f'<polyline points="{points}" fill="none" stroke="#c7cbc5" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>')

    # Overlay candidate M.M. Road ways. Retain each OSM way separately for review.
    highlighted = []
    for feature in features:
        props = feature.get("properties", {})
        way_id = props.get("osm_way_id")
        if way_id not in CANDIDATE_WAYS:
            continue
        coords = feature.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            continue
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in map(xy, coords))
        parts.append(f'<polyline points="{points}" fill="none" stroke="#d18b19" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>')
        highlighted.append((way_id, props.get("name", "M.M. Road candidate")))

    # Endpoint markers.
    for point, label, color in [
        (TOLL, "Mianwali Toll Plaza", "#c43d35"),
        (WATTA_KHEL, "Watta Khel Chowk", "#236b9b"),
    ]:
        x, y = xy(point)
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="{color}" stroke="white" stroke-width="3"/>')
        parts.append(f'<text x="{x + 14:.1f}" y="{y - 13:.1f}" font-family="Arial,sans-serif" font-size="17" font-weight="bold" fill="{color}" stroke="#fbfaf6" stroke-width="4" paint-order="stroke">{escape(label)}</text>')

    # Compact legend and way IDs.
    legend_y = HEIGHT - 48
    parts.append(f'<rect x="35" y="{HEIGHT - 145}" width="510" height="112" rx="10" fill="white" stroke="#d9ddd6"/>')
    parts.append(f'<text x="55" y="{HEIGHT - 116}" font-family="Arial,sans-serif" font-size="15" font-weight="bold" fill="#202820">Highlighted OSM way IDs</text>')
    ids_text = ", ".join(str(item[0]) for item in highlighted) or "No candidate ways found"
    parts.append(f'<text x="55" y="{HEIGHT - 88}" font-family="Arial,sans-serif" font-size="14" fill="#39443b">{escape(ids_text)}</text>')
    parts.append(f'<text x="55" y="{HEIGHT - 62}" font-family="Arial,sans-serif" font-size="12" fill="#69736a">OSM data © OpenStreetMap contributors | Verify alignment before corridor generation</text>')
    parts.append("</svg>")

    OUTPUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Road features displayed: {len(features)}")
    print(f"Candidate ways highlighted: {len(highlighted)}")
    print(f"Highlighted way IDs: {', '.join(str(x[0]) for x in highlighted)}")
    print(f"SVG preview saved: {OUTPUT}")

if __name__ == "__main__":
    main()
