"""UV, bake, export and preview the scrapyard cars built by build_scrapyard_cars.py.

Run inside Blender with a global STEP set to one of:
  "uv"       smart-UV-project each car
  "bake"     bake the procedural rust/soot/chip shader to <Car>_albedo.png
  "export"   swap in the baked material and export <Car>.fbx
  "preview"  render 3/4 preview PNGs
  "save"     write assets/models/scrapyard_cars.blend (only the ScrapyardCars scene)
Optional global CARS limits which cars a step touches.
"""

import math
import os

import bpy
from mathutils import Vector

REPO = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
EXPORT_DIR = os.path.join(REPO, "assets", "models", "export")
PREVIEW_DIR = os.path.join(REPO, "assets", "models", "previews")
BLEND_PATH = os.path.join(REPO, "assets", "models", "scrapyard_cars.blend")
SCENE_NAME = "ScrapyardCars"
TEX_SIZE = 1024


def enum_ids(rna_struct, prop):
    return [i.identifier for i in rna_struct.bl_rna.properties[prop].enum_items]


def checked(rna_struct, prop, value):
    ids = enum_ids(rna_struct, prop)
    if value not in ids:
        raise RuntimeError(f"{prop}={value!r} not in {ids}")
    return value


def scene():
    return bpy.data.scenes[SCENE_NAME]


def cars():
    names = globals().get("CARS") or ["ScrapSedan", "ScrapPickup"]
    return [bpy.data.objects[n] for n in names]


def set_engine(sc, want):
    try:
        sc.render.engine = want
    except TypeError as e:
        raise RuntimeError(f"engine {want} unavailable: {e}")


def only_select(sc, ob):
    vl = sc.view_layers[0]
    vl.update()
    for o in sc.objects:
        o.select_set(False)
    ob.hide_set(False)
    ob.select_set(True)
    vl.objects.active = ob


# --------------------------------------------------------------------------

def step_uv():
    sc = scene()
    for ob in cars():
        only_select(sc, ob)
        me = ob.data
        while me.uv_layers:
            me.uv_layers.remove(me.uv_layers[0])
        me.uv_layers.new(name="UVMap")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=0.004,
                                 area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        uvs = [d.uv for d in me.uv_layers[0].data]
        lo = min(min(u.x, u.y) for u in uvs)
        hi = max(max(u.x, u.y) for u in uvs)
        print(f"{ob.name}: {len(me.uv_layers)} UV map, range {lo:.3f}..{hi:.3f}")


def link(nt, a, b):
    nt.links.new(a, b)


def node(nt, kind, loc, **inputs):
    n = nt.nodes.new(kind)
    n.location = loc
    for k, v in inputs.items():
        n.inputs[k].default_value = v
    return n


def map_range(nt, loc, value, a, b, c=0.0, d=1.0):
    m = node(nt, "ShaderNodeMapRange", loc)
    m.clamp = True
    link(nt, value, m.inputs["Value"])
    m.inputs["From Min"].default_value = a
    m.inputs["From Max"].default_value = b
    m.inputs["To Min"].default_value = c
    m.inputs["To Max"].default_value = d
    return m.outputs["Result"]


def math_node(nt, loc, op, a, b):
    m = node(nt, "ShaderNodeMath", loc)
    m.operation = checked(m, "operation", op)
    for sock, val in ((m.inputs[0], a), (m.inputs[1], b)):
        if isinstance(val, (int, float)):
            sock.default_value = val
        else:
            link(nt, val, sock)
    return m.outputs[0]


def mix_col(nt, loc, fac, a, b):
    m = node(nt, "ShaderNodeMix", loc)
    m.data_type = checked(m, "data_type", "RGBA")
    m.clamp_factor = True
    ins = [s for s in m.inputs if s.type == "RGBA"]
    fac_in = next(s for s in m.inputs if s.name == "Factor" and s.type == "VALUE")
    for sock, val in ((fac_in, fac), (ins[0], a), (ins[1], b)):
        if isinstance(val, tuple):
            sock.default_value = val
        elif isinstance(val, (int, float)):
            sock.default_value = val
        else:
            link(nt, val, sock)
    return next(s for s in m.outputs if s.type == "RGBA")


