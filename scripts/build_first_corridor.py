#!/usr/bin/env python3
"""Build a 1 km, 200 m-wide test corridor northbound from Mianwali Toll Plaza.

Uses the mapped geometry of OSM way 170335647 only. The source GeoJSON is not
modified. Outputs a corridor GeoJSON and an SVG preview under data/.

Run from the project root:
  python scripts/build_first_corridor.py
"""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "mianwali_roads.geojson"
OUT_GEOJSON = ROOT / "data" / "first_1km_corridor.geojson"
OUT_SVG = ROOT / "data" / "first_1km_corridor_preview.svg"

TOLL_LONLAT = (71.55638679942773, 32.51905049886542)
TARGET_WAY_ID = 170335647
LENGTH_M = 1000.0
HALF_WIDTH_M = 100.0

def project(lonlat, lon0, lat0):
    lon, lat = lonlat
    x = math.radians(lon - lon0) * 6371008.8 * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * 6371008.8
    return (x, y)

def unproject(xy, lon0, lat0):
    x, y = xy
    lon = lon0 + math.degrees(x / (6371008.8 * math.cos(math.radians(lat0))))
    lat = lat0 + math.degrees(y / 6371008.8)
    return [lon, lat]

def nearest_on_segment(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    denom = vx * vx + vy * vy
    if denom == 0:
        return a, 0.0
    t = max(0.0, min(1.0, ((p[0]-a[0])*vx + (p[1]-a[1])*vy) / denom))
    return (a[0] + t*vx, a[1] + t*vy), t

def line_length(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))

def cut_line_from_toll_toward_start(points, toll):
    best = None
    walked = 0.0
    for i, (a, b) in enumerate(zip(points, points[1:])):
        q, t = nearest_on_segment(toll, a, b)
        snap = math.dist(toll, q)
        if best is None or snap < best[0]:
            best = (snap, i, q, t, walked)
        walked += math.dist(a, b)

    snap, i, q, t, distance_from_start = best
    # Way 170335647 is oriented north-to-south. Travel from the snapped point
    # toward its START (north, toward Watta Khel).
    remaining = distance_from_start + t * math.dist(points[i], points[i+1])
    if remaining < LENGTH_M:
        raise SystemExit(
            f"Only {remaining:.1f} m of this mapped way lies north of the toll snap. "
            "Do not extend across unverified joins; inspect/verify the next segment first."
        )

    # Walk backwards along the OSM way from the snapped point, exactly 1 km.
    result = [q]
    need = LENGTH_M
    current = q
    for j in range(i, -1, -1):
        start = points[j]
        segment = math.dist(current, start)
        if segment >= need:
            ratio = need / segment if segment else 0
            endpoint = (current[0] + (start[0]-current[0])*ratio,
                        current[1] + (start[1]-current[1])*ratio)
            result.append(endpoint)
            need = 0
            break
        result.append(start)
        need -= segment
        current = start
    if need > 0.01:
        raise SystemExit("Could not construct the requested 1 km route segment.")
    result.reverse()
    return result, q, snap

def offset_side(points, half_width, side):
    # Simple miter joins. Suitable for this short preview corridor; sharp
    # corners are limited to avoid extreme spikes.
    out = []
    for i, p in enumerate(points):
        if i == 0:
            a, b = points[0], points[1]
            dx, dy = b[0]-a[0], b[1]-a[1]
            length = math.hypot(dx, dy)
            nx, ny = -dy/length, dx/length
        elif i == len(points)-1:
            a, b = points[-2], points[-1]
            dx, dy = b[0]-a[0], b[1]-a[1]
            length = math.hypot(dx, dy)
            nx, ny = -dy/length, dx/length
        else:
            a, p0, b = points[i-1], p, points[i+1]
            d1 = (p0[0]-a[0], p0[1]-a[1])
            d2 = (b[0]-p0[0], b[1]-p0[1])
            l1, l2 = math.hypot(*d1), math.hypot(*d2)
            n1 = (-d1[1]/l1, d1[0]/l1)
            n2 = (-d2[1]/l2, d2[0]/l2)
            nx, ny = n1[0]+n2[0], n1[1]+n2[1]
            nl = math.hypot(nx, ny)
            if nl < 1e-8:
                nx, ny = n2
                nl = 1.0
            nx, ny = nx/nl, ny/nl
            denom = max(0.25, abs(nx*n2[0] + ny*n2[1]))
            scale = min(half_width / denom, half_width * 3)
            out.append((p[0] + side*nx*scale, p[1] + side*ny*scale))
            continue
        out.append((p[0] + side*nx*half_width, p[1] + side*ny*half_width))
    return out

