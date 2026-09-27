"""Build the Ancient Pickle Jar (the enemy CORE relic for the core stage) in Blender and export it.

Run from the repo root:
    "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" -b --factory-startup ^
        --python tools/blender/build_jar.py

Writes models/core/core.blend and models/core/core.glb. Preview every damage state from the game's
camera in core_viewer.html. Concept art: brand/concepts/jar_v1.png, core_v1.png.

Same conventions as tools/blender/build_castle.py (helpers are copied, not imported, because that
script builds on import):
    Blender +X = away from the court, +Y = toward the game camera, +Z = up.
    Origin = the gate line on the lane's centre line; the red side mirrors this GLB in X at runtime.
    The camera is fixed 30 deg above the ground, so detail goes on tops and the +Y side.

Exported scene graph:
    core_s0..core_s3  one joined mesh per damage state: pristine, cracked, leaking, shattered
    core_debris       empty; children are glass shards + the lid, for the shatter beat
Materials (looked up by name in the game): M_stone, M_glass, M_brine_team, M_pickle, M_bronze, M_iron,
M_rune, M_cloth_team, M_wood, M_candle, M_flame, M_crack. The game makes M_glass/M_brine
translucent and M_brine_team/M_rune/M_flame glow; *_team is grey and tinted per side (the
brine is the defending team's colour).
"""
import bpy, math, random, os
from mathutils import Vector, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT_DIR = os.path.join(ROOT, 'models', 'core')
TEX_DIR = os.path.join(ROOT, 'textures')
TILE = 1.6
TAU = math.tau

# ---------------------------------------------------------------- layout (Blender units)
LANE_HALF = 8.0                     # rail centre line (Babylon z = +-7.2 at the game's 0.9 scale)
C = Vector((1.9, 0.5, 0))           # altar + jar centre, behind the gate line, a touch toward camera
ALTAR = [(3.2, 0.0), (3.2, 0.45), (2.7, 0.45), (2.7, 0.9), (2.25, 0.9), (2.25, 1.3)]  # 3 steps
TOP_Z = 1.3
GLASS = [(1.55, TOP_Z), (1.9, 1.5), (2.0, 2.2), (2.0, 5.4), (1.86, 5.9), (1.5, 6.2), (1.5, 6.5)]
LID = [(1.62, 6.38), (1.78, 6.42), (1.78, 6.86), (1.52, 6.96), (1.1, 7.1), (0.36, 7.22),
       (0.3, 7.5), (0.0, 7.78)]
POST_ANGLES = (40, 140, 220, 320)
POST_R = 2.95


# ---------------------------------------------------------------- materials
def load_image(name):
    img = bpy.data.images.load(os.path.join(TEX_DIR, name))
    img.pack()
    return img


def pixel_image(name, w, h, fn):
    img = bpy.data.images.new(name, w, h)
    px = []
    for y in range(h):
        for x in range(w):
            r, g, b = fn(x, y)
            px += [r, g, b, 1.0]
    img.pixels = px
    img.pack()
    return img


_wood_rng = random.Random(11)
_wood_noise = [[_wood_rng.random() for _ in range(32)] for _ in range(32)]


