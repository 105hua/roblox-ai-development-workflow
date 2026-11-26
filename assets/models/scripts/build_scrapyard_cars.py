"""Build two generic scrapyard wrecks for Roblox: ScrapSedan and ScrapPickup.

Run inside Blender (Text Editor > Run Script, or exec() through the Blender MCP).
Everything is modelled by hand from bmesh primitives, lofts and booleans. No
library assets, no generators.

Units: 1 Blender unit = 1 Roblox stud (Scene > Units > Unit System = None), as
the Roblox Blender guide recommends. Front of each car points along +X, up is +Z.

Each car ends up as ONE mesh object with two corner colour attributes:
  Base  - flat base colour per part (paint, interior, rims, glass ...)
  Mask  - R = rust amount, G = soot/burn amount, B = paint-chip amount
bake_export_scrapyard_cars.py turns those into a baked albedo texture.
"""

import math

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

SCENE_NAME = "ScrapyardCars"


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def enum_ids(rna_struct, prop):
    return [i.identifier for i in rna_struct.bl_rna.properties[prop].enum_items]


def checked(rna_struct, prop, value):
    ids = enum_ids(rna_struct, prop)
    if value not in ids:
        raise RuntimeError(f"{prop}={value!r} not in {ids}")
    return value


def lerp_table(table, x):
    """Piecewise interpolation with smoothstep between keys."""
    if x <= table[0][0]:
        return table[0][1]
    for (x0, v0), (x1, v1) in zip(table, table[1:]):
        if x <= x1:
            t = (x - x0) / (x1 - x0)
            t = t * t * (3 - 2 * t)
            return v0 + (v1 - v0) * t
    return table[-1][1]


def T(x, y, z):
    return Matrix.Translation((x, y, z))


def R(deg, axis):
    return Matrix.Rotation(math.radians(deg), 4, axis)


def about(pivot, m):
    """Apply matrix m around a pivot point."""
    return T(*pivot) @ m @ T(*(-c for c in pivot))


def dent_offset(p, center, radius, vec):
    d = (Vector(p) - Vector(center)).length
    if d >= radius:
        return Vector((0, 0, 0))
    f = (1 - (d / radius) ** 2) ** 2
    return Vector(vec) * f


def dent(verts, center, radius, vec):
    for v in verts:
        v.co += dent_offset(v.co, center, radius, vec)


# --------------------------------------------------------------------------
# geometry generators: return (coords, faces) in local space
# --------------------------------------------------------------------------

def box_geo(x0, x1, y0, y1, z0, z1, nx=1, ny=1):
    coords, faces = [], []

    def vid(layer, i, j):
        return layer * (nx + 1) * (ny + 1) + i * (ny + 1) + j

    for layer, z in ((0, z0), (1, z1)):
        for i in range(nx + 1):
            for j in range(ny + 1):
                coords.append((x0 + (x1 - x0) * i / nx, y0 + (y1 - y0) * j / ny, z))
    B = lambda i, j: vid(0, i, j)
    U = lambda i, j: vid(1, i, j)
    for i in range(nx):
        for j in range(ny):
            faces.append((U(i, j), U(i + 1, j), U(i + 1, j + 1), U(i, j + 1)))
            faces.append((B(i, j), B(i, j + 1), B(i + 1, j + 1), B(i + 1, j)))
    for i in range(nx):
        faces.append((B(i, 0), B(i + 1, 0), U(i + 1, 0), U(i, 0)))
        faces.append((B(i + 1, ny), B(i, ny), U(i, ny), U(i + 1, ny)))
    for j in range(ny):
        faces.append((B(0, j + 1), B(0, j), U(0, j), U(0, j + 1)))
        faces.append((B(nx, j), B(nx, j + 1), U(nx, j + 1), U(nx, j)))
    return coords, faces


def lathe_geo(profile, seg):
    """Revolve (r, z) profile around local Z. r == 0 points become poles."""
    coords, faces, rings = [], [], []
    for r, z in profile:
        if r <= 1e-6:
            coords.append((0, 0, z))
            rings.append([len(coords) - 1] * seg)
        else:
            ring = []
            for k in range(seg):
                a = 2 * math.pi * k / seg
                coords.append((r * math.cos(a), r * math.sin(a), z))
                ring.append(len(coords) - 1)
            rings.append(ring)
    for ra, rb in zip(rings, rings[1:]):
        for k in range(seg):
            k2 = (k + 1) % seg
            quad = [ra[k], ra[k2], rb[k2], rb[k]]
            uniq = []
            for q in quad:
                if q not in uniq:
                    uniq.append(q)
            if len(uniq) >= 3:
                faces.append(tuple(uniq))
    return coords, faces


