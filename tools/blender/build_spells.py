"""Build Volleybolt's spell projectile models (PS1 low-poly, vertex-coloured) and export them.

Run from the repo root:
    "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" -b --factory-startup ^
        --python tools/blender/build_spells.py

Writes models/fx/spells.blend + models/fx/spells.glb with two top-level objects:
    fx_fireball   faceted flame comet: bright core + two nested flame shells tapering into tongues
    fx_frostbolt  faceted ice spear with small trailing shards
    fx_iceblock   freeze prison: one big faceted glass gem around the wizard + base shards (M_fx_ice)
Travel direction is Blender +X (the game orients each instance along its velocity). Colour lives
in the COLOR_0 vertex colours (the game renders these unlit); materials:
    M_fx_core   opaque, unlit          (fire core, ice spear)
    M_fx_shell  additive in the game   (the translucent fire shells)
Sizes are in game units at volley tier 1; the game's per-volley scale applies on top.
"""
import bpy, math, random, os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT_DIR = os.path.join(ROOT, 'models', 'fx')
TAU = math.tau


class MB:
    def __init__(self):
        self.v, self.f, self.col, self.mat = [], [], [], []

    def vert(self, co):
        self.v.append(Vector(co))
        return len(self.v) - 1

    def face(self, idx, color, mat):
        self.f.append(list(idx))
        self.col.append(color if isinstance(color[0], (tuple, list)) else [color] * len(idx))
        self.mat.append(mat)


def along_x(m, profile, sides, color_of, mat, jag=None, seed=0, rot=0.0):
    """Revolve (x, radius) rings around the X axis (the travel axis). Radius 0 = a point.
    color_of(x) gives each ring's colour; jag scales the radius of the rings listed in it."""
    rng = random.Random(seed)
    rings = []
    for k, (x, r) in enumerate(profile):
        if r == 0:
            rings.append([m.vert((x, 0, 0))])
            continue
        ring = []
        for i in range(sides):
            a = rot + TAU * i / sides
            rr = r * (1 + (jag.get(k, 0) * (rng.random() - 0.35) if jag else 0))
            ring.append(m.vert((x, rr * math.cos(a), rr * math.sin(a))))
        rings.append(ring)
    for k in range(len(rings) - 1):
        lo, hi = rings[k], rings[k + 1]
        c_lo, c_hi = color_of(profile[k][0]), color_of(profile[k + 1][0])
        for i in range(sides):
            j = (i + 1) % sides
            if len(lo) == 1:
                m.face([lo[0], hi[j], hi[i]], [c_lo, c_hi, c_hi], mat)
            elif len(hi) == 1:
                m.face([lo[i], lo[j], hi[0]], [c_lo, c_lo, c_hi], mat)
            else:
                m.face([lo[i], lo[j], hi[j], hi[i]], [c_lo, c_lo, c_hi, c_hi], mat)