def wood_planks(x, y):
    if y % 8 == 0:
        return (0.16, 0.10, 0.06)
    n = _wood_noise[y][x // 4]
    grain = 0.9 + 0.2 * n
    return (0.46 * grain, 0.30 * grain, 0.17 * grain)


def make_mat(name, image=None, color=(1, 1, 1, 1)):
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
    return m


MAT_ORDER = ['M_stone', 'M_glass', 'M_brine_team', 'M_pickle', 'M_bronze', 'M_iron', 'M_rune',
             'M_cloth_team', 'M_wood', 'M_candle', 'M_flame', 'M_crack']


def build_materials():
    mats = {
        'M_stone': make_mat('M_stone', load_image('tower_stone.png')),
        'M_glass': make_mat('M_glass', color=(0.72, 0.9, 0.78, 1)),
        'M_brine_team': make_mat('M_brine_team', color=(0.85, 0.85, 0.85, 1)),
        'M_pickle': make_mat('M_pickle', color=(0.17, 0.33, 0.06, 1)),
        'M_bronze': make_mat('M_bronze', color=(0.4, 0.25, 0.11, 1)),
        'M_iron': make_mat('M_iron', color=(0.24, 0.23, 0.25, 1)),
        'M_rune': make_mat('M_rune', color=(0.55, 1.0, 0.35, 1)),
        'M_cloth_team': make_mat('M_cloth_team', color=(0.85, 0.85, 0.85, 1)),
        'M_wood': make_mat('M_wood', pixel_image('wood_planks', 32, 32, wood_planks)),
        'M_candle': make_mat('M_candle', color=(0.92, 0.86, 0.7, 1)),
        'M_flame': make_mat('M_flame', color=(1.0, 0.75, 0.35, 1)),
        'M_crack': make_mat('M_crack', color=(0.92, 1.0, 0.96, 1)),
    }
    # Single-sided juice (glTF doubleSided=false): only its far inner wall + surface ever draw.
    mats['M_brine_team'].use_backface_culling = True
    return mats


# ---------------------------------------------------------------- mesh accumulator (from build_castle)
class MB:
    def __init__(self):
        self.v, self.f, self.uv, self.mat, self.smooth, self.tag = [], [], [], [], [], []

    def vert(self, co):
        self.v.append(Vector(co))
        return len(self.v) - 1

    def face(self, idx, uvs, mat, tag, smooth=False):
        self.f.append(list(idx))
        self.uv.append([tuple(u) for u in uvs])
        self.mat.append(MAT_ORDER.index(mat))
        self.tag.append(tag)
        self.smooth.append(smooth)

    def quad_planar(self, idx, mat, tag, smooth=False):
        pts = [self.v[i] for i in idx]
        n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
        ax = max(range(3), key=lambda k: abs(n[k]))
        a, b = [(1, 2), (0, 2), (0, 1)][ax]
        self.face(idx, [(p[a] / TILE, p[b] / TILE) for p in pts], mat, tag, smooth)


def lathe(m, profile, sides, center, mat, tag, rot=0.0, jitter=0.0, seed=0, jag_top=None,
          cap_top=False, smooth=True, flip=False):
    """Revolve (radius, z) rings around `center` (z taken from the profile, plus center.z)."""
    rng = random.Random(seed)
    rings = []
    for k, (r, z) in enumerate(profile):
        ring = []
        for i in range(sides):
            a = rot + TAU * i / sides
            rr = r * (1 + jitter * (rng.random() - 0.5)) if r > 0 else 0
            zz = z + (jag_top[i] if (jag_top and k == len(profile) - 1) else 0)
            p = Vector((center.x + rr * math.cos(a), center.y + rr * math.sin(a), center.z + zz))
            ring.append(m.vert(p))
            if r == 0:
                break
        rings.append(ring)
    for k in range(len(rings) - 1):
        r_avg = max((profile[k][0] + profile[k + 1][0]) / 2, 0.3)
        circ = TAU * r_avg / TILE
        z0, z1 = profile[k][1] / TILE, profile[k + 1][1] / TILE
        lo, hi = rings[k], rings[k + 1]
        for i in range(sides):
            j = (i + 1) % sides
            u0, u1 = circ * i / sides, circ * (i + 1) / sides
            if len(hi) == 1:
                idx, uvs = [lo[i], lo[j], hi[0]], [(u0, z0), (u1, z0), ((u0 + u1) / 2, z1)]
            elif len(lo) == 1:
                idx, uvs = [lo[0], hi[j], hi[i]], [((u0 + u1) / 2, z0), (u1, z1), (u0, z1)]
            else:
                idx, uvs = [lo[i], lo[j], hi[j], hi[i]], [(u0, z0), (u1, z0), (u1, z1), (u0, z1)]
            if flip:                                   # inward-facing (seen from inside)
                idx, uvs = idx[::-1], uvs[::-1]
            m.face(idx, uvs, mat, tag, smooth)
    if cap_top and len(rings[-1]) > 2:
        m.quad_planar(rings[-1], mat, tag)
    return rings


def box(m, center, size, mat, tag, rot_z=0.0, jitter=0.0, seed=0):
    rng = random.Random(seed)
    sx, sy, sz = (s / 2 for s in size)
    cz, sn = math.cos(rot_z), math.sin(rot_z)
    idx = []
    for dz in (-sz, sz):
        for (dx, dy) in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
            p = Vector((dx, dy, dz))
            if jitter:
                p += Vector([(rng.random() - 0.5) * jitter for _ in range(3)])
            idx.append(m.vert(Vector((p.x * cz - p.y * sn, p.x * sn + p.y * cz, p.z)) + Vector(center)))
    b0, b1, b2, b3, t0, t1, t2, t3 = idx
    for f in ([b3, b2, b1, b0], [t0, t1, t2, t3], [b0, b1, t1, t0], [b1, b2, t2, t1],
              [b2, b3, t3, t2], [b3, b0, t0, t3]):
        m.quad_planar(f, mat, tag)
    return idx


def beam(m, p0, p1, t, mat, tag):
    d = (p1 - p0).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    s = d.cross(up).normalized() * (t / 2)
    u = d.cross(s).normalized() * (t / 2)
    ring = lambda p: [m.vert(p + s + u), m.vert(p - s + u), m.vert(p - s - u), m.vert(p + s - u)]
    a, b = ring(p0), ring(p1)
    for i in range(4):
        j = (i + 1) % 4
        m.quad_planar([a[i], a[j], b[j], b[i]], mat, tag)
    m.quad_planar(a[::-1], mat, tag)
    m.quad_planar(b, mat, tag)


def poly(m, pts, mat, tag, facing, smooth=False):
    """Flat polygon from world points, wound so its normal points along `facing`."""
    n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
    if n.dot(facing) < 0:
        pts = pts[::-1]
    idx = [m.vert(p) for p in pts]
    m.quad_planar(idx, mat, tag, smooth)


def xform(m, start, mat3, offset):
    """Rotate + move every vertex added since `start` (build a part at the origin, then place it)."""
    for i in range(start, len(m.v)):
        m.v[i] = mat3 @ m.v[i] + offset


def cyl_point(a_deg, z, r, center=C):
    a = math.radians(a_deg)
    return Vector((center.x + r * math.cos(a), center.y + r * math.sin(a), z))


def jag(n, amp, seed):
    rng = random.Random(seed)
    return [(rng.random() - 0.35) * amp for _ in range(n)]


# ---------------------------------------------------------------- parts
def altar(m):
    lathe(m, ALTAR, 12, C, 'M_stone', 'stone', rot=math.radians(7.5), jitter=0.02, seed=1,
          cap_top=True, smooth=False)
    # Glowing runes on the camera-facing risers of the lower two steps.
    rng = random.Random(2)
    for r, z0, z1 in ((3.2, 0.0, 0.45), (2.7, 0.45, 0.9)):
        zc = (z0 + z1) / 2
        for a in range(38, 150, 16):
            a += rng.uniform(-3, 3)
            s = 0.15 if rng.random() < 0.6 else 0.1
            p = cyl_point(a, zc, r + 0.035)
            t = Vector((-math.sin(math.radians(a)), math.cos(math.radians(a)), 0))
            up = Vector((0, 0, 1))
            out = (p - Vector((C.x, C.y, zc))).normalized()
            poly(m, [p + t * s, p + up * s, p - t * s, p - up * s], 'M_rune', 'rune', out)


def jar_glass(m, s):
    lathe(m, GLASS, 14, C, 'M_glass', 'glass', smooth=True)
    # Glass cracks: pale glinting lines (M_crack), spider-webbed around impact points on the
    # camera-facing side; the leaking jar adds longer running cracks. Dark lines read as ink, not glass.
    webs = {0: [], 1: [(84, 4.3)], 2: [(70, 4.6), (104, 3.4), (88, 5.2)]}[s]
    rng = random.Random(40 + s)
    for (a, z) in webs:
        web(m, a, z, rng)
    if s == 2:
        for k in range(3):
            a, z = rng.uniform(60, 120), rng.uniform(2.4, 5.0)
            crack_run(m, a, z, rng, rng.randint(5, 8))


GLASS_R = 2.04                                              # just outside the glass wall


def crack_seg(m, a0, z0, a1, z1, w=0.028):
    p0, p1 = cyl_point(a0, z0, GLASS_R), cyl_point(a1, z1, GLASS_R)
    out = (p0 - Vector((C.x, C.y, p0.z))).normalized()
    side = (p1 - p0).cross(out).normalized() * (w / 2)
    poly(m, [p0 - side, p0 + side, p1 + side, p1 - side], 'M_crack', 'crack', out)


def web(m, a, z, rng):
    """Impact star: kinked radial spokes + broken concentric rings between them."""
    deg_per_unit = 360 / (TAU * GLASS_R)                    # arc length -> degrees on the jar
    n = rng.randint(6, 8)
    spokes = []
    for i in range(n):
        ang = TAU * i / n + rng.uniform(-0.25, 0.25)
        L = rng.uniform(0.7, 1.3)
        pts, r = [(a, z)], 0.0
        while r < L:
            r = min(L, r + rng.uniform(0.18, 0.32))
            ang += rng.uniform(-0.18, 0.18)
            pts.append((a + math.cos(ang) * r * deg_per_unit, z + math.sin(ang) * r))
        for (a0, z0), (a1, z1) in zip(pts, pts[1:]):
            crack_seg(m, a0, z0, a1, z1, 0.075)
        spokes.append(pts)
    for ring in (1, 2):                                     # rings link neighbouring spokes
        for i in range(n):
            if rng.random() < 0.35:
                continue
            A, B = spokes[i], spokes[(i + 1) % n]
            if len(A) > ring and len(B) > ring:
                crack_seg(m, *A[ring], *B[ring], 0.055)


def crack_run(m, a, z, rng, steps):
    for _ in range(steps):
        a2, z2 = a + rng.uniform(-7, 7), z + rng.uniform(-0.45, 0.45)
        crack_seg(m, a, z, a2, z2, 0.065)
        if rng.random() < 0.3:                               # small side branch
            crack_seg(m, a2, z2, a2 + rng.uniform(-5, 5), z2 + rng.uniform(-0.3, 0.3), 0.045)
        a, z = a2, z2


def brine(m, level):
    """The juice, built so it never sits IN FRONT of the pickle: inward-facing walls (with backface
    culling only the far inner wall draws) + an upward-facing surface. The pickle keeps its own green
    against coloured juice instead of being tinted yellow/teal through a filled volume."""
    prof = [(r * 0.93, z) for r, z in GLASS if z <= level] + [(1.86, level)]
    prof[0] = (1.45, TOP_Z + 0.08)
    rings = lathe(m, prof, 14, C, 'M_brine_team', 'brine', smooth=True, flip=True)
    poly(m, [m.v[i].copy() for i in rings[-1]], 'M_brine_team', 'brine', Vector((0, 0, 1)))   # surface
    poly(m, [m.v[i].copy() for i in rings[0]], 'M_brine_team', 'brine', Vector((0, 0, 1)))    # floor


def pickle(m, lying=False):
    start = len(m.v)
    prof = [(0.0, 0.0), (0.34, 0.1), (0.6, 0.42), (0.72, 0.95), (0.76, 1.8), (0.7, 2.7),
            (0.6, 3.15), (0.36, 3.45), (0.0, 3.58)]
    lathe(m, prof, 9, Vector((0, 0, 0)), 'M_pickle', 'pickle', jitter=0.16, seed=7, smooth=False)
    for i in range(start, len(m.v)):                         # banana curve
        v = m.v[i]
        v.x += 0.1 * (v.z - 1.8) ** 2
    if lying:   # flopped out over the front edge of the altar, toward the camera
        rot = Matrix.Rotation(math.radians(-8), 3, 'Z') @ Matrix.Rotation(math.radians(84), 3, 'Y')
        xform(m, start, rot, Vector((C.x - 1.6, C.y + 1.5, TOP_Z + 0.62)))
    else:
        rot = Matrix.Rotation(math.radians(9), 3, 'Y') @ Matrix.Rotation(math.radians(-6), 3, 'X')
        xform(m, start, rot, Vector((C.x - 0.25, C.y, TOP_Z + 0.55)))


PICKLE_MID = 1.79                                             # half the pickle's length (its centre)


def pickle_free(m):
    """The pickle on its own, centred on the origin and upright: the victory cinematic launches it.
    Exported as `core_pickle`, parked where the in-jar pickle floats (see main)."""
    start = len(m.v)
    prof = [(0.0, 0.0), (0.34, 0.1), (0.6, 0.42), (0.72, 0.95), (0.76, 1.8), (0.7, 2.7),
            (0.6, 3.15), (0.36, 3.45), (0.0, 3.58)]
    lathe(m, prof, 9, Vector((0, 0, 0)), 'M_pickle', 'pickle', jitter=0.16, seed=7, smooth=False)
    for i in range(start, len(m.v)):
        v = m.v[i]
        v.x += 0.1 * (v.z - 1.8) ** 2
        v.z -= PICKLE_MID


LID_Z = 6.64                                                  # lid pivot height (rim centre)


def lid(m, at=None):
    """The bronze lid with rivets + knob, built around its own centre (0, 0, 0).
    at=(Matrix, position) rotates it about that centre and moves it; default = on the jar."""
    start = len(m.v)
    base = Vector((0, 0, -LID_Z))
    lathe(m, LID, 14, base, 'M_bronze', 'bronze', smooth=False)
    for i in range(12):
        p = cyl_point(i * 30, 0.0, 1.8, Vector((0, 0, 0)))
        box(m, p, (0.13, 0.13, 0.13), 'M_bronze', 'rivet', rot_z=math.radians(i * 30))
    rot, pos = at if at else (Matrix.Identity(3), Vector((C.x, C.y, LID_Z)))
    xform(m, start, rot, pos)


def seal_and_tag(m):
    a = 72
    p = cyl_point(a, 6.62, 1.86)
    out = (p - Vector((C.x, C.y, p.z))).normalized()
    t = Vector((-math.sin(math.radians(a)), math.cos(math.radians(a)), 0))
    up = Vector((0, 0, 1))
    ring = [p + out * 0.05 + (t * math.cos(k * TAU / 8) + up * math.sin(k * TAU / 8)) * 0.32 for k in range(8)]
    poly(m, ring, 'M_cloth_team', 'seal', out)                               # wax seal
    q = p + out * 0.04 + t * 0.34
    tail = [q + up * 0.1, q + t * 0.42 + up * 0.1, q + t * 0.5 - up * 1.35, q + t * 0.26 - up * 1.1,
            q + t * 0.06 - up * 1.4]
    poly(m, tail, 'M_cloth_team', 'cloth', out)                              # tattered ribbon


def chain(m, p0, p1, sag, frac=1.0, seed=0):
    """Iron links along a sagging curve p0 -> p1; frac < 1 stops early (snapped)."""
    rng = random.Random(seed)
    mid = (p0 + p1) / 2 - Vector((0, 0, sag))
    pts, n = [], 60
    for i in range(n + 1):
        t = i / n
        pts.append((1 - t) ** 2 * p0 + 2 * (1 - t) * t * mid + t ** 2 * p1)
    length = sum((pts[i + 1] - pts[i]).length for i in range(n))
    step, R, r = 0.26, 0.15, 0.045
    k, acc, target = 0, 0.0, 0.0
    idx = 0
    while target <= length * frac:
        while idx < n and acc + (pts[idx + 1] - pts[idx]).length < target:
            acc += (pts[idx + 1] - pts[idx]).length
            idx += 1
        if idx >= n:
            break
        seg = pts[idx + 1] - pts[idx]
        d = seg.normalized()
        c = pts[idx] + d * (target - acc)
        ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
        s = d.cross(ref).normalized()
        if k % 2:
            s = d.cross(s).normalized()                        # alternate link planes
        w = d.cross(s).normalized()
        rings = []
        for i in range(6):
            u = TAU * i / 6
            cc = c + d * (R * 1.35 * math.cos(u)) + s * (R * math.sin(u))
            rad = (d * math.cos(u) + s * math.sin(u)).normalized()
            rings.append([m.vert(cc + (rad * math.cos(v) + w * math.sin(v)) * r)
                          for v in (TAU * j / 4 for j in range(4))])
        for i in range(6):
            i2 = (i + 1) % 6
            for j in range(4):
                j2 = (j + 1) % 4
                m.face([rings[i][j], rings[i2][j], rings[i2][j2], rings[i][j2]], [(0, 0)] * 4, 'M_iron', 'iron')
        k += 1
        target += step


def posts(m):
    tops = []
    for i, a in enumerate(POST_ANGLES):
        p = cyl_point(a, 0.45, POST_R)
        box(m, (p.x, p.y, 0.45 + 0.8), (0.5, 0.5, 1.6), 'M_stone', 'stone', rot_z=math.radians(a), jitter=0.06, seed=60 + i)
        box(m, (p.x, p.y, 2.12), (0.34, 0.34, 0.24), 'M_iron', 'iron', rot_z=math.radians(a))
        tops.append(Vector((p.x, p.y, 2.2)))
    return tops


def chains(m, s, tops):
    for i, (a, top) in enumerate(zip(POST_ANGLES, tops)):
        end = cyl_point(a, 5.55, 1.96)
        if s >= 3:
            # slack stubs hanging off the posts (s3 wreck, s4 wreck after the cinematic)
            chain(m, top, top + (end - top).normalized() * 0.4 - Vector((0, 0, 1.6)), 0.2, seed=i)
        elif s == 2 and a == 40:
            chain(m, top, end, 0.35, frac=0.45, seed=i)                        # snapped
            chain(m, end, end - Vector((0, 0, 1.4)) + (top - end).normalized() * 0.3, 0.05, seed=i + 9)
        else:
            chain(m, top, end, 0.35, seed=i)


def candles(m):
    rng = random.Random(80)
    spots = [(70, 2.95, 0.45), (84, 2.92, 0.45), (99, 2.97, 0.45), (113, 2.94, 0.45),
             (64, 3.55, 0.0), (121, 3.5, 0.0), (92, 3.6, 0.0)]
    for i, (a, r, z) in enumerate(spots):
        p = cyl_point(a, z, r)
        h = rng.uniform(0.28, 0.62)
        rad = rng.uniform(0.11, 0.16)
        lathe(m, [(rad, 0), (rad, h), (rad * 0.85, h + 0.03)], 6, Vector((p.x, p.y, z)), 'M_candle', 'candle',
              smooth=False, cap_top=True)
        f = Vector((p.x, p.y, z + h + 0.14))
        for ang in (0, 90):
            t = Vector((math.cos(math.radians(ang)), math.sin(math.radians(ang)), 0))
            pts = [f - Vector((0, 0, 0.12)), f + t * 0.07, f + Vector((0, 0, 0.16)), f - t * 0.07]
            n = t.cross(Vector((0, 0, 1)))
            poly(m, pts, 'M_flame', 'flame', n)
            poly(m, pts[::-1], 'M_flame', 'flame', -n)


def banners(m):
    # Behind the jar (away from the camera), flanking it, so they frame it instead of covering it.
    for i, (dx, h) in enumerate(((-2.1, 6.4), (2.2, 6.9))):
        base = Vector((C.x + dx, C.y - 3.6, 0))
        beam(m, base, base + Vector((0, 0, h)), 0.16, 'M_wood', 'wood')
        beam(m, base + Vector((-0.85, 0, h - 0.35)), base + Vector((0.85, 0, h - 0.35)), 0.12, 'M_wood', 'wood')
        box(m, base + Vector((0, 0, h + 0.12)), (0.22, 0.22, 0.24), 'M_bronze', 'bronze')
        y = base.y + 0.1
        top, bot = h - 0.45, h - 3.3
        xs = [-0.72, -0.36, 0.0, 0.36, 0.72]
        pts = [Vector((base.x + xs[0], y, top)), Vector((base.x + xs[-1], y, top)),
               Vector((base.x + xs[-1], y, bot + 0.25)), Vector((base.x + 0.36, y, bot - 0.1)),
               Vector((base.x + 0.0, y, bot + 0.35)), Vector((base.x - 0.36, y, bot - 0.1)),
               Vector((base.x + xs[0], y, bot + 0.25))]
        poly(m, pts, 'M_cloth_team', 'cloth', Vector((0, 1, 0)))
        emb = Vector((base.x, y + 0.02, (top + bot) / 2 + 0.2))
        poly(m, [emb + Vector((0, 0, 0.42)), emb + Vector((0.3, 0, 0)), emb - Vector((0, 0, 0.42)),
                 emb - Vector((0.3, 0, 0))], 'M_bronze', 'emblem', Vector((0, 1, 0)))


def lane_wards(m):
    """Rune obelisks on the two rails + a low curb: the core closes the lane end like the castle."""
    for i, y in enumerate((LANE_HALF, -LANE_HALF)):
        box(m, (0.1, y, 1.3), (1.1, 1.1, 2.6), 'M_stone', 'stone', jitter=0.08, seed=90 + i)
        lathe(m, [(0.78, 2.6), (0.0, 3.3)], 4, Vector((0.1, y, 0)), 'M_stone', 'stone', rot=math.radians(45),
              smooth=False)
        f = Vector((0.1, y + 0.56, 1.6))
        poly(m, [f + Vector((0, 0, 0.45)), f + Vector((0.26, 0, 0)), f - Vector((0, 0, 0.45)),
                 f - Vector((0.28, 0, 0))], 'M_rune', 'rune', Vector((0, 1, 0)))
    rng = random.Random(95)
    y = -LANE_HALF + 0.8
    while y < LANE_HALF - 0.8:
        L = rng.uniform(0.9, 1.4)
        L = min(L, LANE_HALF - 0.8 - y)
        if L < 0.3:
            break
        box(m, (0.1, y + L / 2, 0.22), (0.7, L - 0.06, 0.44), 'M_stone', 'stone', jitter=0.06, seed=int(y * 10) + 200)
        y += L


def puddle(m, center, r0, r1, z, seed):
    rng = random.Random(seed)
    c = m.vert(Vector((center.x, center.y, z)))
    ring = []
    for i in range(16):
        a = TAU * i / 16
        rr = rng.uniform(r0, r1)
        ring.append(m.vert(Vector((center.x + rr * math.cos(a), center.y + rr * math.sin(a), z))))
    for i in range(16):
        m.face([c, ring[i], ring[(i + 1) % 16]], [(0, 0)] * 3, 'M_brine_team', 'brine')


def shattered_glass(m):
    lathe(m, GLASS[:3], 14, C, 'M_glass', 'glass', jag_top=jag(14, 1.4, 55), smooth=True)
    rng = random.Random(56)
    for i, a in enumerate((58, 96, 131, 250)):                                 # standing shards
        h = rng.uniform(1.2, 2.2)
        b0, b1 = cyl_point(a - 6, 2.0, 2.0), cyl_point(a + 6, 2.0, 2.0)
        tip = cyl_point(a + rng.uniform(-4, 4), 2.0 + h, 1.95)
        out = (b0 - Vector((C.x, C.y, 2.0))).normalized()
        poly(m, [b0, b1, tip], 'M_glass', 'glass', out)
    for i in range(16):                                                        # glass scattered on the floor
        a = rng.uniform(0, 360)
        r = rng.uniform(2.6, 5.0)
        z = 0.47 if r < 3.2 else 0.02
        p = cyl_point(a, z, r)
        s = rng.uniform(0.12, 0.3)
        ang = rng.uniform(0, TAU)
        pts = [p + Vector((math.cos(ang + k * 2.1) * s, math.sin(ang + k * 2.1) * s, 0)) for k in range(3)]
        poly(m, pts, 'M_glass', 'glass', Vector((0, 0, 1)))


# ---------------------------------------------------------------- the core, per state
def build_state(s):
    m = MB()
    altar(m)
    lane_wards(m)
    tops = posts(m)
    chains(m, s, tops)
    candles(m)
    banners(m)
    if s < 3:
        jar_glass(m, s)
        brine(m, 5.55 if s < 2 else 3.7)
        pickle(m)
        lid(m)
        seal_and_tag(m)
        if s == 2:
            puddle(m, Vector((C.x - 0.6, C.y + 1.9, 0)), 0.5, 0.9, TOP_Z + 0.01, 71)    # leaking
            puddle(m, Vector((C.x - 0.9, C.y + 3.9, 0)), 0.5, 1.0, 0.02, 72)
    else:
        shattered_glass(m)
        if s == 3:
            pickle(m, lying=True)       # s4 = the same wreck after the cinematic carried the pickle away
        puddle(m, Vector((C.x, C.y, 0)), 2.0, 2.35, TOP_Z + 0.01, 73)
        puddle(m, Vector((C.x - 0.8, C.y + 4.2, 0)), 1.2, 2.1, 0.02, 74)
        rot = Matrix.Rotation(math.radians(18), 3, 'X') @ Matrix.Rotation(math.radians(-12), 3, 'Y')
        lid(m, (rot, Vector((C.x + 1.3, C.y + 3.4, 0.55))))                       # knocked onto the ground
    return m


# ---------------------------------------------------------------- vertex-colour shading
def shade(co, tag, fr):
    if tag in ('glass', 'brine', 'rune', 'flame', 'crack', 'seal'):
        return (1.0, 1.0, 1.0)
    if tag == 'pickle':
        v = 0.72 + 0.3 * fr
        return (v, v, v * 0.95)
    if tag in ('iron', 'bronze', 'rivet', 'emblem'):
        v = 0.7 + 0.3 * fr
        return (v, v, v)
    if tag in ('cloth', 'candle'):
        v = 0.82 + 0.18 * fr
        return (v, v, v)
    v = 0.62 + 0.38 * min(1.0, co.z / 1.6)                 # ground-contact occlusion
    v *= 0.86 + 0.18 * fr
    warm = 0.5 + 0.5 * fr
    return (min(1, v * (1.0 + 0.03 * warm)), min(1, v), min(1, v * (0.95 - 0.04 * warm)))


def to_object(name, m, mats, seed):
    nv = len(m.v)
    assert not [f for f in m.f if any(i < 0 or i >= nv for i in f)], name
    keep = [i for i, f in enumerate(m.f) if len(f) >= 3 and len(set(f)) == len(f)]
    if len(keep) != len(m.f):
        for attr in ('f', 'uv', 'mat', 'smooth', 'tag'):
            setattr(m, attr, [getattr(m, attr)[i] for i in keep])
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in m.v], [], m.f)
    for key in MAT_ORDER:
        me.materials.append(mats[key])
    me.uv_layers.new(name='UVMap')                          # both layers before touching either
    me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    rng = random.Random(seed)
    uvs, cols = [], []
    for pi, poly_ in enumerate(me.polygons):
        fr = rng.random()
        for j, li in enumerate(poly_.loop_indices):
            uvs += m.uv[pi][j]
            c = shade(m.v[me.loops[li].vertex_index], m.tag[pi], fr)
            cols += (c[0], c[1], c[2], 1.0)
    me.polygons.foreach_set('material_index', m.mat)
    me.polygons.foreach_set('use_smooth', m.smooth)
    me.uv_layers['UVMap'].data.foreach_set('uv', uvs)
    me.color_attributes['Col'].data.foreach_set('color', cols)
    me.color_attributes.active_color = me.color_attributes['Col']
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def build_debris(mats):
    root = bpy.data.objects.new('core_debris', None)
    bpy.context.scene.collection.objects.link(root)
    rng = random.Random(300)
    for i in range(14):
        a = rng.uniform(20, 160) if i < 10 else rng.uniform(160, 380)
        z = rng.uniform(2.3, 5.8)
        m = MB()
        s = rng.uniform(0.35, 0.7)
        pts = [Vector((0, 0, 0)), Vector((s, 0.02, s * 0.3)), Vector((s * 0.35, -0.02, s * 1.1))]
        poly(m, pts, 'M_glass', 'glass', Vector((0, 1, 0)))
        poly(m, pts, 'M_glass', 'glass', Vector((0, -1, 0)))
        obj = to_object(f'shard_{i:02d}', m, mats, 400 + i)
        obj.location = cyl_point(a, z, 2.0)
        obj.rotation_euler = (0, 0, math.radians(a + 90))
        obj.parent = root
    m = MB()
    lid(m, (Matrix.Identity(3), Vector((0, 0, 0))))
    obj = to_object('lid', m, mats, 450)
    obj.location = Vector((C.x, C.y, LID_Z))
    obj.parent = root
    return root


# ---------------------------------------------------------------- scene, export
def reset_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def export(objs):
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, 'core.blend'), compress=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT_DIR, 'core.glb'), export_format='GLB',
        export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_apply=True,
        export_yup=True, export_materials='EXPORT', export_image_format='AUTO',
        use_visible=False, export_animations=False)


def main():
    reset_scene()
    mats = build_materials()
    states = []
    for s in range(5):              # s4: shattered, pickle gone (after the victory cinematic)
        m = build_state(s)
        states.append(to_object(f'core_s{s}', m, mats, 1000 + s))
        print(f'core_s{s}: {len(m.f)} faces, {sum(len(f) - 2 for f in m.f)} tris', flush=True)
    debris = build_debris(mats)
    m = MB()
    pickle_free(m)
    pk = to_object('core_pickle', m, mats, 1100)
    pk.location = Vector((C.x - 0.25, C.y, TOP_Z + 0.55 + PICKLE_MID))
    for o in states[1:] + [pk]:
        o.hide_set(True)
    export(states + [debris, pk])
    print('exported', os.path.join(OUT_DIR, 'core.glb'), flush=True)


main()