def noise_tex(nt, loc, vec, scale, detail, rough, offset=(0, 0, 0)):
    mp = node(nt, "ShaderNodeMapping", (loc[0] - 200, loc[1]))
    link(nt, vec, mp.inputs["Vector"])
    mp.inputs["Location"].default_value = offset
    n = node(nt, "ShaderNodeTexNoise", loc)
    link(nt, mp.outputs["Vector"], n.inputs["Vector"])
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    return n


def ramp(nt, loc, fac, stops):
    r = node(nt, "ShaderNodeValToRGB", loc)
    link(nt, fac, r.inputs["Fac"])
    els = r.color_ramp.elements
    while len(els) < len(stops):
        els.new(0.5)
    for el, (pos, col) in zip(els, stops):
        el.position = pos
        el.color = (*col, 1.0)
    return r.outputs["Color"]


def build_bake_material(name):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial", (1800, 0))
    bsdf = node(nt, "ShaderNodeBsdfPrincipled", (1500, 0))
    link(nt, bsdf.outputs[0], out.inputs["Surface"])

    base = node(nt, "ShaderNodeAttribute", (-1200, 300))
    base.attribute_name = "Base"
    mask = node(nt, "ShaderNodeAttribute", (-1200, 0))
    mask.attribute_name = "Mask"
    sep = node(nt, "ShaderNodeSeparateColor", (-1000, 0))
    link(nt, mask.outputs["Color"], sep.inputs[0])
    rust_amt, soot_amt, chip_amt = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    tc = node(nt, "ShaderNodeTexCoord", (-1400, -400))
    obj = tc.outputs["Object"]
    xyz = node(nt, "ShaderNodeSeparateXYZ", (-1200, -600))
    link(nt, obj, xyz.inputs[0])
    z = xyz.outputs["Z"]

    # sun-faded base colour
    hsv = node(nt, "ShaderNodeHueSaturation", (-900, 300))
    link(nt, base.outputs["Color"], hsv.inputs["Color"])
    hsv.inputs["Saturation"].default_value = 0.72
    hsv.inputs["Value"].default_value = 0.9

    # paint chips to primer
    n_chip = noise_tex(nt, (-700, 500), obj, 3.2, 10, 0.7, (11, 2, 5))
    chip_v = math_node(nt, (-500, 500), "ADD", n_chip.outputs["Fac"],
                       math_node(nt, (-700, 650), "MULTIPLY", chip_amt, 0.32))
    chip = map_range(nt, (-300, 500), chip_v, 0.715, 0.735)
    col = mix_col(nt, (0, 300), chip, hsv.outputs["Color"], (0.21, 0.2, 0.19, 1))

    # soot and ash
    n_soot = noise_tex(nt, (-700, 100), obj, 0.6, 5, 0.6, (3, 9, 1))
    soot_v = math_node(nt, (-500, 100), "ADD", n_soot.outputs["Fac"], soot_amt)
    soot_v = math_node(nt, (-400, 150), "SUBTRACT", soot_v,
                       map_range(nt, (-600, 250), z, 2.0, 3.4, 0.45, 0.0))  # paint survives low down
    soot = map_range(nt, (-300, 100), soot_v, 0.75, 1.05)
    n_ash = noise_tex(nt, (-700, -100), obj, 2.0, 6, 0.6, (5, 5, 5))
    ash = ramp(nt, (-300, -100), n_ash.outputs["Fac"],
               [(0.35, (0.025, 0.023, 0.022)), (0.6, (0.09, 0.085, 0.08)), (0.75, (0.22, 0.21, 0.2))])
    col = mix_col(nt, (250, 200), soot, col, ash)

    # rust: patchy, heavier low down
    n_rust = noise_tex(nt, (-700, -350), obj, 0.55, 8, 0.68)
    low = map_range(nt, (-700, -550), z, 0.0, 4.5, 0.18, 0.0)
    rust_v = math_node(nt, (-500, -350), "ADD", n_rust.outputs["Fac"],
                       math_node(nt, (-500, -500), "ADD",
                                 math_node(nt, (-700, -700), "MULTIPLY", rust_amt, 0.75), low))
    rust_v = math_node(nt, (-350, -400), "MULTIPLY", rust_v,
                       map_range(nt, (-500, -800), rust_amt, 0.0, 0.05))
    rust = map_range(nt, (-200, -350), rust_v, 0.84, 0.96)
    n_rc = noise_tex(nt, (-300, -650), obj, 2.6, 8, 0.65, (2, 7, 3))
    rust_col = ramp(nt, (-100, -650), n_rc.outputs["Fac"],
                    [(0.3, (0.08, 0.035, 0.018)), (0.5, (0.27, 0.105, 0.04)), (0.7, (0.16, 0.07, 0.03))])
    col = mix_col(nt, (500, 0), rust, col, rust_col)

    # broad dirt and weathering variation
    n_dirt = noise_tex(nt, (300, -500), obj, 0.9, 4, 0.55, (8, 1, 6))
    dirt = map_range(nt, (500, -500), n_dirt.outputs["Fac"], 0.3, 0.7, 0.55, 1.0)
    col = mix_col(nt, (700, -100), dirt, (0, 0, 0, 1), col)

    # ambient occlusion grime
    ao = node(nt, "ShaderNodeAmbientOcclusion", (600, -300))
    ao.samples = 16
    ao.inputs["Distance"].default_value = 1.2
    ao_f = map_range(nt, (800, -300), ao.outputs["AO"], 0.0, 1.0, 0.3, 1.0)
    col = mix_col(nt, (1000, 0), ao_f, (0, 0, 0, 1), col)
    link(nt, col, bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.85
    return mat


def bake_image(name):
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, TEX_SIZE, TEX_SIZE, alpha=False)
    img.colorspace_settings.name = "sRGB"
    return img