def cyl_geo(r, z0, z1, seg=12):
    return lathe_geo([(0, z0), (r, z0), (r, z1), (0, z1)], seg)


def torus_geo(R_, r, nu=12, nv=6):
    coords, faces = [], []
    for i in range(nu):
        u = 2 * math.pi * i / nu
        for j in range(nv):
            v = 2 * math.pi * j / nv
            coords.append(((R_ + r * math.cos(v)) * math.cos(u),
                           (R_ + r * math.cos(v)) * math.sin(u),
                           r * math.sin(v)))
    for i in range(nu):
        for j in range(nv):
            a = i * nv + j
            b = ((i + 1) % nu) * nv + j
            c = ((i + 1) % nu) * nv + (j + 1) % nv
            d = i * nv + (j + 1) % nv
            faces.append((a, b, c, d))
    return coords, faces


def prism_geo(corners, thick):
    """Flat polygon (3+ coplanar corners) extruded by thick along its normal."""
    P = [Vector(c) for c in corners]
    n = (P[1] - P[0]).cross(P[-1] - P[0]).normalized()
    top = [tuple(p) for p in P]
    bot = [tuple(p - n * thick) for p in P]
    m = len(P)
    coords = top + bot
    faces = [tuple(range(m)), tuple(reversed(range(m, 2 * m)))]
    for k in range(m):
        k2 = (k + 1) % m
        faces.append((k, m + k, m + k2, k2))
    return coords, faces


