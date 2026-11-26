#!/usr/bin/env python3
"""Build a city-only general-road dataset and SVG preview from the Pakistan OSM PBF.

Run from project root:
  python scripts/build_mianwali_city_map.py

The city crop is a practical working rectangle, NOT an official boundary.
Road widths are not encoded in OSM consistently; Blender widths are estimates.
"""
import json
import math
from pathlib import Path
import osmium

ROOT = Path(__file__).resolve().parents[1]
PBF = ROOT / "data" / "pakistan-261125.osm.pbf"
OUT = ROOT / "data" / "mianwali_city_general_roads.geojson"
SVG = ROOT / "exports" / "Mianwali_City_Roads_Preview.svg"

# Mianwali urban working crop, WGS84. Review the preview for edge clipping.
MIN_LAT, MAX_LAT = 32.565, 32.605
MIN_LON, MAX_LON = 71.515, 71.565

# General through/connecting roads only; omit residential/service/living streets.
ROAD_TYPES = {
    "trunk", "primary", "secondary", "tertiary", "unclassified",
    "trunk_link", "primary_link", "secondary_link", "tertiary_link", "road",
}

def clip_segment(a, b):
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

def clip_line(coords):
    result, current = [], []
    for a, b in zip(coords, coords[1:]):
        seg = clip_segment(a, b)
        if seg is None:
            if len(current) > 1:
                result.append(current)
            current = []
            continue
        ca, cb = seg
        if current and math.dist(current[-1], ca) < 1e-9:
            current.append(cb)
        else:
            if len(current) > 1:
                result.append(current)
            current = [ca, cb]
    if len(current) > 1:
        result.append(current)
    return result

class Extractor(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.features = []
        self.ways = 0
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
        parts = clip_line(coords)
        if not parts:
            return
        props = {"osm_way_id": int(way.id), "highway": highway}
        for key in ("name", "ref", "lanes", "surface", "oneway", "bridge", "tunnel", "layer"):
            value = way.tags.get(key)
            if value is not None:
                props[key] = value
        for n, part in enumerate(parts, 1):
            self.features.append({
                "type": "Feature",
                "properties": {**props, "part": n},
                "geometry": {"type": "LineString", "coordinates": part},
            })
        self.ways += 1

def make_svg(features):
    width, height, margin = 1500, 1200, 65
    lat0 = (MIN_LAT + MAX_LAT) / 2
    # Local metric projection preserves the city's approximate aspect ratio.
    def xy(p):
        x = math.radians(p[0] - (MIN_LON + MAX_LON)/2) * 6371008.8 * math.cos(math.radians(lat0))
        y = math.radians(p[1] - lat0) * 6371008.8
        return x, y
    bounds = [xy([MIN_LON, MIN_LAT]), xy([MAX_LON, MAX_LAT])]
    minx, miny = bounds[0]
    maxx, maxy = bounds[1]
    scale = min((width-2*margin)/(maxx-minx), (height-2*margin)/(maxy-miny))
    ox = (width-(maxx-minx)*scale)/2
    oy = (height-(maxy-miny)*scale)/2
    def screen(p):
        x,y=xy(p)
        return ox+(x-minx)*scale, height-(oy+(y-miny)*scale)
    colors = {"trunk":"#b34b32","primary":"#d18b19","secondary":"#d9aa38","tertiary":"#687d83","unclassified":"#9aa5a3","road":"#9aa5a3",
              "trunk_link":"#b34b32","primary_link":"#d18b19","secondary_link":"#d9aa38","tertiary_link":"#687d83"}
    widths = {"trunk":6,"primary":5,"secondary":4,"tertiary":3,"unclassified":2.5,"road":2.5}
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f7f6f1"/>',
        '<text x="38" y="40" font-family="Arial" font-size="26" font-weight="bold" fill="#202820">Mianwali city — general road network</text>',
        '<text x="38" y="67" font-family="Arial" font-size="14" fill="#59645b">Main and connecting roads only | residential streets/services excluded | © OpenStreetMap contributors</text>',
    ]
    for f in features:
        coords=f["geometry"]["coordinates"]
        pts=" ".join(f"{screen(p)[0]:.1f},{screen(p)[1]:.1f}" for p in coords)
        kind=f["properties"]["highway"]
        color=colors.get(kind,"#9aa5a3")
        sw=widths.get(kind.replace("_link",""),2.5)
        lines.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round"/>')
    legend=[("trunk","#b34b32"),("primary","#d18b19"),("secondary","#d9aa38"),("tertiary","#687d83"),("unclassified","#9aa5a3")]
    x=40
    for label,color in legend:
        lines.append(f'<line x1="{x}" y1="{height-35}" x2="{x+32}" y2="{height-35}" stroke="{color}" stroke-width="6"/>')
        lines.append(f'<text x="{x+40}" y="{height-29}" font-family="Arial" font-size="14" fill="#303830">{label}</text>')
        x += 180
    lines += [
        '<text x="38" y="98" font-family="Arial" font-size="13" fill="#8a4b20">Working crop is approximate, not an official city boundary. Check edge coverage before final use.</text>',
        '</svg>'
    ]
    SVG.parent.mkdir(parents=True, exist_ok=True)
    SVG.write_text("\n".join(lines), encoding="utf-8")

def main():
    if not PBF.is_file():
        raise SystemExit(f"Pakistan OSM PBF missing: {PBF}")
    print("Reading Pakistan OSM extract (offline)...")
    handler=Extractor()
    handler.apply_file(str(PBF), locations=True)
    data={
        "type":"FeatureCollection",
        "name":"Mianwali city general roads",
        "source":"© OpenStreetMap contributors",
        "extent_note":"Approximate working crop only; not an official municipal boundary.",
        "bbox_wgs84":[MIN_LON,MIN_LAT,MAX_LON,MAX_LAT],
        "road_classes":sorted(ROAD_TYPES),
        "features":handler.features,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data,ensure_ascii=False),encoding="utf-8")
    make_svg(handler.features)
    counts={}
    for f in handler.features:
        k=f["properties"]["highway"]
        counts[k]=counts.get(k,0)+1
    print("MIANWALI CITY ROADS EXTRACTED")
    print(f"OSM ways: {handler.ways}")
    print(f"Clipped line parts: {len(handler.features)}")
    print("Classes: "+", ".join(f"{k}={v}" for k,v in sorted(counts.items())))
    print(f"GeoJSON: {OUT}")
    print(f"Preview: {SVG}")
    print("Note: OSM coverage and road classification may be incomplete; widths are approximate.")

if __name__=="__main__":
    main()
