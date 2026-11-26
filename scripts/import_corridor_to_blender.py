#!/usr/bin/env python3
"""Import the first Mianwali test corridor GeoJSON into Blender.

Run this script from Blender's Scripting workspace (not system Python).
Input:  data/first_1km_corridor.geojson
Output: exports/Mianwali_First_1km.blend

The map is a flat, metre-scaled base. It does not invent terrain elevation,
building footprints, or a verified carriageway width.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "first_1km_corridor.geojson"
OUTPUT = ROOT / "exports" / "Mianwali_First_1km.blend"

# Same local tangent-plane projection used by the corridor builder.
ORIGIN_LON = 71.55638679942773
ORIGIN_LAT = 32.51905049886542
EARTH_R = 6371008.8
COLLECTION_NAME = "Mianwali_First_1km"


def project(lonlat):
    lon, lat = lonlat
    x = math.radians(lon - ORIGIN_LON) * EARTH_R * math.cos(math.radians(ORIGIN_LAT))
    y = math.radians(lat - ORIGIN_LAT) * EARTH_R
    return (x, y, 0.0)


def material(name, color, roughness=0.85):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
    return mat


def add_mesh(name, vertices, faces, mat, collection):
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


def add_curve(name, points, bevel, mat, collection):
    curve = bpy.data.curves.new(name + "Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = bevel
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(len(points) - 1)
    for p, co in zip(spline.points, points):
        p.co = (*co, 1.0)
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


def add_marker(name, xy, radius, height, mat, collection):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=24, radius=radius, depth=height,
        location=(xy[0], xy[1], height / 2.0)
    )
    obj = bpy.context.object
    obj.name = name
    # Move the newly created object into the project collection.
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


def add_label(body, location, size, mat, collection):
    data = bpy.data.curves.new(body + "Label", "FONT")
    data.body = body
    data.size = size
    data.extrude = 0
    obj = bpy.data.objects.new(body + "Label", data)
    obj.location = location
    collection.objects.link(obj)
    if mat:
        obj.data.materials.append(mat)
    return obj


def main():
    if not SOURCE.exists():
        raise RuntimeError(
            f"Missing {SOURCE}. Run scripts/build_first_corridor.py first."
        )
    geo = json.loads(SOURCE.read_text(encoding="utf-8"))
    by_kind = {f.get("properties", {}).get("kind"): f for f in geo.get("features", [])}
    required = ("test_corridor", "candidate_centerline",
                "original_toll_plaza_coordinate", "snapped_start_on_candidate_road")
    missing = [k for k in required if k not in by_kind]
    if missing:
        raise RuntimeError("GeoJSON is missing features: " + ", ".join(missing))

    # Remove only this generated collection, preserving other Blender work.
    old = bpy.data.collections.get(COLLECTION_NAME)
    if old:
        for obj in list(old.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(old)

    collection = bpy.data.collections.new(COLLECTION_NAME)
    bpy.context.scene.collection.children.link(collection)

    ground_mat = material("Corridor | muted sand", (0.58, 0.48, 0.30))
    edge_mat = material("Corridor | boundary", (0.28, 0.20, 0.09))
    line_mat = material("Road | centreline guide", (0.12, 0.09, 0.05))
    toll_mat = material("Marker | Toll Plaza", (0.72, 0.08, 0.06))
    snap_mat = material("Marker | road snap", (0.05, 0.25, 0.55))
    label_mat = material("Labels", (0.04, 0.04, 0.04))

    polygon_wgs = by_kind["test_corridor"]["geometry"]["coordinates"][0]
    polygon = [project(p) for p in polygon_wgs]
    # Drop duplicate closing vertex for mesh face.
    if len(polygon) > 2 and polygon[0] == polygon[-1]:
        polygon = polygon[:-1]
    add_mesh("200m_Corridor_Ground", polygon, [tuple(range(len(polygon)))],
             ground_mat, collection)

    # Draw polygon boundary as a thin raised line.
    boundary = [(x, y, 0.35) for x, y, _ in polygon]
    boundary.append(boundary[0])
    add_curve("Corridor_Boundary_Outline", boundary, 0.45, edge_mat, collection)

    centre_wgs = by_kind["candidate_centerline"]["geometry"]["coordinates"]
    centre = [project(p) for p in centre_wgs]
    centre_raised = [(x, y, 0.55) for x, y, _ in centre]
    # This is a visual centreline guide only; it does not represent road width.
    add_curve("OSM_Road_Centreline_Guide", centre_raised, 0.65,
              line_mat, collection)

    toll = project(by_kind["original_toll_plaza_coordinate"]["geometry"]["coordinates"])
    snap = project(by_kind["snapped_start_on_candidate_road"]["geometry"]["coordinates"])
    add_marker("Toll_Plaza_Reference", toll[:2], 5.0, 2.0, toll_mat, collection)
    add_marker("Road_Snap_Reference", snap[:2], 3.5, 1.6, snap_mat, collection)
    add_label("Toll Plaza", (toll[0] + 8, toll[1] + 8, 2.5), 5.0, label_mat, collection)
    add_label("OSM road snap", (snap[0] + 8, snap[1] - 10, 2.2), 3.5, label_mat, collection)

    # Store source and scale metadata on the collection.
    props = geo.get("properties", {})
    collection["source"] = "© OpenStreetMap contributors"
    collection["source_osm_way_id"] = int(props.get("source_osm_way_id", 170335647))
    collection["length_m"] = float(props.get("length_m", 1000))
    collection["width_m"] = float(props.get("width_m", 200))
    collection["snap_distance_m"] = float(props.get("toll_to_mapped_road_snap_distance_m", 0))
    collection["status"] = "Candidate alignment - not yet field/image verified"

    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"

    # Set a useful top-down viewport and save the project.
    bpy.ops.object.select_all(action="DESELECT")
    for area in bpy.context.screen.areas if bpy.context.screen else []:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.region_3d.view_perspective = "ORTHO"
            space.region_3d.view_location = (0.0, 500.0, 0.0)
            space.region_3d.view_distance = 1250.0
            space.region_3d.view_rotation = (1.0, 0.0, 0.0, 0.0)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT))

    print("MIANWALI BLENDER MAP CREATED")
    print(f"Source: {SOURCE}")
    print(f"Output: {OUTPUT}")
    print("Scale: metres | Corridor: 1000 m x 200 m")
    print("Objects: ground polygon, boundary, centreline guide, two reference markers")
    print("Note: flat candidate base only; no elevation or building data added.")


if __name__ == "__main__":
    main()
