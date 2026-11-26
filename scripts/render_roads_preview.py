"""Render a lightweight SVG preview from the extracted roads-only GeoJSON."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "mianwali_roads_only.geojson"
OUTPUT = ROOT / "exports" / "mianwali_roads_only_preview.svg"

STROKES = {
    "motorway": 3.8, "motorway_link": 2.4,
    "trunk": 3.4, "trunk_link": 2.2,
    "primary": 3.0, "primary_link": 2.0,
    "secondary": 2.4, "secondary_link": 1.8,
    "tertiary": 1.7, "tertiary_link": 1.4,
    "unclassified": 1.2
}


def main():
    if not SOURCE.exists():
        raise SystemExit("GeoJSON missing. Run scripts/extract_roads.py first.")
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    lines = [f["geometry"]["coordinates"] for f in data["features"] if f.get("geometry", {}).get("type") == "LineString"]
    points = [p for line in lines for p in line]
    if not points:
        raise SystemExit("No road lines found in GeoJSON.")

    min_lon = min(p[0] for p in points)
    max_lon = max(p[0] for p in points)
    min_lat = min(p[1] for p in points)
    max_lat = max(p[1] for p in points)
    width, height, margin = 1800, 1200, 30
    lon_scale = (width - 2 * margin) / max(max_lon - min_lon, 1e-9)
    lat_scale = (height - 2 * margin) / max(max_lat - min_lat, 1e-9)
    scale = min(lon_scale, lat_scale)

    def project(point):
        x = margin + (point[0] - min_lon) * scale
        y = height - margin - (point[1] - min_lat) * scale
        return x, y

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<g fill="none" stroke="#30343b" stroke-linecap="round" stroke-linejoin="round">'
    ]
    for feature in data["features"]:
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            continue
        path = " ".join(
            ("M" if i == 0 else "L") + f" {project(p)[0]:.2f},{project(p)[1]:.2f}"
            for i, p in enumerate(coords)
        )
        stroke = STROKES.get(props.get("highway"), 1.2)
        parts.append(f'<path d="{path}" stroke-width="{stroke}"/>')
    parts.extend(["</g>", "</svg>"])
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"Saved preview: {OUTPUT}")


if __name__ == "__main__":
    main()
