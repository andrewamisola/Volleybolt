"""Build the MODULAR PICKLE WIZARD (base + cosmetic parts) in Blender and export it as GLBs.

Contract: docs/superpowers/specs/2026-10-01-modular-pickle-design.md section 1.

Run from the repo root:
    "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" -b --factory-startup ^
        --python tools/blender/build_pickle.py

Writes
    models/pickle2/pickle_base.glb            armature PickleRig + mesh pickle_body (M_skin, M_face) + 8 animations
    models/pickle2/parts/hat_wizard.glb       mesh skinned to the same PickleRig (rigid, 100 % sock_hat)
    models/pickle2/parts/outfit_robe.glb      cloak/tunic weighted to body/leg bones
    models/pickle2/parts/staff_classic.glb    wooden staff (rigid, 100 % sock_staff), gem = M_team
    models/pickle2/pickle.blend               everything in one file (for the Lab / debugging)

Conventions (same as build_props*.py / build_gatehouse.py): Blender +Z up, glTF export_yup, the character faces
Blender -Y (so its RIGHT hand is at -X, its LEFT hand at +X), origin on the ground between the feet, materials
looked up BY NAME in the game (M_skin M_face M_hat M_robe M_wood M_team), Closest-filtered packed pixel images.

The body is ONE tall bumpy cucumber (head + body); a roughly square face patch (material M_face, UVs 0..1 over
the patch) sits on the upper third at the front, centred z ~ 1.25. Textures are PIXEL-FIRST: small procedural
images with a handful of palette colours, generated per pixel (no gradients).

Animations are keyed procedurally (one Action per clip, 30 fps, every deforming bone keyed on every frame so no
bone is left holding the previous clip's pose), pushed to NLA tracks named exactly like the clips, and exported
as separate glTF animations. Loop clips end on their own first frame.
"""
import bpy, math, os, random, sys
from mathutils import Vector, Quaternion, Euler, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT_DIR = os.path.join(ROOT, 'models', 'pickle2')
PARTS_DIR = os.path.join(OUT_DIR, 'parts')
TAU = math.tau
FPS = 30


# ------------------------------------------------------------------ palette (sRGB 0..255; pixels are written as-is)
def hx(s):
    s = s.lstrip('#')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def lin(hexstr):
    out = []
    for c in hx(hexstr):
        c /= 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], 1.0)


SKIN_BASE = '#5b8c35'       # also M_face base colour (the game paints skin colour + eyes/mouth on top)
SKIN_DARK = '#3d6b2a'
SKIN_SHADE = '#2f5624'
SKIN_MID = '#6a9d3e'
SKIN_WART = '#a8c967'

# ------------------------------------------------------------------ pixel images
def pixel_image(name, w, h, fn):
    img = bpy.data.images.new(name, w, h)
    px = []
    for y in range(h):                       # Blender rows run bottom -> top; fn gets y from the TOP like a canvas
        for x in range(w):
            r, g, b = fn(x, h - 1 - y)
            px += [r / 255.0, g / 255.0, b / 255.0, 1.0]
    img.pixels = px
    img.pack()
    img.colorspace_settings.name = 'sRGB'
    return img


def hash2(x, y, seed):
    n = (x * 374761393 + y * 668265263 + seed * 2147483647) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def skin_pixels():
    """64x64 cucumber skin, tiles horizontally (u around the body) and vertically. Period-8 lengthwise stripes that
    wander a little, light wart dots with a dark pixel under them, a few mid-tone speckles. Five palette colours."""
    W = H = 64
    c_base, c_dark, c_shade, c_mid, c_wart = map(hx, (SKIN_BASE, SKIN_DARK, SKIN_SHADE, SKIN_MID, SKIN_WART))
    grid = [[c_base] * W for _ in range(H)]
    for y in range(H):
        wob = round(1.6 * math.sin(TAU * y / 32.0) + 0.8 * math.sin(TAU * y / 16.0 + 1.0))
        for x in range(W):
            m = (x + wob) % 8
            if m == 0:
                col = c_dark
            elif m == 1:
                col = c_dark if hash2(x, y, 6) < 0.45 else c_mid
            elif m == 2:
                col = c_mid if hash2(x, y, 3) < 0.55 else c_base
            elif m == 5:
                col = c_mid if hash2(x, y, 4) < 0.30 else c_base
            else:
                col = c_mid if hash2(x, y, 5) < 0.10 else c_base
            grid[y][x] = col
    rng = random.Random(21)
    for _ in range(70):                      # warts: 2x1 light pixels, shade pixel below-right
        x, y = rng.randrange(W), rng.randrange(H)
        grid[y][x] = c_wart
        if rng.random() < 0.6:
            grid[y][(x + 1) % W] = c_wart
        grid[(y + 1) % H][(x + 1) % W] = c_shade
    return lambda x, y: grid[y][x]