def step_bake():
    sc = scene()
    set_engine(sc, "CYCLES")
    sc.cycles.samples = 32
    sc.render.bake.margin = 6
    for ob in cars():
        mat = build_bake_material(f"{ob.name}_ProceduralBake")
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        img = bake_image(f"{ob.name}_albedo")
        tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.location = (1500, 400)
        mat.node_tree.nodes.active = tex
        only_select(sc, ob)
        bake_props = bpy.ops.object.bake.get_rna_type().properties
        bake_types = [i.identifier for i in bake_props["type"].enum_items]
        if "DIFFUSE" not in bake_types:
            raise RuntimeError(f"DIFFUSE not in {bake_types}")
        bpy.ops.object.bake(type="DIFFUSE", pass_filter={"COLOR"}, margin=6, use_clear=True)
        path = os.path.join(EXPORT_DIR, f"{ob.name}_albedo.png")
        os.makedirs(EXPORT_DIR, exist_ok=True)
        img.filepath_raw = path
        img.file_format = "PNG"
        img.save()
        print(f"baked {path}")


def final_material(ob):
    name = f"{ob.name}_Mat"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = node(nt, "ShaderNodeOutputMaterial", (400, 0))
    bsdf = node(nt, "ShaderNodeBsdfPrincipled", (100, 0))
    link(nt, bsdf.outputs[0], out.inputs["Surface"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.location = (-300, 0)
    img = bpy.data.images.get(f"{ob.name}_albedo")
    path = os.path.join(EXPORT_DIR, f"{ob.name}_albedo.png")
    if img is None or os.path.normcase(bpy.path.abspath(img.filepath)) != os.path.normcase(path):
        img = bpy.data.images.load(path, check_existing=True)
    tex.image = img
    link(nt, tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.85
    bsdf.inputs["Metallic"].default_value = 0.0
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return mat


def step_export():
    sc = scene()
    props = bpy.ops.export_scene.fbx.get_rna_type().properties
    def pick(prop, value):
        ids = [i.identifier for i in props[prop].enum_items]
        if value not in ids:
            raise RuntimeError(f"{prop}={value!r} not in {ids}")
        return value
    for ob in cars():
        final_material(ob)
        only_select(sc, ob)
        loc = ob.location.copy()
        ob.location = (0, 0, 0)
        path = os.path.join(EXPORT_DIR, f"{ob.name}.fbx")
        try:
            bpy.ops.export_scene.fbx(
                filepath=path, use_selection=True,
                object_types={pick("object_types", "MESH")},
                apply_scale_options=pick("apply_scale_options", "FBX_SCALE_UNITS"),
                path_mode=pick("path_mode", "COPY"), embed_textures=True,
                add_leaf_bones=False, bake_anim=False,
                use_mesh_modifiers=True, use_tspace=False,
                colors_type=pick("colors_type", "NONE"),
                mesh_smooth_type=pick("mesh_smooth_type", "FACE"))
        finally:
            ob.location = loc
        print(f"exported {path} ({os.path.getsize(path) // 1024} KB)")


def step_preview():
    sc = scene()
    set_engine(sc, "CYCLES")
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1280, 800
    sc.render.film_transparent = False
    coll = bpy.data.collections.get("Preview_Stage")
    if coll is None:
        coll = bpy.data.collections.new("Preview_Stage")
        sc.collection.children.link(coll)
    if "Preview_Ground" not in bpy.data.objects:
        me = bpy.data.meshes.new("Preview_Ground")
        s = 60
        me.from_pydata([(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)], [], [(0, 1, 2, 3)])
        g = bpy.data.objects.new("Preview_Ground", me)
        coll.objects.link(g)
        gm = bpy.data.materials.new("Preview_Ground_Mat")
        gm.use_nodes = True
        b = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        b.inputs["Base Color"].default_value = (0.16, 0.14, 0.12, 1)
        b.inputs["Roughness"].default_value = 1.0
        me.materials.append(gm)
    if "Preview_Sun" not in bpy.data.objects:
        ld = bpy.data.lights.new("Preview_Sun", "SUN")
        ld.energy = 3.5
        ld.angle = math.radians(8)
        sun = bpy.data.objects.new("Preview_Sun", ld)
        sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
        coll.objects.link(sun)
    if sc.world is None:
        sc.world = bpy.data.worlds.new("Preview_World")
    sc.world.use_nodes = True
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.55, 0.62, 0.72, 1)
    bg.inputs["Strength"].default_value = 0.7
    if "Preview_Cam" not in bpy.data.objects:
        cd = bpy.data.cameras.new("Preview_Cam")
        cd.lens = 50
        cam = bpy.data.objects.new("Preview_Cam", cd)
        coll.objects.link(cam)
    cam = bpy.data.objects["Preview_Cam"]
    sc.camera = cam
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    all_cars = [bpy.data.objects[n] for n in ("ScrapSedan", "ScrapPickup")]
    views = globals().get("VIEWS") or {"3q": (1.0, -0.95, 0.55), "3q_rear": (-1.0, 0.9, 0.6)}
    for ob in cars():
        for other in all_cars:
            other.hide_render = other is not ob
        centre = ob.matrix_world @ Vector((0, 0, ob.dimensions.z * 0.42))
        for tag, d in views.items():
            dv = Vector(d).normalized()
            cam.location = centre + dv * 31.0
            cam.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
            sc.render.filepath = os.path.join(PREVIEW_DIR, f"{ob.name}_{tag}.png")
            bpy.ops.render.render(write_still=True)
            print("rendered", sc.render.filepath)
    for other in all_cars:
        other.hide_render = False


def step_save():
    sc = scene()
    blocks = {sc}
    bpy.data.libraries.write(BLEND_PATH, blocks, path_remap="RELATIVE_ALL", fake_user=True,
                             compress=True)
    print(f"wrote {BLEND_PATH} ({os.path.getsize(BLEND_PATH) // 1024} KB)")


{"uv": step_uv, "bake": step_bake, "export": step_export,
 "preview": step_preview, "save": step_save}[STEP]()