def main():
    if not SOURCE.exists():
        raise SystemExit(f"Missing {SOURCE}; run extract_roads.py first.")
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    feature = next((f for f in data["features"]
                    if f.get("properties", {}).get("osm_way_id") == TARGET_WAY_ID), None)
    if feature is None:
        raise SystemExit(f"OSM way {TARGET_WAY_ID} not found in {SOURCE}.")

    lon0, lat0 = TOLL_LONLAT
    coords = [project(c, lon0, lat0) for c in feature["geometry"]["coordinates"]]
    toll_xy = (0.0, 0.0)
    centerline, snapped, snap_distance = cut_line_from_toll_toward_start(coords, toll_xy)

    left = offset_side(centerline, HALF_WIDTH_M, 1)
    right = offset_side(centerline, HALF_WIDTH_M, -1)
    polygon_xy = left + list(reversed(right)) + [left[0]]

    center_wgs = [unproject(p, lon0, lat0) for p in centerline]
    polygon_wgs = [unproject(p, lon0, lat0) for p in polygon_xy]
    snap_wgs = unproject(snapped, lon0, lat0)

    collection = {
        "type": "FeatureCollection",
        "name": "Mianwali first 1 km test corridor",
        "source": "© OpenStreetMap contributors",
        "properties": {
            "source_osm_way_id": TARGET_WAY_ID,
            "length_m": LENGTH_M,
            "width_m": HALF_WIDTH_M * 2,
            "start_reference": "Mianwali Toll Plaza",
            "direction": "toward Watta Khel Chowk",
            "toll_to_mapped_road_snap_distance_m": round(snap_distance, 2),
            "warning": "Candidate corridor only; verify road alignment and snap distance before 3D use."
        },
        "features": [
            {"type": "Feature", "properties": {"kind": "test_corridor", "width_m": 200},
             "geometry": {"type": "Polygon", "coordinates": [polygon_wgs]}},
            {"type": "Feature", "properties": {"kind": "candidate_centerline", "osm_way_id": TARGET_WAY_ID},
             "geometry": {"type": "LineString", "coordinates": center_wgs}},
            {"type": "Feature", "properties": {"kind": "original_toll_plaza_coordinate"},
             "geometry": {"type": "Point", "coordinates": list(TOLL_LONLAT)}},
            {"type": "Feature", "properties": {"kind": "snapped_start_on_candidate_road"},
             "geometry": {"type": "Point", "coordinates": snap_wgs}},
        ]
    }
    OUT_GEOJSON.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")

    # Draw an SVG preview in local metric coordinates.
    all_xy = polygon_xy + centerline + [toll_xy, snapped]
    minx, maxx = min(p[0] for p in all_xy), max(p[0] for p in all_xy)
    miny, maxy = min(p[1] for p in all_xy), max(p[1] for p in all_xy)
    W, H, pad = 1100, 650, 70
    sx = (W-2*pad) / max(maxx-minx, 1)
    sy = (H-2*pad) / max(maxy-miny, 1)
    scale = min(sx, sy)
    def xy(p):
        return (pad+(p[0]-minx)*scale, H-pad-(p[1]-miny)*scale)
    def pts(seq):
        return " ".join(f"{xy(p)[0]:.1f},{xy(p)[1]:.1f}" for p in seq)
    tx, ty = xy(toll_xy)
    px, py = xy(snapped)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        '<rect width="100%" height="100%" fill="#fbfaf6"/>',
        '<text x="35" y="35" font-family="Arial" font-size="22" font-weight="bold" fill="#202820">Mianwali — first 1 km test corridor</text>',
        '<text x="35" y="58" font-family="Arial" font-size="13" fill="#59645b">Candidate OSM way 170335647 | 200 m total width | northbound toward Watta Khel</text>',
        f'<polygon points="{pts(polygon_xy)}" fill="#e8c46c" fill-opacity="0.35" stroke="#bd861f" stroke-width="2"/>',
        f'<polyline points="{pts(centerline)}" fill="none" stroke="#9a5c08" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>',
        f'<circle cx="{tx:.1f}" cy="{ty:.1f}" r="7" fill="#c43d35" stroke="white" stroke-width="2"/>',
        f'<text x="{tx+12:.1f}" y="{ty+4:.1f}" font-family="Arial" font-size="14" fill="#c43d35">Toll Plaza coordinate</text>',
        f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="#236b9b" stroke="white" stroke-width="2"/>',
        f'<text x="{px+12:.1f}" y="{py-10:.1f}" font-family="Arial" font-size="13" fill="#236b9b">Road snap point</text>',
        f'<text x="35" y="{H-25}" font-family="Arial" font-size="12" fill="#59645b">Snap offset: {snap_distance:.1f} m | Candidate only — verify before 3D use | © OpenStreetMap contributors</text>',
        '</svg>'
    ]
    OUT_SVG.write_text("\n".join(svg), encoding="utf-8")

    print("FIRST CORRIDOR GENERATED")
    print(f"OSM way: {TARGET_WAY_ID}")
    print(f"Length along mapped road: {LENGTH_M:.0f} m")
    print(f"Total width: {HALF_WIDTH_M*2:.0f} m (100 m each side)")
    print(f"Toll Plaza coordinate to mapped-road snap: {snap_distance:.1f} m")
    print(f"GeoJSON: {OUT_GEOJSON}")
    print(f"SVG preview: {OUT_SVG}")
    print("IMPORTANT: This is a candidate test corridor, not yet an approved final alignment.")

if __name__ == "__main__":
    main()