def beam_geo(p0, p1, a, b):
    """Rectangular bar from p0 to p1 with cross-section a x b."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0).normalized()
    hint = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
    u = d.cross(hint).normalized()
    v = u.cross(d).normalized()
    coords = []
    for c in (p0, p1):
        for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            coords.append(tuple(c + u * (su * a / 2) + v * (sv * b / 2)))
    faces = [(3, 2, 1, 0), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    return coords, faces


def rounded_rect(w, zb, zt, rt, rb, n):
    """Closed car cross-section in (y, z), resampled to n evenly spaced points,
    starting at the right-hand middle and running counter-clockwise."""
    hw = w / 2
    h = zt - zb
    rt = min(rt, hw, h / 2)
    rb = min(rb, hw, h / 2)
    pts = [(hw, (zb + zt) / 2)]

    def arc(cy, cz, r, a0, a1, k=8):
        for i in range(k + 1):
            a = math.radians(a0 + (a1 - a0) * i / k)
            pts.append((cy + r * math.cos(a), cz + r * math.sin(a)))

    arc(hw - rt, zt - rt, rt, 0, 90)
    arc(-hw + rt, zt - rt, rt, 90, 180)
    arc(-hw + rb, zb + rb, rb, 180, 270)
    arc(hw - rb, zb + rb, rb, 270, 360)
    P = pts + [pts[0]]
    cum = [0.0]
    for p, q in zip(P, P[1:]):
        cum.append(cum[-1] + math.hypot(q[0] - p[0], q[1] - p[1]))
    L = cum[-1]
    out, j = [], 0
    for i in range(n):
        s = L * i / n
        while cum[j + 1] < s:
            j += 1
        p, q = P[j], P[j + 1]
        seg = cum[j + 1] - cum[j]
        t = (s - cum[j]) / seg if seg > 0 else 0
        out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def body_rings(xs, zb, zt, wt, tp, n=32, rt=0.55, rb=0.3):
    rings = []
    for x in xs:
        w = lerp_table(wt, x)
        a = lerp_table(zb, x)
        b = lerp_table(zt, x)
        t = lerp_table(tp, x)
        zm = (a + b) / 2
        ring = []
        for y, z in rounded_rect(w, a, b, rt, rb, n):
            if z > zm:
                y *= 1 - (1 - t) * ((z - zm) / ((b - a) / 2))
            ring.append((x, y, z))
        rings.append(ring)
    return rings


def loft_geo(rings):
    coords, faces = [], []
    n = len(rings[0])
    for ring in rings:
        coords.extend(ring)
    for i in range(len(rings) - 1):
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((i * n + k, i * n + k2, (i + 1) * n + k2, (i + 1) * n + k))
    for idx, ring in ((0, rings[0]), (len(rings) - 1, rings[-1])):
        c = Vector((0, 0, 0))
        for p in ring:
            c += Vector(p)
        coords.append(tuple(c / n))
        ci = len(coords) - 1
        for k in range(n):
            faces.append((ci, idx * n + (k + 1) % n, idx * n + k))
    return coords, faces


# --------------------------------------------------------------------------
# Part: a bmesh with Base / Mask colour layers
# --------------------------------------------------------------------------

class Part:
    def __init__(self):
        self.bm = bmesh.new()
        self.cb = self.bm.loops.layers.color.new("Base")
        self.cm = self.bm.loops.layers.color.new("Mask")

    def paint(self, faces, base, mask):
        b = (*base, 1.0)
        m = (*mask, 1.0)
        for f in faces:
            for l in f.loops:
                l[self.cb] = b
                l[self.cm] = m

    def add(self, geo, base, mask, matrix=None):
        coords, faces = geo
        vs = [self.bm.verts.new(matrix @ Vector(c) if matrix else Vector(c)) for c in coords]
        fs = [self.bm.faces.new([vs[i] for i in f]) for f in faces]
        self.paint(fs, base, mask)
        return vs, fs

    def fix_normals(self):
        bmesh.ops.recalc_face_normals(self.bm, faces=self.bm.faces[:])
        self.bm.normal_update()

    def to_object(self, name, coll):
        self.fix_normals()
        me = bpy.data.meshes.new(name)
        self.bm.to_mesh(me)
        self.bm.free()
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        return ob


# --------------------------------------------------------------------------
# scene / boolean plumbing
# --------------------------------------------------------------------------

def get_scene():
    sc = bpy.data.scenes.get(SCENE_NAME) or bpy.data.scenes.new(SCENE_NAME)
    us = sc.unit_settings
    us.system = checked(us, "system", "NONE")
    us.system_rotation = checked(us, "system_rotation", "DEGREES")
    for win in bpy.context.window_manager.windows:
        win.scene = sc
    return sc


def fresh_collection(sc, name):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        sc.collection.children.link(coll)
    for ob in list(coll.objects):
        me = ob.data if ob.type == "MESH" else None
        bpy.data.objects.remove(ob)
        if me is not None and me.users == 0:
            bpy.data.meshes.remove(me)
    return coll


def make_cutters(sc, name, parts):
    coll = fresh_collection(sc, name)
    for i, part in enumerate(parts):
        ob = part.to_object(f"{name}_{i:02d}", coll)
        ob.display_type = checked(ob, "display_type", "WIRE")
    return coll


def drop_collection(coll):
    for ob in list(coll.objects):
        me = ob.data
        bpy.data.objects.remove(ob)
        if me.users == 0:
            bpy.data.meshes.remove(me)
    bpy.data.collections.remove(coll)


def apply_boolean(sc, target, coll, operation):
    mod = target.modifiers.new("Bool", checked(bpy.types.Modifier, "type", "BOOLEAN"))
    mod.operation = checked(mod, "operation", operation)
    mod.operand_type = checked(mod, "operand_type", "COLLECTION")
    mod.collection = coll
    mod.solver = checked(mod, "solver", "EXACT")
    vl = sc.view_layers[0]
    vl.update()
    dg = vl.depsgraph
    ev = target.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    target.modifiers.remove(mod)
    old = target.data
    target.data = me
    bpy.data.meshes.remove(old)


def remove_flaps(bm):
    """The exact boolean can leave zero-volume flaps: pairs of back-to-back faces
    on the same vertices where a wall pinches to nothing. Deleting both faces of
    each pair keeps the surrounding surface closed and makes it manifold again."""
    bm.verts.index_update()
    seen, kill = {}, set()
    for f in bm.faces:
        key = tuple(sorted(v.index for v in f.verts))
        if key in seen:
            kill.update((f, seen[key]))
        else:
            seen[key] = f
    if kill:
        bmesh.ops.delete(bm, geom=list(kill), context="FACES_ONLY")
    loose_e = [e for e in bm.edges if not e.link_faces]
    if loose_e:
        bmesh.ops.delete(bm, geom=loose_e, context="EDGES")
    loose_v = [v for v in bm.verts if not v.link_edges]
    if loose_v:
        bmesh.ops.delete(bm, geom=loose_v, context="VERTS")
    return len(kill)


def assemble(sc, coll, name, body, bool_steps, parts, location):
    """body: Part to carve; bool_steps: [(operation, [Part, ...]), ...];
    parts: Parts merged in unchanged. Returns the final single-mesh object."""
    body_ob = body.to_object(name + "_body_tmp", coll)
    for step, (op, cutters) in enumerate(bool_steps):
        ccoll = make_cutters(sc, f"{name}_bool{step}", cutters)
        apply_boolean(sc, body_ob, ccoll, op)
        drop_collection(ccoll)

    bm = bmesh.new()
    bm.from_mesh(body_ob.data)
    for p in parts:
        tmp = bpy.data.meshes.new("tmp")
        p.fix_normals()
        p.bm.to_mesh(tmp)
        p.bm.free()
        bm.from_mesh(tmp)
        bpy.data.meshes.remove(tmp)
    old_body = body_ob.data
    bpy.data.objects.remove(body_ob)
    bpy.data.meshes.remove(old_body)

    bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=bm.edges[:])
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    remove_flaps(bm)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

    # origin at the base centre
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    off = Vector(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, min(zs)))
    bmesh.ops.translate(bm, verts=bm.verts[:], vec=-off)

    me = bpy.data.meshes.get(name)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(40))
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.location = location
    return ob


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# --------------------------------------------------------------------------
# palette: (base colour, mask (rust, soot, chips))
# --------------------------------------------------------------------------

UNDER = ((0.10, 0.065, 0.045), (0.9, 0.1, 0.0))
DARK = ((0.025, 0.025, 0.025), (0.3, 0.0, 0.0))
GLASS = ((0.04, 0.055, 0.06), (0.0, 0.0, 0.0))
LAMP = ((0.16, 0.16, 0.15), (0.0, 0.0, 0.0))
RED = ((0.42, 0.035, 0.03), (0.0, 0.0, 0.0))
STEEL = ((0.30, 0.30, 0.31), (0.85, 0.0, 0.2))
CHROME = ((0.40, 0.40, 0.41), (0.6, 0.0, 0.3))


def wheel_well(part, x, z, r, y_in, y_out, colour):
    part.add(cyl_geo(r, y_in, y_out, 16), *colour, T(x, 0, z) @ R(-90, "X"))


# --------------------------------------------------------------------------
# ScrapSedan: rusted four-door, sitting on bare rims, both left doors gone,
# roof caved in, windscreen out, rear bumper hanging off.
# --------------------------------------------------------------------------

def build_sedan(sc, coll, location):
    PAINT = ((0.40, 0.09, 0.07), (0.6, 0.0, 0.45))
    INTER = ((0.15, 0.13, 0.11), (0.25, 0.0, 0.1))
    SEAT = ((0.24, 0.19, 0.14), (0.1, 0.0, 0.15))

    zb = [(-8, 1.35), (-7.2, 0.9), (7.2, 0.9), (8, 1.35)]
    zt = [(-8, 2.75), (-7.5, 3.05), (-4.6, 3.2), (3.0, 3.2), (3.8, 3.0), (7.4, 2.8), (8, 2.45)]
    wt = [(-8, 6.1), (-7.4, 6.5), (-5, 6.6), (5, 6.6), (7.4, 6.5), (8, 6.1)]
    tp = [(-8, 0.97), (-4.6, 0.93), (3.0, 0.93), (8, 0.97)]
    xs = [-8 + 16 * i / 26 for i in range(27)]

    body = Part()
    body.add(loft_geo(body_rings(xs, zb, zt, wt, tp)), *PAINT)
    body.fix_normals()
    for v in body.bm.verts:
        v.co += v.normal * (noise.noise(v.co * 0.45) * 0.07)
    dent(body.bm.verts, (8.0, -3.4, 2.7), 2.4, (-0.55, 0.35, -0.15))  # front corner hit
    dent(body.bm.verts, (-1.2, -3.4, 2.1), 1.7, (0, 0.3, 0))          # side dent
    dent(body.bm.verts, (5.6, 1.2, 3.0), 1.6, (0, 0, -0.3))           # bonnet
    dent(body.bm.verts, (-7.0, 2.5, 3.0), 1.5, (0, 0, -0.25))         # boot lid
    body.fix_normals()
    under = [f for f in body.bm.faces if f.normal.z < -0.6]
    body.paint(under, *UNDER)

    def cut(geo, colour, m=None):
        p = Part()
        p.add(geo, *colour, m)
        return p

    cutters = [
        cut(box_geo(-3.55, 2.95, -2.85, 2.85, 1.25, 4.5), INTER),       # cabin tub
        cut(box_geo(-3.4, 2.6, 2.3, 4.0, 1.45, 4.5), PAINT),            # left doors gone
        cut(box_geo(3.26, 3.34, -3.2, 3.2, 2.9, 3.6), DARK),            # bonnet seam
        cut(box_geo(-4.69, -4.61, -3.2, 3.2, 2.9, 3.6), DARK),          # boot seam
        cut(box_geo(7.75, 8.6, -1.5, 1.5, 1.55, 2.25), DARK),           # grille
        cut(box_geo(-8.6, -7.75, 2.0, 2.9, 2.25, 2.8), RED),            # tail lights
        cut(box_geo(-8.6, -7.75, -2.9, -2.0, 2.25, 2.8), RED),
        cut(box_geo(7.75, 8.6, 1.9, 2.9, 1.85, 2.3), LAMP),             # headlights
        cut(box_geo(7.75, 8.6, -2.9, -1.9, 1.85, 2.3), LAMP),
    ]
    for x in (-3.55, -0.6, 2.9):                                         # right door gaps
        cutters.append(cut(box_geo(x - 0.04, x + 0.04, -3.7, -3.0, 1.3, 3.4), DARK))
    for x in (-5.2, 5.2):
        for s in (-1, 1):
            p = Part()
            y_in, y_out = (2.05, 4.3) if s > 0 else (-4.3, -2.05)
            wheel_well(p, x, 1.05, 1.5, y_in, y_out, UNDER)
            cutters.append(p)

    parts = Part()

    # caved-in roof
    rz0, rz1 = 4.85, 5.03

    def roof_dz(x, y):
        dz = -0.22 * (y / 2.72) ** 2 - 0.1 * ((x + 0.7) / 2.05) ** 2
        dz += dent_offset((x, y, 5.0), (-0.5, 1.2, 5.0), 3.2, (0, 0, -1.0)).z
        dz += dent_offset((x, y, 5.0), (-0.9, 2.6, 5.0), 1.5, (0, 0, -0.4)).z
        return dz

    vs, _ = parts.add(box_geo(-2.75, 1.35, -2.72, 2.72, rz0, rz1, 10, 8), *PAINT)
    for v in vs:
        v.co.z += roof_dz(v.co.x, v.co.y)

    def roof_pt(x, y):
        return (x, y, rz0 + roof_dz(x, y) + 0.08)

    pillars = [
        ((2.95, -2.88, 2.95), roof_pt(1.25, -2.58)),   # A pillars
        ((2.95, 2.88, 2.95), roof_pt(1.25, 2.58)),
        ((-0.6, -2.92, 2.95), roof_pt(-0.6, -2.6)),    # B pillar (left one torn off)
        ((-4.2, -2.9, 3.0), roof_pt(-2.65, -2.6)),     # C pillars
        ((-4.2, 2.9, 3.0), roof_pt(-2.65, 2.6)),
    ]
    for p0, p1 in pillars:
        parts.add(beam_geo(p0, p1, 0.32, 0.22), *PAINT)
    parts.add(beam_geo((-0.6, 2.92, 3.0), (-0.45, 2.85, 3.55), 0.3, 0.2), *PAINT)  # torn stub

    # rear window, still in, cracked dark glass
    parts.add(prism_geo([(-4.25, -2.82, 3.1), (-4.25, 2.82, 3.1),
                         roof_pt(-2.68, 2.55), roof_pt(-2.68, -2.55)], 0.08), *GLASS)

    # interior
    for s in (-1, 1):
        y0, y1 = sorted((s * 0.45, s * 2.35))
        parts.add(box_geo(0.0, 1.4, y0, y1, 1.25, 2.05), *SEAT)
        parts.add(box_geo(-0.3, 0.1, y0, y1, 2.0, 3.6), *SEAT,
                  about((-0.1, 0, 2.0), R(-14, "Y")))
    parts.add(box_geo(-3.4, -2.1, -2.6, 2.6, 1.25, 2.0), *SEAT)
    parts.add(box_geo(-3.5, -3.15, -2.6, 2.6, 1.95, 3.4), *SEAT,
              about((-3.3, 0, 1.95), R(-10, "Y")))
    parts.add(box_geo(2.25, 2.95, -2.75, 2.75, 2.55, 3.25), *INTER)       # dashboard
    axis = Vector((-0.85, 0, 0.5)).normalized()
    wheel_rot = Vector((0, 0, 1)).rotation_difference(axis).to_matrix().to_4x4()
    parts.add(torus_geo(0.6, 0.07, 12, 4), *DARK, T(1.75, 1.4, 3.3) @ wheel_rot)
    parts.add(beam_geo((2.4, 1.4, 2.92), (1.75, 1.4, 3.3), 0.14, 0.14), *DARK)

    # bumpers: front bent, rear hanging off one bracket
    parts.add(box_geo(7.95, 8.45, -3.05, 3.05, 1.2, 1.8), *CHROME,
              about((8.2, 0, 1.5), R(5, "Z") @ R(3, "X")))
    parts.add(box_geo(-8.5, -8.05, -3.05, 3.05, 1.25, 1.85), *CHROME,
              about((-8.27, 3.0, 1.55), R(11.5, "X")))

    # bare rims sitting on the ground (r = 1.05)
    rim = [(0, -0.36), (0.9, -0.36), (1.05, -0.33), (1.05, -0.24), (0.94, -0.2),
           (0.94, 0.2), (1.05, 0.24), (1.05, 0.33), (0.86, 0.3), (0.4, 0.18),
           (0.3, 0.36), (0, 0.36)]
    for x in (-5.2, 5.2):
        for s in (-1, 1):
            m = T(x, s * 2.72, 1.05) @ R(-90 if s > 0 else 90, "X")
            if x < 0 and s > 0:
                m = m @ R(10, "Y")  # one bent rim
            parts.add(lathe_geo(rim, 14), *STEEL, m)

    return assemble(sc, coll, "ScrapSedan", body, [("DIFFERENCE", cutters)], [parts], location)


# --------------------------------------------------------------------------
# ScrapPickup: burnt-out pickup, stripped of its wheels and up on cinder
# blocks, bonnet open, glass smashed, tailgate thrown in the bed.
# --------------------------------------------------------------------------

def build_pickup(sc, coll, location):
    PAINT = ((0.55, 0.53, 0.47), (0.58, 0.9, 0.3))    # burnt cream paint
    BURNT = ((0.06, 0.055, 0.05), (0.42, 0.95, 0.0))
    METAL = ((0.18, 0.17, 0.16), (0.7, 0.7, 0.1))
    CONCRETE = ((0.46, 0.45, 0.42), (0.0, 0.1, 0.0))
    RUBBER = ((0.03, 0.03, 0.03), (0.0, 0.6, 0.0))
    HUB_Z = 2.06

    body = Part()
    front = body_rings([0.6 + 8.0 * i / 14 for i in range(15)],
                       [(0.6, 1.95), (8.0, 1.95), (8.6, 2.3)],
                       [(0.6, 4.15), (4.5, 4.15), (5.0, 4.0), (8.1, 3.85), (8.6, 3.45)],
                       [(0.6, 6.8), (8.1, 6.8), (8.6, 6.4)],
                       [(0.6, 0.95), (4.5, 0.95), (5.0, 0.98), (8.6, 0.98)])
    bed = body_rings([-8.6 + 9.0 * i / 14 for i in range(15)],
                     [(-8.6, 1.95), (0.4, 1.95)],
                     [(-8.6, 4.35), (0.4, 4.35)],
                     [(-8.6, 6.7), (-8.3, 6.8), (0.4, 6.8)],
                     [(-8.6, 0.99), (0.4, 0.99)], rt=0.3)
    body.add(loft_geo(front), *PAINT)
    body.add(loft_geo(bed), *PAINT)
    body.fix_normals()
    for v in body.bm.verts:
        v.co += v.normal * (noise.noise(v.co * 0.5 + Vector((7, 3, 1))) * 0.09)
    dent(body.bm.verts, (8.4, 3.4, 3.4), 1.8, (-0.4, -0.3, -0.2))     # front fender
    dent(body.bm.verts, (-2.5, -3.4, 3.3), 1.6, (0, 0.32, -0.1))      # bed side
    dent(body.bm.verts, (-6.5, 3.3, 4.35), 1.2, (0, 0, -0.3))         # bed rail
    body.fix_normals()
    body.paint([f for f in body.bm.faces if f.normal.z < -0.6], *UNDER)

    def cut(geo, colour, m=None):
        p = Part()
        p.add(geo, *colour, m)
        return p

    cutters = [
        cut(box_geo(0.95, 4.3, -2.88, 2.88, 2.35, 6.0), BURNT),        # cab
        cut(box_geo(4.75, 8.05, -2.85, 2.85, 2.45, 6.0), BURNT),       # engine bay
        cut(box_geo(-9.2, 0.1, -2.95, 2.95, 2.75, 6.0), PAINT),        # bed, tailgate gone
        cut(box_geo(8.0, 9.0, -1.8, 1.8, 2.55, 3.3), DARK),            # grille, through
        cut(box_geo(8.2, 9.0, 2.2, 3.0, 2.75, 3.25), LAMP),            # headlights
        cut(box_geo(8.2, 9.0, -3.0, -2.2, 2.75, 3.25), LAMP),
        cut(box_geo(-9.0, -8.35, 3.07, 3.33, 3.0, 3.9), RED),          # tail lights
        cut(box_geo(-9.0, -8.35, -3.33, -3.07, 3.0, 3.9), RED),
    ]
    for x in (1.0, 4.4):                                               # door gaps
        cutters.append(cut(box_geo(x - 0.04, x + 0.04, -3.8, -3.15, 2.1, 4.1), DARK))
        cutters.append(cut(box_geo(x - 0.04, x + 0.04, 3.15, 3.8, 2.1, 4.1), DARK))

    tubs = [cut(box_geo(-6.85, -3.15, 1.95, 3.2, 2.7, 4.0), PAINT),
            cut(box_geo(-6.85, -3.15, -3.2, -1.95, 2.7, 4.0), PAINT),
            cut(box_geo(4.15, 8.0, 2.1, 3.2, 2.4, 4.0), BURNT),
            cut(box_geo(4.15, 8.0, -3.2, -2.1, 2.4, 4.0), BURNT)]
    wells = []
    for x in (-5.0, 6.1):
        for y_in, y_out in ((1.85, 4.5), (-4.5, -1.85)):
            p = Part()
            wheel_well(p, x, HUB_Z, 1.75, y_in, y_out, UNDER)
            wells.append(p)

    parts = Part()

    # chassis, axles, brake drums
    for s in (-1, 1):
        y0, y1 = sorted((s * 1.75, s * 2.25))
        parts.add(box_geo(-8.2, 8.3, y0, y1, 1.5, 1.96), *METAL)
    for x in (-5.0, 6.1):
        parts.add(cyl_geo(0.22, -2.5, 2.5, 8), *METAL, T(x, 0, HUB_Z) @ R(-90, "X"))
        for s in (-1, 1):
            y0, y1 = sorted((s * 2.4, s * 2.9))
            parts.add(cyl_geo(0.62, y0, y1, 12), *STEEL, T(x, 0, HUB_Z) @ R(-90, "X"))
            parts.add(cyl_geo(0.2, *sorted((s * 2.9, s * 3.05)), 8), *STEEL,
                      T(x, 0, HUB_Z) @ R(-90, "X"))

    # engine, radiator
    parts.add(box_geo(5.2, 7.3, -1.25, 1.25, 2.2, 3.75), *METAL)
    parts.add(box_geo(5.4, 7.1, -0.85, 0.85, 3.75, 4.05), *METAL)
    parts.add(cyl_geo(0.7, 4.05, 4.4, 12), *METAL, T(6.2, 0, 0))
    parts.add(box_geo(7.72, 7.94, -2.5, 2.5, 2.45, 3.9), *DARK)

    # bonnet propped open, hinged at the cowl
    vs, _ = parts.add(box_geo(0, 3.55, -3.25, 3.25, 0, 0.16, 6, 6), *BURNT)
    for v in vs:
        v.co.z += 0.18 * (1 - (v.co.y / 3.25) ** 2)
        v.co += dent_offset(v.co, (2.6, -1.2, 0.2), 1.3, (0, 0, -0.25))
    hood_m = T(4.65, 0, 4.0) @ R(-62, "Y")
    for v in vs:
        v.co = hood_m @ v.co

    # cab greenhouse
    rz0 = 6.0

    def roof_dz(x, y):
        return (-0.15 * (y / 2.95) ** 2
                + dent_offset((x, y, 0), (2.2, -1.0, 0), 1.6, (0, 0, -0.3)).z)

    vs, _ = parts.add(box_geo(0.82, 3.15, -2.95, 2.95, rz0, rz0 + 0.18, 6, 6), *BURNT)
    for v in vs:
        v.co.z += roof_dz(v.co.x, v.co.y)

    def roof_pt(x, y):
        return (x, y, rz0 + roof_dz(x, y) + 0.08)

    for s in (-1, 1):
        parts.add(beam_geo((4.45, s * 3.12, 3.95), roof_pt(3.05, s * 2.85), 0.3, 0.22), *BURNT)
        parts.add(beam_geo((0.8, s * 3.12, 3.95), roof_pt(0.95, s * 2.85), 0.34, 0.24), *BURNT)
    # cab back wall with the rear window smashed out
    parts.add(box_geo(0.62, 0.87, -3.1, 3.1, 4.0, 4.55), *BURNT)
    parts.add(box_geo(0.62, 0.87, -3.0, 3.0, 5.75, 6.05), *BURNT)
    for s in (-1, 1):
        y0, y1 = sorted((s * 2.1, s * 3.05))
        parts.add(box_geo(0.62, 0.87, y0, y1, 4.5, 5.8), *BURNT)

    # glass shards left in the frames
    ws0, ws1 = Vector((4.4, 0, 4.1)), Vector((3.1, 0, 5.95))

    def ws(y, f):
        p = ws0 + (ws1 - ws0) * f
        return (p.x, y, p.z)

    shards = [
        [ws(-2.7, 0), ws(-1.6, 0), ws(-2.3, 0.35)],
        [ws(-1.2, 0), ws(0.2, 0), ws(-0.6, 0.22)],
        [ws(0.9, 0), ws(2.6, 0), ws(2.2, 0.42), ws(1.5, 0.15)],
        [ws(-0.4, 1), ws(1.0, 1), ws(0.5, 0.7)],
    ]
    for tri in shards:
        parts.add(prism_geo(tri, 0.05), *GLASS)
    for s in (-1, 1):
        y = s * 3.05
        parts.add(prism_geo([(4.2, y, 4.1), (2.6, y, 4.1), (3.7, y, 4.75)], 0.05), *GLASS)
        parts.add(prism_geo([(1.1, y, 4.1), (2.0, y, 4.1), (1.2, y, 5.1)], 0.05), *GLASS)

    # burnt interior: seat frame, dash, steering wheel
    parts.add(box_geo(1.35, 2.6, -2.6, 2.6, 2.35, 2.7), *METAL)
    parts.add(box_geo(1.0, 1.25, -2.6, 2.6, 2.7, 4.2), *METAL,
              about((1.1, 0, 2.7), R(-12, "Y")))
    parts.add(box_geo(3.7, 4.3, -3.0, 3.0, 3.4, 4.0), *BURNT)
    axis = Vector((-0.85, 0, 0.5)).normalized()
    wheel_rot = Vector((0, 0, 1)).rotation_difference(axis).to_matrix().to_4x4()
    parts.add(torus_geo(0.65, 0.07, 12, 4), *METAL, T(3.3, 1.45, 4.25) @ wheel_rot)
    parts.add(beam_geo((3.95, 1.45, 3.85), (3.3, 1.45, 4.25), 0.14, 0.14), *METAL)

    # front bumper, bent
    parts.add(box_geo(8.55, 8.95, -3.35, 3.35, 2.15, 2.75), *CHROME,
              about((8.75, 0, 2.45), R(4, "Z")))

    # tailgate and a burnt tyre thrown in the bed
    parts.add(box_geo(-7.8, -1.6, -1.5, 0.3, 2.75, 2.97), *PAINT,
              about((-4.7, -0.6, 2.75), R(6, "Z")))
    parts.add(torus_geo(1.0, 0.35, 16, 8), *RUBBER, T(-2.0, 1.75, 2.97 + 0.35))

    blocks = Part()
    block_cores = []
    for x in (-5.0, 6.1):
        for s in (-1, 1):
            yc = s * 2.65
            blocks.add(box_geo(x - 0.73, x + 0.73, yc - 0.37, yc + 0.37, 0.0, 0.73), *CONCRETE)
            blocks.add(box_geo(x - 0.37, x + 0.37, yc - 0.73, yc + 0.73, 0.73, 1.46), *CONCRETE)
            for dx in (-0.33, 0.33):   # cores of the lower block run across (along Y)
                block_cores.append(cut(box_geo(x + dx - 0.22, x + dx + 0.22, yc - 0.6, yc + 0.6,
                                               0.15, 0.58), DARK))
            for dy in (-0.33, 0.33):   # upper block turned 90 degrees
                block_cores.append(cut(box_geo(x - 0.6, x + 0.6, yc + dy - 0.22, yc + dy + 0.22,
                                               0.88, 1.31), DARK))
    blocks_ob = blocks.to_object("ScrapPickup_blocks_tmp", coll)
    ccoll = make_cutters(sc, "ScrapPickup_cores", block_cores)
    apply_boolean(sc, blocks_ob, ccoll, "DIFFERENCE")
    drop_collection(ccoll)
    blocks_part = Part()
    blocks_part.bm.free()
    blocks_part.bm = bmesh.new()
    blocks_part.bm.from_mesh(blocks_ob.data)
    me = blocks_ob.data
    bpy.data.objects.remove(blocks_ob)
    bpy.data.meshes.remove(me)

    return assemble(sc, coll, "ScrapPickup", body,
                    [("DIFFERENCE", cutters), ("UNION", tubs), ("DIFFERENCE", wells)],
                    [parts, blocks_part], location)


def main():
    sc = get_scene()
    coll = fresh_collection(sc, "ScrapyardCars_Models")
    sedan = build_sedan(sc, coll, (0, -6.0, 0))
    pickup = build_pickup(sc, coll, (0, 6.5, 0))
    for ob in (sedan, pickup):
        d = ob.dimensions
        print(f"{ob.name}: {tri_count(ob)} tris, size {d.x:.2f} x {d.y:.2f} x {d.z:.2f} studs")


main()