def lerp3(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


# The fireball's collision radius is 0.25 at the game's base mesh scale of 0.85, i.e. 0.294 in model
# units, and both grow together with volley tier. The core is authored to EXACTLY that sphere and
# the flame shells hug it (within ~15%), trailing behind: what players see is what they must block.
HITBOX_R = 0.25 / 0.85


def fireball():
    """Head at +X. The profile runs from the tail (x < 0) to the nose so faces point outward."""
    m = MB()
    white, yellow, orange, red, ember = ((1, 0.97, 0.8), (1, 0.82, 0.3), (1, 0.48, 0.1),
                                         (0.9, 0.2, 0.04), (0.55, 0.08, 0.02))
    # Core: a chunky faceted egg, white-hot.
    R = HITBOX_R
    along_x(m, [(-R, 0), (-0.55 * R, 0.85 * R), (0.1 * R, R), (0.65 * R, 0.7 * R), (R, 0)], 6,
            lambda x: lerp3(yellow, white, (x + R) / (2 * R)), 'M_fx_core', rot=0.3)
    # Inner flame: yellow -> orange, ragged tongues at the tail.
    along_x(m, [(-2.4 * R, 0), (-1.5 * R, 0.5 * R), (-0.6 * R, 0.95 * R), (0.1 * R, 1.08 * R),
                (0.7 * R, 0.8 * R), (1.08 * R, 0)], 7,
            lambda x: lerp3(orange, yellow, (x + 2.4 * R) / (3.3 * R)), 'M_fx_shell',
            jag={1: 1.4, 2: 0.4}, seed=2, rot=0.1)
    # Outer flame: orange -> red -> ember, longer and more ragged.
    along_x(m, [(-3.6 * R, 0), (-2.3 * R, 0.5 * R), (-1.1 * R, 0.95 * R), (0.0, 1.15 * R),
                (0.6 * R, 0.95 * R), (1.14 * R, 0)], 8,
            lambda x: lerp3(ember, orange, (x + 3.6 * R) / (4.2 * R)), 'M_fx_shell',
            jag={1: 1.8, 2: 0.5}, seed=3, rot=0.5)
    return m


def frostbolt():
    m = MB()
    white, ice, deep = (0.95, 1, 1), (0.55, 0.85, 1), (0.2, 0.45, 0.9)
    # Main spear: a long hexagonal bipyramid, white at the point.
    along_x(m, [(-0.42, 0), (-0.1, 0.13), (0.1, 0.13), (0.62, 0)], 6,
            lambda x: lerp3(deep, white, (x + 0.42) / 1.0), 'M_fx_core', rot=0.2)
    # Three trailing shards, splayed back.
    for k in range(3):
        a = TAU * k / 3 + 0.5
        dy, dz = math.cos(a), math.sin(a)
        base = Vector((-0.15, dy * 0.1, dz * 0.1))
        tip = base + Vector((-0.42, dy * 0.18, dz * 0.18))
        side = Vector((0, -dz, dy)) * 0.05
        up = Vector((0, dy, dz)).cross(Vector((1, 0, 0))).normalized() * 0.05
        p = [m.vert(base + Vector((0.12, 0, 0))), m.vert(base + side), m.vert(base + up),
             m.vert(base - side), m.vert(base - up), m.vert(tip)]
        for i in range(4):
            j = 1 + (i + 1) % 4
            m.face([p[0], p[1 + i], p[j]], [white, ice, ice], 'M_fx_core')
            m.face([p[5], p[j], p[1 + i]], [deep, ice, ice], 'M_fx_core')
    return m


def crystal(m, base, axis, height, width, colors, mat, sides=6, rot=0.0):
    """Hexagonal crystal: a prism from `base` along `axis` with a pointed tip."""
    axis = axis.normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    u = axis.cross(ref).normalized()
    v = axis.cross(u).normalized()
    deep, mid, tip = colors
    shaft = height * 0.78
    rings = []
    for k, (h, w) in enumerate(((0.0, width), (shaft, width * 0.92))):
        ring = []
        for i in range(sides):
            a = rot + TAU * i / sides
            ring.append(m.vert(base + axis * h + (u * math.cos(a) + v * math.sin(a)) * w))
        rings.append(ring)
    top = m.vert(base + axis * height)
    lo, hi = rings
    for i in range(sides):
        j = (i + 1) % sides
        m.face([lo[i], lo[j], hi[j], hi[i]], [deep, deep, mid, mid], mat)
        m.face([hi[i], hi[j], top], [mid, mid, tip], mat)
    m.face(lo[::-1], [deep] * sides, mat)


def iceblock():
    """Freeze prison (WoW Ice Block style): ONE big faceted gem of translucent blue glass encasing
    the wizard, plus a few small shards leaning out at the base. The gem is the convex hull of
    jittered points; each facet gets its own brightness so the glass reads as cut crystal.
    Local frame = the game's ice root (y = 1 above the paddle): z -1.05 is the ground, the wizard
    stands inside, the top clears the hat. Blender +Y is the camera side."""
    import bmesh
    m = MB()
    rng = random.Random(11)
    pts = []
    for z, n, r0, r1 in ((-1.05, 6, 0.62, 0.78), (-0.2, 6, 0.8, 0.95), (0.75, 5, 0.66, 0.8),
                         (1.35, 4, 0.3, 0.45)):
        for i in range(n):
            a = TAU * (i + rng.random() * 0.6) / n
            r = r0 + (r1 - r0) * rng.random()
            pts.append(Vector((r * math.cos(a), r * 0.78 * math.sin(a), z + (rng.random() - 0.5) * 0.25)))
    pts.append(Vector((0.12, -0.05, 1.72)))                          # off-centre crown
    bm = bmesh.new()
    verts = [bm.verts.new(p) for p in pts]
    bmesh.ops.convex_hull(bm, input=verts)
    bm.normal_update()
    deep, glass, light = (0.06, 0.22, 0.95), (0.16, 0.4, 1.0), (0.42, 0.66, 1.0)   # saturated glass blue
    for f in bm.faces:
        if len(f.verts) < 3:
            continue
        zc = sum(v.co.z for v in f.verts) / len(f.verts)
        base = lerp3(deep, glass, (zc + 1.05) / 1.6) if zc < 0.55 else lerp3(glass, light, (zc - 0.55) / 1.2)
        k = 0.62 + 0.6 * rng.random()                                  # per-facet glint (cut-glass contrast)
        col = tuple(min(1.0, c * k) for c in base)
        idx = [m.vert(v.co) for v in f.verts]
        m.face(idx, col, 'M_fx_ice')
    bm.free()
    # Small shards at the base, leaning out.
    colors = ((0.2, 0.4, 0.95), (0.45, 0.7, 1.0), (0.8, 0.92, 1.0))
    for ang, h, w, lean in ((200, 0.75, 0.17, 0.7), (-20, 0.6, 0.14, 0.8), (125, 0.5, 0.12, 0.9)):
        a = math.radians(ang)
        out = Vector((math.cos(a), math.sin(a) * 0.8, 0))
        crystal(m, Vector((out.x * 0.8, out.y * 0.8, -1.05)), Vector((0, 0, 1)) + out * lean, h, w,
                colors, 'M_fx_ice', rot=rng.random())
    return m


def make_mat(name):
    mat = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = (1, 1, 1, 1)
    bsdf.inputs['Roughness'].default_value = 1.0
    return mat


def to_object(name, m, mats):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in m.v], [], m.f)
    order = list(mats)
    for key in order:
        me.materials.append(mats[key])
    me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')    # create before touching (see castle)
    cols = []
    for pi, poly in enumerate(me.polygons):
        for j in range(len(poly.loop_indices)):
            c = m.col[pi][j]
            cols += (c[0], c[1], c[2], 1.0)
    me.polygons.foreach_set('material_index', [order.index(k) for k in m.mat])
    me.color_attributes['Col'].data.foreach_set('color', cols)
    me.color_attributes.active_color = me.color_attributes['Col']
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    print(f'{name}: {sum(len(f) - 2 for f in m.f)} tris', flush=True)
    return obj


def main():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    mats = {k: make_mat(k) for k in ('M_fx_core', 'M_fx_shell', 'M_fx_ice')}
    to_object('fx_fireball', fireball(), mats)
    to_object('fx_frostbolt', frostbolt(), mats).location = (0, 0, 0)
    to_object('fx_iceblock', iceblock(), mats)
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, 'spells.blend'), compress=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT_DIR, 'spells.glb'), export_format='GLB',
                              export_vertex_color='ACTIVE', export_apply=True, export_yup=True,
                              export_materials='EXPORT', use_visible=False, export_animations=False)
    print('exported', os.path.join(OUT_DIR, 'spells.glb'), flush=True)


main()