def hat_pixels():
    """32x32 floppy-wizard-hat purple with tiny yellow stars (3x3 plus shapes) and a few darker speckles."""
    W = H = 32
    base, dark, light, star = map(hx, ('#5a2d91', '#43206f', '#6e3fae', '#ffd23f'))
    grid = [[base] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            h = hash2(x, y, 7)
            if h < 0.10:
                grid[y][x] = dark
            elif h > 0.94:
                grid[y][x] = light
    for (sx, sy) in ((5, 4), (21, 7), (12, 14), (27, 18), (4, 24), (17, 27), (14, 2)):
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            grid[(sy + dy) % H][(sx + dx) % W] = star
    for (sx, sy) in ((24, 28), (8, 10), (30, 11)):
        grid[sy % H][sx % W] = star          # tiny single-pixel stars
    return lambda x, y: grid[y][x]


def robe_pixels():
    """32x32 deep-indigo cloth: dark vertical fold lines, light stitch dots, two tiny stars."""
    W = H = 32
    base, dark, light, star = map(hx, ('#4e2a8a', '#3a1f68', '#6a46a8', '#ffd23f'))
    grid = [[base] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if x % 8 == 0:
                grid[y][x] = dark
            elif x % 8 == 1 and hash2(x, y, 9) < 0.5:
                grid[y][x] = dark
            elif hash2(x, y, 11) > 0.93:
                grid[y][x] = light
    for (sx, sy) in ((12, 9), (26, 22)):
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            grid[(sy + dy) % H][(sx + dx) % W] = star
    return lambda x, y: grid[y][x]


def wood_pixels():
    """8x16 staff wood: grain runs along v (the staff's length); 4 browns."""
    W, H = 8, 16
    a, b, c, d = map(hx, ('#8a6038', '#6e4a2a', '#53361d', '#a47848'))
    grid = [[a] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if x in (0, 4):
                grid[y][x] = c if hash2(x, y, 2) < 0.8 else b
            elif x in (2, 6):
                grid[y][x] = d if hash2(x, y, 3) < 0.35 else a
            else:
                grid[y][x] = b if hash2(x, y, 4) < 0.35 else a
    grid[5][3] = c; grid[11][6] = c; grid[11][7] = c
    return lambda x, y: grid[y][x]


def witch_pixels():
    """32x32 charcoal felt: speckles + one lighter sewn-on patch with stitch dots."""
    W = H = 32
    base, dark, light, patch, stitch = map(hx, ('#2e2b3a', '#22202c', '#3c384b', '#4a3f5c', '#a8977a'))
    grid = [[base] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            h = hash2(x, y, 13)
            if h < 0.12:
                grid[y][x] = dark
            elif h > 0.95:
                grid[y][x] = light
    for y in range(9, 17):
        for x in range(18, 26):
            edge = y in (9, 16) or x in (18, 25)
            grid[y][x] = stitch if edge and (x + y) % 2 == 0 else patch
    return lambda x, y: grid[y][x]


def gold_pixels():
    """16x16 gold: warm base, dark vertical bands, a bright highlight row."""
    W = H = 16
    base, dark, light = map(hx, ('#e0a82e', '#a8741c', '#ffd86a'))
    grid = [[base] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if x % 4 == 0:
                grid[y][x] = dark
            elif y % 8 == 2 and x % 4 != 3:
                grid[y][x] = light
    return lambda x, y: grid[y][x]


def cape_pixels():
    """32x32 midnight cloth: dark fold lines (long, along v) + a few light flecks."""
    W = H = 32
    base, dark, light = map(hx, ('#2a3452', '#1d243b', '#3a4672'))
    grid = [[base] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if x % 6 == 0 or (x % 6 == 1 and hash2(x, y, 17) < 0.4):
                grid[y][x] = dark
            elif hash2(x, y, 19) > 0.94:
                grid[y][x] = light
    return lambda x, y: grid[y][x]


def knit_pixels():
    """16x16 cream knit: columns of little V stitches, a darker row between courses."""
    W = H = 16
    base, dark = map(hx, ('#e8dcc0', '#bfae88'))
    grid = [[base] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            col, row = x % 4, y % 3
            if (row == 0 and col in (0, 3)) or (row == 1 and col in (1, 2)):     # a V per 4x3 stitch
                grid[y][x] = dark
    return lambda x, y: grid[y][x]


def bark_pixels():
    """8x16 gnarled bark: grey-brown, deep grain lines along v, a knot."""
    W, H = 8, 16
    a, b, c, d = map(hx, ('#6a5440', '#53412f', '#3a2c1f', '#86704f'))
    grid = [[a] * W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            if x in (1, 5) or (x == (y // 3) % W):
                grid[y][x] = c if hash2(x, y, 23) < 0.75 else b
            elif hash2(x, y, 29) < 0.3:
                grid[y][x] = d
            elif hash2(x, y, 31) < 0.35:
                grid[y][x] = b
    for (x, y) in ((3, 6), (4, 6), (3, 7)):
        grid[y][x] = c
    return lambda x, y: grid[y][x]

# ------------------------------------------------------------------ materials
def make_mat(name, color=(1, 1, 1, 1), image=None):
    m = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value = 1.0
    bsdf.inputs['Metallic'].default_value = 0.0
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.0
    if image is not None:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = image
        tex.interpolation = 'Closest'
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = color
    m.diffuse_color = color
    return m


def build_materials():
    return {
        'M_skin': make_mat('M_skin', lin(SKIN_BASE), pixel_image('skin_64', 64, 64, skin_pixels())),
        'M_face': make_mat('M_face', lin(SKIN_BASE)),
        'M_hat': make_mat('M_hat', lin('#5a2d91'), pixel_image('hat_32', 32, 32, hat_pixels())),
        'M_robe': make_mat('M_robe', lin('#4e2a8a'), pixel_image('robe_32', 32, 32, robe_pixels())),
        'M_wood': make_mat('M_wood', lin('#8a6038'), pixel_image('wood_8x16', 8, 16, wood_pixels())),
        'M_team': make_mat('M_team', (1, 1, 1, 1)),
        'M_witch': make_mat('M_witch', lin('#2e2b3a'), pixel_image('witch_32', 32, 32, witch_pixels())),
        'M_gold': make_mat('M_gold', lin('#e0a82e'), pixel_image('gold_16', 16, 16, gold_pixels())),
        'M_cape': make_mat('M_cape', lin('#2a3452'), pixel_image('cape_32', 32, 32, cape_pixels())),
        'M_knit': make_mat('M_knit', lin('#e8dcc0'), pixel_image('knit_16', 16, 16, knit_pixels())),
        'M_bark': make_mat('M_bark', lin('#6a5440'), pixel_image('bark_8x16', 8, 16, bark_pixels())),
        'M_frame': make_mat('M_frame', lin('#2a2230')),
    }


# ------------------------------------------------------------------ rig definition
# name, parent, head, tail   (rest pose, Blender coords; R-side bones at -X, L-side at +X)
def mirror(v, s):
    return (v[0] * s, v[1], v[2])


ARM_S = (0.30, -0.02, 1.05)       # shoulder
ARM_E = (0.385, -0.065, 0.88)     # elbow
ARM_W = (0.405, -0.11, 0.75)      # wrist
HAND_C = (0.41, -0.12, 0.69)      # mitten centre
HAND_T = (0.41, -0.125, 0.62)     # hand bone tail
LEG_X = 0.15

BONES = [
    ('root', None, (0, 0, 0), (0, 0, 0.18)),
    ('hips', 'root', (0, 0, 0.38), (0, 0, 0.55)),
    ('body_lo', 'hips', (0, 0, 0.55), (0, 0, 0.90)),
    ('body_mid', 'body_lo', (0, 0, 0.90), (0, 0, 1.20)),
    ('body_hi', 'body_mid', (0, 0, 1.20), (0, 0, 1.45)),
    ('head', 'body_hi', (0, 0, 1.45), (0, 0, 1.70)),
    ('arm_L_up', 'body_mid', ARM_S, ARM_E),
    ('arm_L_lo', 'arm_L_up', ARM_E, ARM_W),
    ('hand_L', 'arm_L_lo', ARM_W, HAND_T),
    ('arm_R_up', 'body_mid', mirror(ARM_S, -1), mirror(ARM_E, -1)),
    ('arm_R_lo', 'arm_R_up', mirror(ARM_E, -1), mirror(ARM_W, -1)),
    ('hand_R', 'arm_R_lo', mirror(ARM_W, -1), mirror(HAND_T, -1)),
    ('leg_L_up', 'hips', (LEG_X, 0, 0.40), (LEG_X, 0, 0.25)),
    ('leg_L_lo', 'leg_L_up', (LEG_X, 0, 0.25), (LEG_X, 0, 0.12)),
    ('foot_L', 'leg_L_lo', (LEG_X, 0, 0.12), (LEG_X, -0.20, 0.06)),
    ('leg_R_up', 'hips', (-LEG_X, 0, 0.40), (-LEG_X, 0, 0.25)),
    ('leg_R_lo', 'leg_R_up', (-LEG_X, 0, 0.25), (-LEG_X, 0, 0.12)),
    ('foot_R', 'leg_R_lo', (-LEG_X, 0, 0.12), (-LEG_X, -0.20, 0.06)),
    # sockets (no body weights)
    ('sock_hat', 'head', (0, 0, 1.56), (0, 0, 1.66)),
    ('sock_face', 'head', (0, -0.30, 1.25), (0, -0.38, 1.25)),
    ('sock_staff', 'hand_R', mirror(HAND_C, -1), (-HAND_C[0], HAND_C[1], HAND_C[2] + 0.10)),
    ('sock_chest', 'body_mid', (0, -0.33, 0.95), (0, -0.40, 0.95)),
]
DEFORM = [b[0] for b in BONES if not b[0].startswith('sock_')]


def build_armature():
    data = bpy.data.armatures.new('PickleRig')
    obj = bpy.data.objects.new('PickleRig', data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for name, parent, head, tail in BONES:
        eb = data.edit_bones.new(name)
        eb.head = Vector(head)
        eb.tail = Vector(tail)
        eb.use_deform = not name.startswith('sock_')
        if parent:
            eb.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    data.display_type = 'STICK'
    return obj


# ------------------------------------------------------------------ mesh accumulator
class MB:
    def __init__(self):
        self.v, self.w = [], []
        self.f, self.fm, self.fuv, self.fs = [], [], [], []

    def vert(self, co, w):
        tot = sum(w.values())
        self.v.append(Vector(co))
        self.w.append({k: x / tot for k, x in w.items()})
        return len(self.v) - 1

    def face(self, idx, mat, uv=None, smooth=True):
        self.f.append(list(idx))
        self.fm.append(mat)
        self.fuv.append(uv if uv is not None else [(0.0, 0.0)] * len(idx))
        self.fs.append(smooth)

    def tris(self):
        return sum(len(f) - 2 for f in self.f)


def to_object(name, mb, mats, matnames, arm_obj):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in mb.v], [], mb.f)
    for mn in matnames:
        me.materials.append(mats[mn])
    uvl = me.uv_layers.new(name='UVMap')
    for poly, uv, mi, sm in zip(me.polygons, mb.fuv, mb.fm, mb.fs):
        poly.material_index = matnames.index(mi)
        poly.use_smooth = sm
        for li, p in zip(range(poly.loop_start, poly.loop_start + poly.loop_total), uv):
            uvl.data[li].uv = p
    me.validate()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    groups = {}
    for i, w in enumerate(mb.w):
        for bn, x in w.items():
            if x <= 1e-5:
                continue
            if bn not in groups:
                groups[bn] = obj.vertex_groups.new(name=bn)
            groups[bn].add([i], x, 'REPLACE')
    obj.parent = arm_obj
    mod = obj.modifiers.new('PickleRig', 'ARMATURE')
    mod.object = arm_obj
    return obj


# ------------------------------------------------------------------ skinning helpers
BODY_CENTRES = [('hips', 0.40), ('body_lo', 0.72), ('body_mid', 1.05), ('body_hi', 1.32), ('head', 1.57)]


def body_w(z):
    """Linear blend between the two nearest bone centres (smooth bending through the column)."""
    if z <= BODY_CENTRES[0][1]:
        return {BODY_CENTRES[0][0]: 1.0}
    if z >= BODY_CENTRES[-1][1]:
        return {BODY_CENTRES[-1][0]: 1.0}
    for (a, za), (b, zb) in zip(BODY_CENTRES, BODY_CENTRES[1:]):
        if za <= z <= zb:
            t = (z - za) / (zb - za)
            return {a: 1 - t, b: t}


def sstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ primitives
def tube(mb, pts, radii, sides, wfn, mat, uspan=0.25, vscale=1 / 2.2, smooth=True, cap0=True, cap1=True,
         squash=(1.0, 1.0)):
    """Swept tube along a polyline. wfn(i, t, point) -> weights. u = around * uspan, v = arc length * vscale.
    squash = relative width in (normal, binormal) directions."""
    pts = [Vector(p) for p in pts]
    n = len(pts)
    rings = []
    vs = [0.0]
    for i in range(1, n):
        vs.append(vs[-1] + (pts[i] - pts[i - 1]).length * vscale)
    ref = Vector((1, 0, 0))
    tans = []
    for i in range(n):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        tans.append((b - a).normalized())
    for i in range(n):
        T = tans[i]
        r0 = ref if abs(T.dot(ref)) < 0.9 else Vector((0, 1, 0))
        nrm = (r0 - T * T.dot(r0)).normalized()
        bn = T.cross(nrm)
        ring = []
        for k in range(sides):
            a = TAU * k / sides
            co = pts[i] + (nrm * math.cos(a) * squash[0] + bn * math.sin(a) * squash[1]) * radii[i]
            ring.append(mb.vert(co, wfn(i, i / (n - 1), pts[i])))
        rings.append(ring)
    for i in range(n - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            u0, u1 = k / sides * uspan, (k + 1) / sides * uspan
            mb.face([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]], mat,
                    [(u0, vs[i]), (u1, vs[i]), (u1, vs[i + 1]), (u0, vs[i + 1])], smooth)
    if cap0:
        c = mb.vert(pts[0] - tans[0] * radii[0] * 0.6, wfn(0, 0.0, pts[0]))
        for k in range(sides):
            k2 = (k + 1) % sides
            mb.face([c, rings[0][k2], rings[0][k]], mat, [(0, vs[0]), (0, vs[0]), (0, vs[0])], smooth)
    if cap1:
        c = mb.vert(pts[-1] + tans[-1] * radii[-1] * 0.6, wfn(n - 1, 1.0, pts[-1]))
        for k in range(sides):
            k2 = (k + 1) % sides
            mb.face([rings[-1][k], rings[-1][k2], c], mat, [(0, vs[-1]), (0, vs[-1]), (0, vs[-1])], smooth)
    return rings


def ellipsoid(mb, c, radii, lon, lat, wfn, mat, uspan=0.3, smooth=True, flat_bottom_z=None):
    """UV sphere scaled (rx, ry, rz) around c. Poles on +/-Z. lat = number of latitude bands."""
    rx, ry, rz = radii
    cx, cy, cz = c
    top = mb.vert((cx, cy, cz + rz), wfn(Vector((cx, cy, cz + rz))))
    rings = []
    for j in range(1, lat):
        th = math.pi * j / lat
        ring = []
        for k in range(lon):
            a = TAU * k / lon - math.pi / 2          # k = 0 at -Y (front)
            co = Vector((cx + rx * math.sin(th) * math.cos(a), cy + ry * math.sin(th) * math.sin(a),
                         cz + rz * math.cos(th)))
            if flat_bottom_z is not None:
                co.z = max(co.z, flat_bottom_z)
            ring.append(mb.vert(co, wfn(co)))
        rings.append(ring)
    bot = mb.vert((cx, cy, max(cz - rz, flat_bottom_z) if flat_bottom_z is not None else cz - rz),
                  wfn(Vector((cx, cy, cz - rz))))
    for k in range(lon):
        k2 = (k + 1) % lon
        u0, u1 = k / lon * uspan, (k + 1) / lon * uspan
        mb.face([top, rings[0][k2], rings[0][k]], mat, [((u0 + u1) / 2, 0), (u1, 0.1), (u0, 0.1)], smooth)
        mb.face([bot, rings[-1][k], rings[-1][k2]], mat, [((u0 + u1) / 2, 1), (u0, 0.9), (u1, 0.9)], smooth)
        for j in range(len(rings) - 1):
            v0, v1 = (j + 1) / lat * 0.5, (j + 2) / lat * 0.5
            mb.face([rings[j][k], rings[j][k2], rings[j + 1][k2], rings[j + 1][k]], mat,
                    [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], smooth)


# ------------------------------------------------------------------ the body (head + body = one cucumber)
NSEG = 20
BODY_RINGS = [  # z, radius
    (0.20, 0.16), (0.27, 0.27), (0.38, 0.32), (0.52, 0.335), (0.70, 0.345), (0.90, 0.35), (0.975, 0.35),
    (1.10, 0.352), (1.25, 0.347), (1.40, 0.33), (1.525, 0.295), (1.61, 0.235), (1.65, 0.17), (1.68, 0.095)]
BOTTOM_Z, APEX_Z = 0.18, 1.70
PATCH_K0, PATCH_K1 = 7, 12                 # patch vertex columns (5 segments = 90 degrees, centred on the front)
PATCH_Z0, PATCH_Z1 = 0.975, 1.525          # 0.55 tall


def body_radius(z):
    """Piecewise-linear base radius profile (no bumps) -- shared with the robe so it can sit just outside."""
    if z <= BODY_RINGS[0][0]:
        return BODY_RINGS[0][1]
    for (z0, r0), (z1, r1) in zip(BODY_RINGS, BODY_RINGS[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return BODY_RINGS[-1][1]


def ring_angle(k):
    return math.radians(-90 + 18 * (k - 9.5))


def build_body(mb):
    rng = random.Random(5)
    rings = []
    for j, (z, r) in enumerate(BODY_RINGS):
        ring = []
        for k in range(NSEG):
            in_patch = PATCH_K0 <= k <= PATCH_K1 and PATCH_Z0 - 1e-6 <= z <= PATCH_Z1 + 1e-6
            lump = 0.0 if in_patch or j == 0 else (rng.random() - 0.5) * 0.020
            a = ring_angle(k)
            rr = r + lump
            ring.append(mb.vert((rr * math.cos(a), rr * math.sin(a), z), body_w(z)))
        rings.append(ring)
    bot = mb.vert((0, 0, BOTTOM_Z), body_w(BOTTOM_Z))
    apex = mb.vert((0, 0, APEX_Z), body_w(APEX_Z))
    for k in range(NSEG):
        k2 = (k + 1) % NSEG
        u0, u1 = k / NSEG, (k + 1) / NSEG
        mb.face([bot, rings[0][k2], rings[0][k]], 'M_skin',
                [((u0 + u1) / 2, 0.0), (u1, BODY_RINGS[0][0] / 2.2), (u0, BODY_RINGS[0][0] / 2.2)])
        zl = BODY_RINGS[-1][0] / 2.2
        mb.face([rings[-1][k], rings[-1][k2], apex], 'M_skin', [(u0, zl), (u1, zl), ((u0 + u1) / 2, APEX_Z / 2.2)])
    for j in range(len(BODY_RINGS) - 1):
        z0, z1 = BODY_RINGS[j][0], BODY_RINGS[j + 1][0]
        for k in range(NSEG):
            k2 = (k + 1) % NSEG
            quad = [rings[j][k], rings[j][k2], rings[j + 1][k2], rings[j + 1][k]]
            if PATCH_K0 <= k < PATCH_K1 and PATCH_Z0 - 1e-6 <= z0 and z1 <= PATCH_Z1 + 1e-6:
                u0 = (k - PATCH_K0) / (PATCH_K1 - PATCH_K0)
                u1 = (k + 1 - PATCH_K0) / (PATCH_K1 - PATCH_K0)
                v0 = (z0 - PATCH_Z0) / (PATCH_Z1 - PATCH_Z0)
                v1 = (z1 - PATCH_Z0) / (PATCH_Z1 - PATCH_Z0)
                mb.face(quad, 'M_face', [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
            else:
                u0, u1 = k / NSEG, (k + 1) / NSEG
                mb.face(quad, 'M_skin', [(u0, z0 / 2.2), (u1, z0 / 2.2), (u1, z1 / 2.2), (u0, z1 / 2.2)])


def build_limbs(mb):
    for side, s in (('L', 1), ('R', -1)):
        up, lo, hand = f'arm_{side}_up', f'arm_{side}_lo', f'hand_{side}'
        S, E, W = mirror(ARM_S, s), mirror(ARM_E, s), mirror(ARM_W, s)
        Sv, Ev, Wv = Vector(S), Vector(E), Vector(W)
        pts = [Sv, (Sv + Ev) / 2, Ev, (Ev + Wv) / 2, Wv + (Wv - Ev).normalized() * 0.03]
        tw = [0.0, 0.15, 0.5, 0.85, 1.0]
        tube(mb, pts, [0.072, 0.07, 0.066, 0.063, 0.060], 8,
             lambda i, t, p, tw=tw, up=up, lo=lo: {up: 1 - tw[i], lo: tw[i]} if 0 < tw[i] < 1 else ({up: 1} if tw[i] == 0 else {lo: 1}),
             'M_skin', uspan=0.25, cap0=True, cap1=False)
        hc = mirror(HAND_C, s)
        hw = lambda p, hand=hand: {hand: 1.0}
        ellipsoid(mb, hc, (0.078, 0.072, 0.092), 8, 5, hw, 'M_skin', uspan=0.3)
        ellipsoid(mb, (hc[0] - s * 0.045, hc[1] - 0.055, hc[2] + 0.03), (0.036, 0.036, 0.05), 6, 3, hw, 'M_skin',
                  uspan=0.2)
        # leg
        lup, llo, foot = f'leg_{side}_up', f'leg_{side}_lo', f'foot_{side}'
        lx = LEG_X * s
        lz = [0.40, 0.33, 0.25, 0.18, 0.115]
        ltw = [0.0, 0.2, 0.5, 0.85, 1.0]
        tube(mb, [(lx, 0, z) for z in lz], [0.088, 0.085, 0.08, 0.076, 0.074], 8,
             lambda i, t, p, ltw=ltw, lup=lup, llo=llo: {lup: 1 - ltw[i], llo: ltw[i]} if 0 < ltw[i] < 1 else ({lup: 1} if ltw[i] == 0 else {llo: 1}),
             'M_skin', uspan=0.25, cap0=True, cap1=False)
        fw = lambda p, foot=foot: {foot: 1.0}
        ellipsoid(mb, (lx, -0.07, 0.062), (0.118, 0.195, 0.064), 10, 6, fw, 'M_skin', uspan=0.4, flat_bottom_z=0.0)


# ------------------------------------------------------------------ parts
def build_hat(mb):
    W = {'sock_hat': 1.0}
    wf = lambda *a: W
    # spine in rest coords; the hat is tipped a little (back-up, over to the side) around the base centre
    tip = Matrix.Rotation(math.radians(-7), 4, 'X') @ Matrix.Rotation(math.radians(4), 4, 'Y')
    base = Vector((0, 0, 1.585))

    def T(p):
        return base + (tip @ (Vector(p) - base))

    spine = [(0, 0, 1.585), (0, 0.00, 1.76), (0, 0.06, 1.93), (0.02, 0.18, 2.06), (0.07, 0.33, 2.09),
             (0.13, 0.45, 2.01), (0.17, 0.51, 1.92)]
    rad = [0.275, 0.24, 0.19, 0.135, 0.09, 0.05, 0.012]
    sp = [T(p) for p in spine]
    tube(mb, sp, rad, 10, wf, 'M_hat', uspan=1.0, vscale=1 / 1.3, smooth=True, cap0=False, cap1=True)
    # brim: thick disc, slightly drooping at the edge
    N = 12
    rin, rout, zt, zb = 0.235, 0.50, 1.600, 1.575
    top_in, top_out, bot_out, bot_in = [], [], [], []
    for k in range(N):
        a = TAU * k / N
        c, s = math.cos(a), math.sin(a)
        top_in.append(mb.vert(T((rin * c, rin * s, zt)), W))
        top_out.append(mb.vert(T((rout * c, rout * s, zt - 0.045)), W))
        bot_out.append(mb.vert(T((rout * c, rout * s, zb - 0.045)), W))
        bot_in.append(mb.vert(T((rin * c, rin * s, zb)), W))

    def puv(p):                              # planar uv from the brim's plan position, ~2.5 cm per texel
        return (p.x / 0.8 + 0.5, p.y / 0.8 + 0.5)

    for k in range(N):
        k2 = (k + 1) % N
        for quad in ([top_in[k], top_in[k2], top_out[k2], top_out[k]],            # top, faces up
                     [bot_in[k2], bot_in[k], bot_out[k], bot_out[k2]],            # underside, faces down
                     [top_out[k], top_out[k2], bot_out[k2], bot_out[k]]):         # rim, faces out
            mb.face(quad, 'M_hat', [puv(mb.v[i]) for i in quad], smooth=False)
    # team band at the base of the cone
    M = 10
    zb0, zb1, rb = 1.598, 1.665, 0.292
    lo, hi = [], []
    for k in range(M):
        a = TAU * k / M
        lo.append(mb.vert(T((rb * math.cos(a), rb * math.sin(a), zb0)), W))
        hi.append(mb.vert(T((rb * 0.93 * math.cos(a), rb * 0.93 * math.sin(a), zb1)), W))
    for k in range(M):
        k2 = (k + 1) % M
        mb.face([lo[k], lo[k2], hi[k2], hi[k]], 'M_team', smooth=False)
    mb.face(list(reversed(lo)), 'M_team', smooth=False)
    mb.face(hi, 'M_team', smooth=False)


def build_staff(mb):
    W = {'sock_staff': 1.0}
    wf = lambda *a: W
    hx_, hy_ = -HAND_C[0], HAND_C[1]
    zs = [0.06, 0.30, 0.69, 1.10, 1.42]
    tube(mb, [(hx_, hy_, z) for z in zs], [0.026, 0.032, 0.036, 0.036, 0.040], 6, wf, 'M_wood', uspan=1.0,
         vscale=1 / 0.54, smooth=False, cap0=True, cap1=False)
    # wooden crown ring + gem
    tube(mb, [(hx_, hy_, 1.40), (hx_, hy_, 1.45), (hx_, hy_, 1.49)], [0.05, 0.062, 0.04], 6, wf, 'M_wood', uspan=1.0,
         vscale=1 / 0.54, smooth=False, cap0=False, cap1=False)
    gc = Vector((hx_, hy_, 1.585))
    top = mb.vert(gc + Vector((0, 0, 0.12)), W)
    bot = mb.vert(gc - Vector((0, 0, 0.10)), W)
    eq = [mb.vert(gc + Vector((0.085 * math.cos(TAU * k / 6 + 0.3), 0.085 * math.sin(TAU * k / 6 + 0.3), 0)), W)
          for k in range(6)]
    for k in range(6):
        k2 = (k + 1) % 6
        mb.face([top, eq[k2], eq[k]], 'M_team', smooth=False)
        mb.face([bot, eq[k], eq[k2]], 'M_team', smooth=False)
    # lean the whole staff outward ~9 degrees about the grip so the gem clears the hat brim
    pivot = Vector((hx_, hy_, HAND_C[2]))
    rot = Matrix.Rotation(math.radians(-9), 3, 'Y')
    mb.v = [pivot + rot @ (v - pivot) for v in mb.v]


def build_robe(mb):
    NR = 20
    fr = [0.0, 0.10, 0.25, 0.45, 0.65, 0.82, 0.93, 1.0]
    HEM = 0.22

    def top_z(k):
        ang = ring_angle(k)                                     # -90 = front
        back = (1 - math.cos(ang + math.pi / 2)) / 2            # 0 at the front .. 1 at the back
        return 0.92 + 0.30 * back ** 3

    def off(z):
        return 0.035 + 0.10 * max(0.0, (0.68 - z) / 0.46) ** 1.4

    def wts(z, x):
        w = body_w(z)
        wl = 0.55 * max(0.0, min(1.0, (0.40 - z) / 0.22))
        if wl > 0:
            sx = sstep(-0.12, 0.12, x)
            w = {k: v * (1 - wl) for k, v in w.items()}
            w['leg_L_up'] = wl * sx
            w['leg_R_up'] = wl * (1 - sx)
        return w

    rings = []
    for j, f in enumerate(fr):
        ring = []
        for k in range(NR):
            tz = top_z(k)
            z = HEM + (tz - HEM) * f
            r = body_radius(z) + off(z)
            a = ring_angle(k)
            x, y = r * math.cos(a), r * math.sin(a)
            ring.append(mb.vert((x, y, z), wts(z, x)))
        rings.append(ring)
    inner_top, inner_bot = [], []
    for k in range(NR):
        a = ring_angle(k)
        zt = mb.v[rings[-1][k]].z
        r = body_radius(zt) + 0.008
        inner_top.append(mb.vert((r * math.cos(a), r * math.sin(a), zt), wts(zt, r * math.cos(a))))
        zh = HEM
        r = body_radius(zh) + 0.008
        inner_bot.append(mb.vert((r * math.cos(a), r * math.sin(a), zh), wts(zh, r * math.cos(a))))
    for j in range(len(fr) - 1):
        team = j == 0 or j == len(fr) - 2
        for k in range(NR):
            k2 = (k + 1) % NR
            quad = [rings[j][k], rings[j][k2], rings[j + 1][k2], rings[j + 1][k]]
            u0, u1 = 2.0 * k / NR, 2.0 * (k + 1) / NR
            z0, z1 = mb.v[rings[j][k]].z, mb.v[rings[j + 1][k]].z
            if team:
                mb.face(quad, 'M_team', smooth=False)
            else:
                mb.face(quad, 'M_robe', [(u0, z0 / 1.1), (u1, z0 / 1.1), (u1, z1 / 1.1), (u0, z1 / 1.1)])
    for k in range(NR):
        k2 = (k + 1) % NR
        mb.face([rings[-1][k], rings[-1][k2], inner_top[k2], inner_top[k]], 'M_team', smooth=False)   # collar rim (up)
        mb.face([rings[0][k2], rings[0][k], inner_bot[k], inner_bot[k2]], 'M_team', smooth=False)     # hem underside


# ------------------------------------------------------------------ parts, batch 2 (2026-10-01)
def box(mb, c, half, axes, wts, mat):
    """A flat-shaded box: centre c, half sizes (a, b, n) along the three given unit axes."""
    c = Vector(c)
    A, B, N = [Vector(a) for a in axes]
    corners = {}
    for i in (-1, 1):
        for j in (-1, 1):
            for k in (-1, 1):
                corners[(i, j, k)] = mb.vert(c + A * half[0] * i + B * half[1] * j + N * half[2] * k, wts)
    F = [((-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)), ((-1, 1, -1), (1, 1, -1), (1, -1, -1), (-1, -1, -1)),
         ((-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)), ((1, 1, -1), (-1, 1, -1), (-1, 1, 1), (1, 1, 1)),
         ((1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)), ((-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1))]
    for q in F:
        mb.face([corners[x] for x in q], mat, [(0, 0), (1, 0), (1, 1), (0, 1)], smooth=False)


def loop_sweep(mb, centres, frames, section, wfn, mat_fn, uscale=1.0):
    """A CLOSED sweep: at each centre i (with frame (out, up)) place the 2D section points (o, u); join ring to ring
    with wrap-around. mat_fn(i) picks the material of the band starting at ring i."""
    n, S = len(centres), len(section)
    rings = []
    for i, (c, (out, up)) in enumerate(zip(centres, frames)):
        rings.append([mb.vert(c + out * o + up * u, wfn(i, c)) for (o, u) in section])
    for i in range(n):
        i2 = (i + 1) % n
        for k in range(S):
            k2 = (k + 1) % S
            mb.face([rings[i][k], rings[i][k2], rings[i2][k2], rings[i2][k]], mat_fn(i),
                    [(i / n * uscale, k / S), (i / n * uscale, (k + 1) / S), ((i + 1) / n * uscale, (k + 1) / S),
                     ((i + 1) / n * uscale, k / S)], True)


def build_hat_witch(mb):
    W = {'sock_hat': 1.0}
    wf = lambda *a: W
    tip = Matrix.Rotation(math.radians(-5), 4, 'X') @ Matrix.Rotation(math.radians(-6), 4, 'Y')
    base = Vector((0, 0, 1.585))

    def T(p):
        return base + (tip @ (Vector(p) - base))

    # tall straight cone, then a crooked bend at the top
    spine = [(0, 0, 1.585), (0, 0, 1.80), (0, 0.01, 2.02), (0, 0.03, 2.20), (0.02, 0.12, 2.30), (0.05, 0.25, 2.30),
             (0.08, 0.33, 2.22)]
    rad = [0.265, 0.205, 0.145, 0.095, 0.06, 0.035, 0.008]
    tube(mb, [T(p) for p in spine], rad, 10, wf, 'M_witch', uspan=1.0, vscale=1 / 1.3, smooth=True, cap0=False,
         cap1=True)
    # wide brim with a gentle wave
    N = 14
    rin, rout, zt, zb = 0.235, 0.60, 1.600, 1.578
    top_in, top_out, bot_out, bot_in = [], [], [], []
    for k in range(N):
        a = TAU * k / N
        c, s_ = math.cos(a), math.sin(a)
        wave = 0.025 * math.sin(3 * a + 0.6)
        top_in.append(mb.vert(T((rin * c, rin * s_, zt)), W))
        top_out.append(mb.vert(T((rout * c, rout * s_, zt - 0.03 + wave)), W))
        bot_out.append(mb.vert(T((rout * c, rout * s_, zb - 0.03 + wave)), W))
        bot_in.append(mb.vert(T((rin * c, rin * s_, zb)), W))

    def puv(p):
        return (p.x / 0.8 + 0.5, p.y / 0.8 + 0.5)

    for k in range(N):
        k2 = (k + 1) % N
        for quad in ([top_in[k], top_in[k2], top_out[k2], top_out[k]],
                     [bot_in[k2], bot_in[k], bot_out[k], bot_out[k2]],
                     [top_out[k], top_out[k2], bot_out[k2], bot_out[k]]):
            mb.face(quad, 'M_witch', [puv(mb.v[i]) for i in quad], smooth=False)
    # team band + a gold buckle on the front
    M = 10
    zb0, zb1, rb = 1.598, 1.675, 0.283
    lo, hi = [], []
    for k in range(M):
        a = TAU * k / M
        lo.append(mb.vert(T((rb * math.cos(a), rb * math.sin(a), zb0)), W))
        hi.append(mb.vert(T((rb * 0.92 * math.cos(a), rb * 0.92 * math.sin(a), zb1)), W))
    for k in range(M):
        k2 = (k + 1) % M
        mb.face([lo[k], lo[k2], hi[k2], hi[k]], 'M_team', smooth=False)
    mb.face(list(reversed(lo)), 'M_team', smooth=False)
    mb.face(hi, 'M_team', smooth=False)
    bc = T((0, -rb * 0.97, (zb0 + zb1) / 2))
    fwd = (tip.to_3x3() @ Vector((0, -1, 0))).normalized()
    up = (tip.to_3x3() @ Vector((0, 0, 1))).normalized()
    side = up.cross(fwd).normalized()
    for (dx, dz, hw, hh) in ((0, 0.031, 0.05, 0.007), (0, -0.031, 0.05, 0.007), (0.045, 0, 0.007, 0.038),
                             (-0.045, 0, 0.007, 0.038)):
        box(mb, bc + side * dx + up * dz, (hw, hh, 0.01), (side, up, fwd), W, 'M_gold')


def build_crown(mb):
    W = {'sock_hat': 1.0}
    tip = Matrix.Rotation(math.radians(9), 4, 'Y') @ Matrix.Rotation(math.radians(-4), 4, 'X')
    base = Vector((0, 0, 1.55))

    def T(p):
        return base + (tip @ (Vector(p) - base))

    N = 15
    z0, z1, r0, r1, th = 1.535, 1.625, 0.292, 0.305, 0.022
    ob, ot, it, ib = [], [], [], []
    for k in range(N):
        a = TAU * k / N - math.pi / 2              # k = 0 at the front (-Y)
        c, s_ = math.cos(a), math.sin(a)
        ob.append(mb.vert(T((r0 * c, r0 * s_, z0)), W))
        ot.append(mb.vert(T((r1 * c, r1 * s_, z1)), W))
        it.append(mb.vert(T(((r1 - th) * c, (r1 - th) * s_, z1)), W))
        ib.append(mb.vert(T(((r0 - th) * c, (r0 - th) * s_, z0)), W))
    for k in range(N):
        k2 = (k + 1) % N
        u0, u1 = k / N * 3, (k + 1) / N * 3
        mb.face([ob[k], ob[k2], ot[k2], ot[k]], 'M_gold', [(u0, 0), (u1, 0), (u1, 0.5), (u0, 0.5)], smooth=False)
        mb.face([it[k], it[k2], ib[k2], ib[k]], 'M_gold', [(u0, 0.5), (u1, 0.5), (u1, 1), (u0, 1)], smooth=False)
        mb.face([ot[k], ot[k2], it[k2], it[k]], 'M_gold', [(u0, 0.9), (u1, 0.9), (u1, 1), (u0, 1)], smooth=False)
        mb.face([ib[k], ib[k2], ob[k2], ob[k]], 'M_gold', [(u0, 0.9), (u1, 0.9), (u1, 1), (u0, 1)], smooth=False)
    # five points, one every third band segment, each with a team gem below it on the band
    for p in range(5):
        k = p * 3
        a0, a1 = TAU * (k - 1) / N - math.pi / 2, TAU * (k + 1) / N - math.pi / 2
        am = TAU * k / N - math.pi / 2
        o0 = mb.vert(T((r1 * math.cos(a0), r1 * math.sin(a0), z1 - 0.005)), W)
        o1 = mb.vert(T((r1 * math.cos(a1), r1 * math.sin(a1), z1 - 0.005)), W)
        i0 = mb.vert(T(((r1 - th) * math.cos(a0), (r1 - th) * math.sin(a0), z1 - 0.005)), W)
        i1 = mb.vert(T(((r1 - th) * math.cos(a1), (r1 - th) * math.sin(a1), z1 - 0.005)), W)
        pk = mb.vert(T(((r1 + 0.012) * math.cos(am), (r1 + 0.012) * math.sin(am), z1 + 0.13)), W)
        for tri in ((o0, o1, pk), (i1, i0, pk), (i0, o0, pk), (o1, i1, pk)):
            mb.face(list(tri), 'M_gold', [(0.1, 0.1), (0.4, 0.1), (0.25, 0.6)], smooth=False)
        ellipsoid(mb, T(((r1 + 0.012) * math.cos(am), (r1 + 0.012) * math.sin(am), z1 + 0.14)), (0.02, 0.02, 0.02), 6,
                  3, lambda q: W, 'M_gold', smooth=False)
        gc = Vector(T(((r0 + 0.012) * math.cos(am), (r0 + 0.012) * math.sin(am), (z0 + z1) / 2)))
        ellipsoid(mb, gc, (0.026, 0.026, 0.03), 4, 2, lambda q: W, 'M_team', smooth=False)


def build_cape(mb):
    """A short cape hanging behind the arms: outer cloth, team-coloured lining, a team collar band across the back,
    gold clasp studs at the shoulders."""
    fr = [0.0, 0.18, 0.38, 0.58, 0.78, 1.0]               # 0 = top, 1 = hem
    NC = 12
    ZT, ZH = 1.29, 0.40

    def ang(c, f):                                         # +90 degrees = straight back (+Y)
        span = 72 + 22 * f                                 # wraps a little wider at the hem
        return math.radians(90 + span * (2 * c / NC - 1))

    def pos(c, f, inset=0.0):
        e = abs(2 * c / NC - 1)                            # 0 = centre back .. 1 = the side edges
        zt = ZT - 0.17 * e ** 1.5                          # drapes from high on the back, lower at the shoulders
        zh = ZH + 0.24 * e ** 1.5                          # hem longest at the centre back, curving up the sides
        z = zt + (zh - zt) * f
        r = body_radius(z) + 0.045 + 0.065 * f ** 1.4 - inset
        a = ang(c, f)
        return Vector((r * math.cos(a), r * math.sin(a), z))

    outer = [[mb.vert(pos(c, f), body_w(pos(c, f).z)) for c in range(NC + 1)] for f in fr]
    inner = [[mb.vert(pos(c, f, 0.016), body_w(pos(c, f).z)) for c in range(NC + 1)] for f in fr]
    for j in range(len(fr) - 1):
        for c in range(NC):
            uv = [(c / NC * 1.5, fr[j]), ((c + 1) / NC * 1.5, fr[j]), ((c + 1) / NC * 1.5, fr[j + 1]),
                  (c / NC * 1.5, fr[j + 1])]
            mb.face([outer[j][c], outer[j][c + 1], outer[j + 1][c + 1], outer[j + 1][c]][::-1], 'M_cape', uv[::-1])
            mb.face([inner[j][c], inner[j][c + 1], inner[j + 1][c + 1], inner[j + 1][c]], 'M_team', smooth=True)
    for j in range(len(fr) - 1):                           # side edges
        for c, flip in ((0, False), (NC, True)):
            q = [outer[j][c], outer[j + 1][c], inner[j + 1][c], inner[j][c]]
            mb.face(q[::-1] if flip else q, 'M_team', smooth=False)
    last = len(fr) - 1
    for c in range(NC):                                    # hem + top edges
        mb.face([outer[last][c], outer[last][c + 1], inner[last][c + 1], inner[last][c]][::-1], 'M_team', smooth=False)
        mb.face([outer[0][c], outer[0][c + 1], inner[0][c + 1], inner[0][c]], 'M_team', smooth=False)
    # collar band along the top edge
    cent, frames = [], []
    for c in range(NC + 1):
        p = pos(c, 0.0)
        out = Vector((p.x, p.y, 0)).normalized()
        cent.append(p + Vector((0, 0, 0.012)))
        frames.append((out, Vector((0, 0, 1))))
    sec = [(0.0, -0.022), (0.025, 0.0), (0.0, 0.026), (-0.012, 0.0)]
    rings = [[mb.vert(cc + o * a + u * b, body_w(cc.z)) for (a, b) in sec] for cc, (o, u) in zip(cent, frames)]
    for i in range(NC):
        for k in range(4):
            k2 = (k + 1) % 4
            mb.face([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]], 'M_team', smooth=False)
    for c in (0, NC):                                      # gold studs where it clasps at the shoulders
        p = pos(c, 0.0) + Vector((0, 0, 0.005))
        out = Vector((p.x, p.y, 0)).normalized()
        ellipsoid(mb, p + out * 0.03, (0.03, 0.03, 0.03), 6, 3, lambda q, z=p.z: body_w(z), 'M_gold', smooth=False)


def build_scarf(mb):
    """A chunky knit scarf around the neck (front low, clear of the mouth; back a bit higher), team stripes, one
    tail hanging down the front, a knot where it ties."""
    NA = 24
    sec = [(-0.030, -0.040), (0.004, -0.050), (0.034, -0.022), (0.036, 0.022), (0.004, 0.050), (-0.030, 0.040)]
    cent, frames = [], []
    for i in range(NA):
        a = TAU * i / NA - math.pi / 2                    # i = 0 at the front
        back = (1 - math.cos(a + math.pi / 2)) / 2
        z = 0.985 + 0.06 * back
        r = body_radius(z) + 0.042
        cent.append(Vector((r * math.cos(a), r * math.sin(a), z)))
        frames.append((Vector((math.cos(a), math.sin(a), 0)), Vector((0, 0, 1))))
    loop_sweep(mb, cent, frames, sec, lambda i, c: body_w(c.z),
               lambda i: 'M_team' if i % 6 in (2, 3) else 'M_knit', uscale=4.0)
    # the knot + the tail, on the wearer's left-front
    a = math.radians(-58)
    kz = 0.975
    kr = body_radius(kz) + 0.075
    kc = Vector((kr * math.cos(a), kr * math.sin(a), kz))
    wk = body_w(kz)
    ellipsoid(mb, kc, (0.05, 0.045, 0.048), 8, 4, lambda q: wk, 'M_knit', smooth=True)
    pts, rads = [], []
    for t, z in enumerate((0.95, 0.86, 0.76, 0.66, 0.60)):
        rr = body_radius(z) + 0.07 + 0.012 * t
        aa = a + math.radians(4 * t)
        pts.append(Vector((rr * math.cos(aa), rr * math.sin(aa), z)))
        rads.append(0.05)
    tube(mb, pts, rads, 4, lambda i, t, p: wk, 'M_knit', uspan=1.0, vscale=1 / 0.3, smooth=False,
         cap0=False, cap1=True, squash=(1.0, 0.3))
    # team fringe band near the end of the tail
    tube(mb, [pts[-2] + (pts[-1] - pts[-2]) * 0.35, pts[-2] + (pts[-1] - pts[-2]) * 0.65], [0.054, 0.054], 4,
         lambda i, t, p: wk, 'M_team', uspan=1.0, smooth=False, cap0=False, cap1=False, squash=(1.0, 0.33))


def build_glasses(mb):
    """Round specs: two rings over the painted eyes (face canvas eye centres = +/-15.5 degrees, z 1.353), a bridge,
    temples running back along the head. Weighted exactly like the face there so they never slide."""
    zc = 1.353
    wts = body_w(zc)
    wf = lambda *a: wts
    R, rt = 0.082, 0.016
    rb = body_radius(zc) + 0.032
    edges = {}
    for side, deg in (('R', -105.5), ('L', -74.5)):
        a = math.radians(deg)
        n = Vector((math.cos(a), math.sin(a), 0))
        u = Vector((-math.sin(a), math.cos(a), 0))
        v = Vector((0, 0, 1))
        C = Vector((rb * math.cos(a), rb * math.sin(a), zc))
        NS, NT = 14, 4
        rings = []
        for i in range(NS):
            t = TAU * i / NS
            d = u * math.cos(t) + v * math.sin(t)
            rings.append([mb.vert(C + d * R + (d * math.cos(TAU * k / NT) + n * math.sin(TAU * k / NT)) * rt, wts)
                          for k in range(NT)])
        for i in range(NS):
            i2 = (i + 1) % NS
            for k in range(NT):
                k2 = (k + 1) % NT
                mb.face([rings[i][k], rings[i][k2], rings[i2][k2], rings[i2][k]], 'M_frame', smooth=False)
        edges[side] = (C, u, n)
    # bridge: inner edge to inner edge, arching a touch up and out over the nose
    (CR, uR, nR), (CL, uL, nL) = edges['R'], edges['L']
    pR, pL = CR + uR * R, CL - uL * R
    mid = (pR + pL) / 2 + Vector((0, -0.012, 0.012))
    tube(mb, [pR, mid, pL], [rt * 0.9] * 3, 4, wf, 'M_frame', smooth=False, cap0=False, cap1=False)
    # temples: from each outer edge back around the head
    for (C, u, n), s in ((edges['R'], -1), (edges['L'], 1)):
        start = C + u * R * s
        a0 = math.atan2(start.y, start.x)
        pts = [start]
        for t in (0.25, 0.55, 1.0):
            aa = a0 + s * math.radians(55) * t
            rr = body_radius(zc) + 0.02
            pts.append(Vector((rr * math.cos(aa), rr * math.sin(aa), zc + 0.01 * t)))
        tube(mb, pts, [rt * 0.85] * 4, 4, wf, 'M_frame', smooth=False, cap0=False, cap1=True)


def build_staff_branch(mb):
    """A crooked branch: wobbling shaft (straight at the grip), two knots, a forked top cradling a team orb."""
    W = {'sock_staff': 1.0}
    wf = lambda *a: W
    hx_, hy_ = -HAND_C[0], HAND_C[1]
    zs = [0.05, 0.22, 0.42, 0.62, 0.69, 0.78, 0.98, 1.18, 1.36, 1.46]
    dx = [0.015, -0.018, 0.012, 0.0, 0.0, 0.0, 0.022, -0.012, 0.016, 0.0]
    dy = [-0.01, 0.012, 0.018, 0.0, 0.0, 0.0, -0.016, 0.01, -0.008, 0.0]
    rr = [0.028, 0.033, 0.035, 0.034, 0.034, 0.034, 0.033, 0.031, 0.030, 0.032]
    shaft = [(hx_ + a, hy_ + b, z) for a, b, z in zip(dx, dy, zs)]
    tube(mb, shaft, rr, 6, wf, 'M_bark', uspan=1.0, vscale=1 / 0.54, smooth=False, cap0=True, cap1=False)
    for (z, ox, oy, s) in ((0.36, 0.03, 0.0, 0.026), (1.07, -0.028, 0.012, 0.024)):
        ellipsoid(mb, (hx_ + ox, hy_ + oy, z), (s, s, s * 1.3), 6, 3, lambda q: W, 'M_bark', smooth=False)
    # the fork
    top = Vector(shaft[-1])
    for side in (1, -1):
        prong = [top, top + Vector((0.05 * side, 0.01, 0.10)), top + Vector((0.075 * side, 0.0, 0.20)),
                 top + Vector((0.045 * side, -0.01, 0.30))]
        tube(mb, prong, [0.03, 0.024, 0.018, 0.008], 5, wf, 'M_bark', uspan=1.0, vscale=1 / 0.54, smooth=False,
             cap0=False, cap1=True)
    ellipsoid(mb, top + Vector((0, 0, 0.17)), (0.062, 0.062, 0.066), 8, 5, lambda q: W, 'M_team', smooth=False)
    pivot = Vector((hx_, hy_, HAND_C[2]))
    rot = Matrix.Rotation(math.radians(-9), 3, 'Y')
    mb.v = [pivot + rot @ (v - pivot) for v in mb.v]

# ------------------------------------------------------------------ animation
def smooth01(a, b, x):
    return sstep(a, b, x)


class Pose:
    def __init__(self):
        self.r = {b: [0.0, 0.0, 0.0] for b in DEFORM}      # euler degrees, rest-frame axes (X right-left, Y depth, Z up)
        self.l = {b: [0.0, 0.0, 0.0] for b in DEFORM}
        self.s = {b: [1.0, 1.0, 1.0] for b in DEFORM}

    def rot(self, b, x=0.0, y=0.0, z=0.0):
        r = self.r[b]
        r[0] += x; r[1] += y; r[2] += z

    def loc(self, b, x=0.0, y=0.0, z=0.0):
        l = self.l[b]
        l[0] += x; l[1] += y; l[2] += z

    def scale(self, b, x=1.0, y=1.0, z=1.0):
        s = self.s[b]
        s[0] *= x; s[1] *= y; s[2] *= z

    def blend(self, other, w):
        out = Pose()
        for b in DEFORM:
            for i in range(3):
                out.r[b][i] = self.r[b][i] * (1 - w) + other.r[b][i] * w
                out.l[b][i] = self.l[b][i] * (1 - w) + other.l[b][i] * w
                out.s[b][i] = self.s[b][i] * (1 - w) + other.s[b][i] * w
        return out


sin, cos, rad = math.sin, math.cos, math.radians


def p_idle(t, T=2.0):
    p = TAU * t / T
    P = Pose()
    P.loc('hips', z=0.012 * (1 - cos(2 * p)) / 2)
    P.rot('body_lo', y=2.5 * sin(p))
    P.rot('body_mid', y=2.0 * sin(p - 0.6))
    P.rot('body_hi', y=2.0 * sin(p - 1.2), x=1.0 * sin(2 * p))
    P.rot('head', y=2.5 * sin(p - 1.8), x=1.5 * sin(2 * p - 1.0))
    P.scale('body_mid', 1 - 0.01 * sin(2 * p + 0.5), 1 + 0.02 * sin(2 * p + 0.5), 1 - 0.01 * sin(2 * p + 0.5))
    P.rot('arm_L_up', y=-(4 + 2 * sin(p - 0.5)), x=2 * sin(2 * p - 1.2))
    P.rot('arm_R_up', y=(4 + 2 * sin(p - 0.5)), x=2 * sin(2 * p - 1.2))
    P.rot('arm_L_lo', x=-3 - 1.5 * sin(2 * p))
    P.rot('arm_R_lo', x=-3 - 1.5 * sin(2 * p))
    return P


def p_walk(t, s, T=0.8):
    """s = +1 -> toward the character's LEFT (+X), -1 -> right."""
    p = TAU * t / T
    P = Pose()
    hop = abs(sin(p))
    P.loc('hips', z=0.055 * hop)
    roll = 5.0 * s * cos(p)
    P.rot('hips', y=s * 3.0)
    P.rot('body_lo', y=s * 5.0 + roll)
    P.rot('body_mid', y=s * 4.0 + roll * 0.6)
    P.rot('body_hi', y=s * 4.0 - roll * 0.3)
    P.rot('head', y=s * 3.0 - roll * 0.8, x=2.0 * sin(2 * p))
    P.scale('body_lo', 1.03, 0.94 + 0.10 * hop, 1.04 - 0.06 * hop)
    # legs: the airborne-first leg alternates; the leader (side s) reaches outward
    first = 'R' if s > 0 else 'L'
    other = 'L' if s > 0 else 'R'
    lift_first = max(0.0, sin(p))
    lift_other = max(0.0, -sin(p))
    for side, lift in ((first, lift_first), (other, lift_other)):
        P.rot(f'leg_{side}_up', x=-22 * lift, y=-s * 12 * lift)
        P.rot(f'leg_{side}_lo', x=30 * lift)
        P.rot(f'foot_{side}', x=-8 * lift)
    # arms: free arm flails with the hop, the staff arm just carries
    P.rot('arm_L_up', y=-(8 + 16 * hop), x=6 * sin(p))
    P.rot('arm_L_lo', x=-8 - 10 * hop)
    P.rot('arm_R_up', y=(8 + 8 * hop), x=-4 * sin(p))
    P.rot('arm_R_lo', x=-6)
    return P


def p_cast(t, T=1.0):
    p = TAU * t / T
    P = Pose()
    P.loc('hips', z=-0.035 + 0.008 * sin(2 * p))
    P.rot('leg_L_up', y=-8)
    P.rot('leg_R_up', y=8)
    P.scale('leg_L_up', 1, 1, 0.85)
    P.scale('leg_R_up', 1, 1, 0.85)
    P.rot('body_lo', x=-4, y=2 * sin(p))
    P.rot('body_mid', x=-6, y=3 * sin(p - 0.5))
    P.rot('body_hi', x=-6, y=4 * sin(p - 1.0))
    P.rot('head', x=-3 + 2 * sin(2 * p), y=3 * sin(p - 1.4))
    P.scale('body_mid', 1 - 0.015 * sin(2 * p), 1 + 0.03 * sin(2 * p), 1 - 0.015 * sin(2 * p))
    P.scale('body_lo', 1.03, 0.96, 1.03)
    # staff arm (R): hand raised forward-up, hand counter-rotated so the staff points forward-up
    P.rot('arm_R_up', x=-60 + 3 * sin(2 * p))
    P.rot('arm_R_lo', x=-25)
    P.rot('hand_R', x=120 + 6 * sin(2 * p - 0.5))
    # free arm (L): casting gesture
    P.rot('arm_L_up', x=-50 + 4 * sin(2 * p + 1.0), y=-15)
    P.rot('arm_L_lo', x=-30)
    P.rot('hand_L', x=-10 + 8 * sin(2 * p))
    return P


def p_release(t, T=0.3):
    u = t / T
    P = p_cast(0.0).blend(p_idle(0.0), sstep(0.15, 1.0, u))
    th = sstep(0.0, 0.3, u) * (1 - sstep(0.35, 1.0, u))
    P.loc('root', y=-0.10 * th)
    P.rot('body_lo', x=16 * th)
    P.rot('body_mid', x=12 * th)
    P.rot('body_hi', x=8 * th)
    P.rot('head', x=-6 * th)
    P.scale('body_mid', 1 - 0.05 * th, 1 + 0.12 * th, 1 - 0.05 * th)
    P.rot('arm_R_up', x=-30 * th)
    P.rot('hand_R', x=45 * th)
    P.rot('arm_L_up', x=-20 * th)
    return P


def p_parry(t, T=8 / 30.0):
    u = t / T
    f = sstep(0.0, 0.3, u) * (1 - sstep(0.62, 1.0, u))
    P = Pose()
    P.loc('hips', z=-0.03 * f)
    P.rot('leg_L_up', y=-9 * f)
    P.rot('leg_R_up', y=9 * f)
    P.rot('body_lo', x=-8 * f)
    P.rot('body_mid', x=-8 * f, y=1.5 * sin(u * math.pi * 6) * f)
    P.rot('body_hi', x=-4 * f)
    P.rot('head', x=10 * f, y=1.5 * sin(u * math.pi * 6 + 1) * f)
    P.scale('body_lo', 1 + 0.04 * f, 1 - 0.10 * f, 1 + 0.04 * f)
    P.rot('arm_R_up', x=-75 * f)
    P.rot('arm_R_lo', x=-30 * f)
    P.rot('hand_R', x=105 * f)
    P.rot('arm_L_up', x=-75 * f, y=25 * f)
    P.rot('arm_L_lo', x=-30 * f)
    return P


def p_victory(t, T=2.0):
    P = Pose()
    crouch = sstep(0.0, 0.22, t) * (1 - sstep(0.22, 0.34, t))
    ju = min(1.0, max(0.0, (t - 0.32) / 0.85))
    air = sin(math.pi * ju) if 0 < ju < 1 else 0.0
    spin = 360.0 * sstep(0.34, 1.12, t)
    land = sin(math.pi * (t - 1.12) / 0.26) if 1.12 <= t <= 1.38 else 0.0
    arms = sstep(0.22, 0.58, t)
    pump = (1 - sstep(1.4, 2.0, t)) * sin((t - 1.4) * TAU * 2.5) if t > 1.4 else 0.0
    P.loc('hips', z=-0.05 * crouch + 0.38 * air - 0.03 * land + 0.025 * abs(pump))
    P.rot('hips', z=spin)
    P.scale('body_lo', 1 + 0.06 * crouch + 0.04 * land, 1 - 0.14 * crouch + 0.10 * air - 0.08 * land,
            1 + 0.06 * crouch + 0.04 * land - 0.03 * air)
    P.rot('body_lo', x=-3 * arms)
    P.rot('body_hi', x=-5 * arms, y=3 * pump)
    P.rot('head', x=-12 * arms + 3 * crouch, y=-4 * pump)
    P.rot('leg_L_up', y=-10 * crouch - 12 * air)
    P.rot('leg_R_up', y=10 * crouch + 12 * air)
    P.rot('leg_L_lo', x=22 * air)
    P.rot('leg_R_lo', x=22 * air)
    P.rot('arm_L_up', y=-150 * arms + 8 * pump, x=-4 * arms)
    P.rot('arm_L_lo', y=-12 * arms)
    P.rot('hand_L', y=10 * arms)
    P.rot('arm_R_up', y=140 * arms + 8 * pump, x=-4 * arms)
    P.rot('arm_R_lo', y=12 * arms)
    P.rot('hand_R', y=-152 * arms)         # counter-rotate: the staff stays upright overhead
    return P


def p_defeat(t, T=1.5):
    P = Pose()
    f = sstep(0.0, 0.14, t) * (1 - sstep(0.14, 0.22, t))                  # little stagger before the fall
    x = max(0.0, min(1.0, (t - 0.14) / 0.62))
    fall = x * x                                                         # accelerating topple
    ang = -90.0 * fall
    if t > 0.76:                                                         # bounce + rock to rest
        d = t - 0.76
        dec = math.exp(-d * 5.0)
        ang += 4.0 * dec * sin(d * TAU * 2.2)
        bounce = 0.07 * dec * abs(sin(d * TAU * 1.6))
    else:
        bounce = 0.0
    P.rot('root', x=ang)
    P.loc('root', z=0.36 * sin(rad(min(90.0, -ang if ang < 0 else 0))) + bounce, y=0.0)
    P.rot('body_lo', x=-6 * f - 4 * fall)
    P.rot('body_mid', x=-4 * f)
    P.rot('head', x=-10 * f + 35 * fall, z=10 * fall)
    P.loc('hips', z=-0.02 * f)
    fl = sin(x * math.pi * 3.0) * (1 - fall)                             # arm flail on the way down
    P.rot('arm_L_up', y=-(25 * fall + 35 * fl) - 15 * f, x=42 * fall)
    P.rot('arm_R_up', y=(25 * fall + 35 * fl) + 15 * f, x=42 * fall)
    P.rot('arm_L_lo', x=-10 * fall)
    P.rot('arm_R_lo', x=-10 * fall)
    P.rot('leg_L_up', y=-18 * fall, x=-10 * fall)
    P.rot('leg_R_up', y=18 * fall, x=-10 * fall)
    P.rot('leg_L_lo', x=12 * fall)
    P.rot('leg_R_lo', x=12 * fall)
    P.rot('foot_L', x=-12 * fall)
    P.rot('foot_R', x=-12 * fall)
    return P


CLIPS = [  # name, frames (inclusive end), pose fn(t_seconds), loop
    ('idle', 60, lambda t: p_idle(t), True),
    ('left', 24, lambda t: p_walk(t, +1), True),
    ('right', 24, lambda t: p_walk(t, -1), True),
    ('cast_loop', 30, lambda t: p_cast(t), True),
    ('cast_release', 9, lambda t: p_release(t), False),
    ('parry', 8, lambda t: p_parry(t), False),
    ('victory', 60, lambda t: p_victory(t), False),
    ('defeat', 45, lambda t: p_defeat(t), False),
]


def rest_rotations(arm_obj):
    out = {}
    for b in arm_obj.data.bones:
        out[b.name] = b.matrix_local.to_3x3()
    return out


def apply_pose(arm_obj, P, rests, prev_q):
    for name in DEFORM:
        pb = arm_obj.pose.bones[name]
        M = rests[name]
        C = M.to_quaternion()
        e = P.r[name]
        R = Euler((rad(e[0]), rad(e[1]), rad(e[2])), 'XYZ').to_quaternion()
        q = C.inverted() @ R @ C
        pq = prev_q.get(name)
        if pq is not None and q.dot(pq) < 0:
            q = -q
        prev_q[name] = q.copy()
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = q
        pb.location = M.inverted() @ Vector(P.l[name])
        sw = P.s[name]
        # world-axis scale -> bone-local axes (bones are axis-aligned, so this is a permutation)
        pb.scale = Vector([sum(abs(M[j][i]) * sw[j] for j in range(3)) / max(1e-6, sum(abs(M[j][i]) for j in range(3)))
                           for i in range(3)])


def key_all(arm_obj, frame):
    for name in DEFORM:
        pb = arm_obj.pose.bones[name]
        pb.keyframe_insert('rotation_quaternion', frame=frame, group=name)
        pb.keyframe_insert('location', frame=frame, group=name)
        pb.keyframe_insert('scale', frame=frame, group=name)


def bake_clips(arm_obj):
    scene = bpy.context.scene
    scene.render.fps = FPS
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    ad = arm_obj.animation_data_create()
    rests = rest_rotations(arm_obj)
    actions = []
    for name, nframes, fn, loop in CLIPS:
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        ad.action = act
        prev = {}
        for f in range(nframes + 1):
            t = f / FPS
            if loop and f == nframes:
                t = 0.0                              # exact loop closure
            apply_pose(arm_obj, fn(t), rests, prev)
            key_all(arm_obj, f)
        actions.append(act)
    ad.action = None
    for act in actions:
        tr = ad.nla_tracks.new()
        tr.name = act.name
        st = tr.strips.new(act.name, 0, act)
        try:
            if act.slots:
                st.action_slot = act.slots[0]
        except Exception as e:
            print('slot assign', e)
    reset_pose(arm_obj)
    return actions


def reset_pose(arm_obj):
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)


# ------------------------------------------------------------------ export
def export(objs, path, animations):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    kw = dict(filepath=path, export_format='GLB', use_selection=True, export_yup=True,
              export_materials='EXPORT', export_image_format='AUTO', export_skins=True, export_def_bones=False,
              export_rest_position_armature=True, export_apply=False, export_cameras=False, export_lights=False,
              export_animations=animations)
    if animations:
        kw.update(export_animation_mode='NLA_TRACKS', export_force_sampling=True, export_frame_step=1,
                  export_optimize_animation_size=False, export_anim_slide_to_zero=False,
                  export_optimize_animation_keep_anim_armature=True, export_nla_strips_merged_animation_name='')
    bpy.ops.export_scene.gltf(**kw)
    print('exported', path, os.path.getsize(path), 'bytes', flush=True)


def main():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    os.makedirs(PARTS_DIR, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    mats = build_materials()
    arm = build_armature()

    mb = MB()
    build_body(mb)
    build_limbs(mb)
    body = to_object('pickle_body', mb, mats, ['M_skin', 'M_face'], arm)
    tris = {'pickle_body': mb.tris()}

    mh = MB(); build_hat(mh)
    hat = to_object('hat_wizard', mh, mats, ['M_hat', 'M_team'], arm); tris['hat_wizard'] = mh.tris()
    mr = MB(); build_robe(mr)
    robe = to_object('outfit_robe', mr, mats, ['M_robe', 'M_team'], arm); tris['outfit_robe'] = mr.tris()
    ms = MB(); build_staff(ms)
    staff = to_object('staff_classic', ms, mats, ['M_wood', 'M_team'], arm); tris['staff_classic'] = ms.tris()
    extra = []
    for name, fn, matnames in (('hat_witch', build_hat_witch, ['M_witch', 'M_team', 'M_gold']),
                               ('hat_crown', build_crown, ['M_gold', 'M_team']),
                               ('outfit_cape', build_cape, ['M_cape', 'M_team', 'M_gold']),
                               ('neck_scarf', build_scarf, ['M_knit', 'M_team']),
                               ('face_glasses', build_glasses, ['M_frame']),
                               ('staff_branch', build_staff_branch, ['M_bark', 'M_team'])):
        m = MB(); fn(m)
        extra.append(to_object(name, m, mats, matnames, arm)); tris[name] = m.tris()
    for k, v in tris.items():
        print(f'{k}: {v} tris', flush=True)
    assert tris['pickle_body'] < 2500

    bake_clips(arm)
    reset_pose(arm)
    arm.animation_data.action = None

    export([arm, body], os.path.join(OUT_DIR, 'pickle_base.glb'), True)
    for obj in [hat, robe, staff] + extra:
        export([arm, obj], os.path.join(PARTS_DIR, obj.name + '.glb'), False)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, 'pickle.blend'), compress=True)


main()
