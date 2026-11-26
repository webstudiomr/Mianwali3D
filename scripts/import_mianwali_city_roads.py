"""Import Mianwali city general roads into Blender as a clean flat road map.
Run inside Blender's Text Editor. Project root is fixed for this PC.
Road widths are illustrative defaults by OSM class, not surveyed measurements.
"""
import bpy, json, math
from pathlib import Path

ROOT = Path(r"C:\Mianwali3D")
SOURCE = ROOT / "data" / "mianwali_city_general_roads.geojson"
OUTPUT = ROOT / "exports" / "Mianwali_City_Roads.blend"
COLLECTION_NAME = "Mianwali_City_General_Roads"
EARTH_R = 6371008.8

if not SOURCE.exists():
    raise RuntimeError(f"Missing {SOURCE}. Run build_mianwali_city_map.py first.")
geo=json.loads(SOURCE.read_text(encoding="utf-8"))
features=geo.get("features",[])
if not features:
    raise RuntimeError("No road features found in GeoJSON.")

bbox=geo["bbox_wgs84"]
ORIGIN_LON=(bbox[0]+bbox[2])/2
ORIGIN_LAT=(bbox[1]+bbox[3])/2
def project(p):
    lon,lat=p
    x=math.radians(lon-ORIGIN_LON)*EARTH_R*math.cos(math.radians(ORIGIN_LAT))
    y=math.radians(lat-ORIGIN_LAT)*EARTH_R
    return (x,y,0.18)

def mat(name,color):
    m=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    return m

old=bpy.data.collections.get(COLLECTION_NAME)
if old:
    for o in list(old.objects): bpy.data.objects.remove(o,do_unlink=True)
    bpy.data.collections.remove(old)
coll=bpy.data.collections.new(COLLECTION_NAME)
bpy.context.scene.collection.children.link(coll)

asphalt=mat("Roads | charcoal asphalt",(0.075,0.085,0.09))
mainroad=mat("Roads | main routes",(0.12,0.13,0.14))
ground=mat("Map | muted ground",(0.42,0.46,0.39))
widths={"trunk":7.0,"primary":6.0,"secondary":4.8,"tertiary":3.8,"unclassified":3.2,"road":3.2,
        "trunk_link":6.0,"primary_link":5.0,"secondary_link":4.2,"tertiary_link":3.5}

# Ground is only a neutral flat presentation surface, not real terrain.
corners=[project((bbox[0],bbox[1])),project((bbox[2],bbox[1])),project((bbox[2],bbox[3])),project((bbox[0],bbox[3]))]
verts=[(p[0],p[1],-0.15) for p in corners]
mesh=bpy.data.meshes.new("Mianwali_Map_Ground_Mesh")
mesh.from_pydata(verts,[],[(0,1,2,3)]); mesh.materials.append(ground)
obj=bpy.data.objects.new("Flat_Map_Ground_Not_Terrain",mesh); coll.objects.link(obj)

counts={}
for i,f in enumerate(features):
    coords=f.get("geometry",{}).get("coordinates",[])
    if len(coords)<2: continue
    kind=f.get("properties",{}).get("highway","road")
    pts=[project(p) for p in coords]
    curve=bpy.data.curves.new(f"OSM_{kind}_{i}","CURVE")
    curve.dimensions="3D"; curve.resolution_u=1
    curve.bevel_depth=widths.get(kind,3.2)/2
    curve.bevel_resolution=1
    spline=curve.splines.new("POLY")
    spline.points.add(len(pts)-1)
    for point,co in zip(spline.points,pts): point.co=(*co,1)
    ob=bpy.data.objects.new(f"Road_{kind}_{i}",curve)
    coll.objects.link(ob)
    curve.materials.append(mainroad if kind in ("trunk","primary","secondary") else asphalt)
    counts[kind]=counts.get(kind,0)+1

scene=bpy.context.scene
scene.unit_settings.system="METRIC"
scene.unit_settings.length_unit="METERS"
# Select generated collection and configure top view in any open 3D viewport.
bpy.ops.object.select_all(action="DESELECT")
for area in bpy.context.screen.areas if bpy.context.screen else []:
    if area.type=="VIEW_3D":
        sp=area.spaces.active
        sp.region_3d.view_perspective="ORTHO"
        sp.region_3d.view_location=(0,0,0)
        sp.region_3d.view_distance=max((corners[2][0]-corners[0][0])*1.35,3000)
        sp.region_3d.view_rotation=(1,0,0,0)
OUTPUT.parent.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT))
print("MIANWALI CITY ROAD MAP CREATED")
print("Output:",OUTPUT)
print("Road objects:",sum(counts.values()),"| classes:",counts)
print("Flat schematic road map; widths estimated; no buildings or terrain.")
