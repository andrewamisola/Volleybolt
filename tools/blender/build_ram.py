"""Build the battering ram in the breach (the ATTACKER's tower for the core stage) in Blender
and export it.

Run from the repo root:
    "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" -b --factory-startup ^
        --python tools/blender/build_ram.py

Writes models/ram/ram.blend and models/ram/ram.glb. Concept art: brand/concepts/ram_v1.png
(the ram shed) and brand/concepts/core_v1.png (the stage: breached gate + ram at the far end).

At a core stage the attackers have already broken INTO the defender's fortress; the defender's
core relic (the pickle jar, see build_jar.py) sits at the OTHER end of the lane. This model is
what stands where the defender's tower used to be: the wall they smashed through, still broken
open, with their covered battering ram parked in the gap.

Same conventions as tools/blender/build_castle.py / build_jar.py (helpers are copied, not
imported, because those scripts build on import):
    Blender +X = away from the court (toward the backdrop), +Y = toward the game camera, +Z up.
    Origin = the gate line on the lane's centre line; the rails sit at Blender y = +-8.0.
    The game places this at the lane end at scale 0.9 and mirrors it in X for the red side.
    The camera is fixed 30 deg above the ground looking along -Y, so faces along +-X are
    edge-on and never seen -- detail goes on tops and the +Y (camera-facing) side.

Exported scene graph:
    ram_s0..ram_s3   one joined mesh per damage state: pristine, battered, broken, wrecked
    ram_debris       empty; children are loose chunks (planks, roof plates, wheel bits, stone
                      blocks) for the crumble beat
Materials (looked up by name in the game): M_wall, M_stone (both stone, different tiling/image),
M_wood (procedural planks), M_iron, M_hide (leather roof covering), M_cloth_team (neutral grey,
tinted per side), M_dark, M_rope (tan lashings). The wall/gate wreckage is NOT team-coloured
(it's the defender's stone); only M_cloth_team (the ram's drape + banner) takes the team tint.
"""
import bpy, math, random, os
from mathutils import Vector, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT_DIR = os.path.join(ROOT, 'models', 'ram')
TEX_DIR = os.path.join(ROOT, 'textures')
TILE = 1.6
TAU = math.tau

# ---------------------------------------------------------------- layout (Blender units)
# Hero-set-piece scale: the ram + breach must read in the same size class as the castle (which
# stands ~12 tall). Chunky toy-siege-engine proportions -- big simple volumes, thick timbers,
# oversized hardware -- not a realistic scale model. TIMBER_MULT (see beam()) additionally fattens
# every structural beam well beyond the plain layout scale-up, for the "everything is chunky like
# the pickle" cartoon look.
TIMBER_MULT = 2.7

LANE_HALF = 8.0                     # rail centre line
BREACH_HALF = 4.3                   # half-width of the smashed-open gap in the wall
WALL_X = 0.75                       # wall half-thickness
# Wall remnant top height per damage state: this is the height at the BASTION end of each
# segment; it ramps DOWN toward the breach (see wall_and_bastions) so nothing near the breach
# ever stands between the camera and the ram. WALL_LOW is the height right at the breach edge.
WALL_TOP = {0: 4.0, 1: 3.8, 2: 3.3, 3: 2.5}
WALL_LOW = 1.5
BASTION_R = 1.2
# Bastions are stubby -- tall enough to read as a tower stump from the rail, short enough that
# even though they sit close to the ram in world X (the wall is centred on x=0, same as the
# breach), they never rise into the ram's silhouette in the fixed 30 deg camera.
BASTION_TOP = {0: 3.4, 1: 3.2, 2: 2.8, 3: 2.0}

# End-structure rule (measured from the live game, model units, runtime scale 0.9 already
# accounted for): the defending wizard stands at model x=-3.4, so nothing tall may pass x=-1.6
# (1 unit clear of the wizard); the visible screen edge is at model x=+7.4, so nothing may pass
# that either. The whole ram must fit in x in [-1.6, +7.2]. RAM_CX=3.0 centres the 8-long shed
# body at roughly x=-1.0..7.0 (clear of both edges with margin); the log's iron nose is
# positioned directly at NOSE_TIP_X (see log_and_chains), not derived from a protrusion length,
# so it lands exactly at the measured target regardless of shed length/position tuning.
RAM_CX = 3.0                         # ram shed centre x (behind the gate line, inside the wall)
NOSE_TIP_X = -1.4                    # iron nose front face target (wizard clearance, see above)
RAM_LEN = 8.0                        # shed length (x, direction of travel) -- hero scale, 7-9
RAM_W = 3.4                          # shed width (y)
WALL_TOP_SHED = 3.3                  # shed side-wall top (eave height)
ROOF_APEX = 6.6                      # roof ridge height -- hero scale, 6-7
WHEEL_R = 1.1                        # wheel radius -> ~2.2 diameter (spec: 2-2.4)
WHEEL_Y = RAM_W / 2 + 0.35
WHEEL_XS = [RAM_CX - 2.8, RAM_CX, RAM_CX + 2.8]
ROOF_Y_HALF = RAM_W / 2 + 0.45        # ridge half-length (ridge runs along Y, not X)


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
# per-board tone, per-row grain streak phase/strength, and a couple of knots (seamless 32x32 tile)
_board_tone = [0.86 + 0.24 * _wood_rng.random() for _ in range(4)]
_row_phase = [_wood_rng.random() * 32 for _ in range(32)]
_row_amp = [0.05 + 0.13 * _wood_rng.random() for _ in range(32)]
_knots = [(_wood_rng.randrange(32), 8 * b + 2 + _wood_rng.randrange(4)) for b in range(4) if _wood_rng.random() < 0.7]


def wood_planks(x, y):
    """Weathered timber, u = ALONG the grain (the mesh UVs run u down each beam / board's long side):
    four boards (8px rows) with dark seams, long grain streaks running along u, a few knots, and a
    weathered grey-brown palette rather than flat orange."""
    board = y // 8
    if y % 8 == 7:
        return (0.17, 0.11, 0.07)                                 # seam between boards (shadowed)
    if y % 8 == 0:
        t = 0.82                                                  # a lit bevel on the board's top edge
    else:
        t = 1.0
    # grain: slow wavy streaks along u, different per row, a few dark lines
    w = math.sin((x + _row_phase[y]) * TAU / 32 * 2) * _row_amp[y]
    streak = 1.0 + w - (0.16 if (x * 7 + y * 13) % 29 == 0 else 0.0)
    k = 1.0
    for kx, ky in _knots:
        dx = min(abs(x - kx), 32 - abs(x - kx)); dy = abs(y - ky)
        if dx * dx + dy * dy * 3 <= 4:
            k = 0.62 if dx * dx + dy * dy * 3 <= 1 else 0.8
    g = _board_tone[board] * streak * k * t
    base = (0.50, 0.36, 0.24)                                     # weathered oak, a touch grey
    return tuple(min(1.0, c * g) for c in base)


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


MAT_ORDER = ['M_wall', 'M_stone', 'M_wood', 'M_iron', 'M_hide', 'M_cloth_team', 'M_dark', 'M_rope']


def build_materials():
    return {
        'M_wall': make_mat('M_wall', load_image('castle_wall.png')),
        'M_stone': make_mat('M_stone', load_image('tower_stone.png')),
        'M_wood': make_mat('M_wood', load_image('wood_planks.png')),   # pixel-first, shared (tools/pixelate_textures.py)
        'M_iron': make_mat('M_iron', color=(0.09, 0.085, 0.095, 1)),
        'M_hide': make_mat('M_hide', color=(0.22, 0.13, 0.07, 1)),
        'M_cloth_team': make_mat('M_cloth_team', color=(0.85, 0.85, 0.85, 1)),
        'M_dark': make_mat('M_dark', color=(0.10, 0.08, 0.07, 1)),
        'M_rope': make_mat('M_rope', color=(0.62, 0.50, 0.30, 1)),
    }


# ---------------------------------------------------------------- mesh accumulator (from build_jar)
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
        if mat == 'M_wood':
            ea = max(p[a] for p in pts) - min(p[a] for p in pts)
            eb = max(p[b] for p in pts) - min(p[b] for p in pts)
            if eb > ea:
                a, b = b, a                                       # u (grain) along the long side
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
            if flip:
                idx, uvs = idx[::-1], uvs[::-1]
            m.face(idx, uvs, mat, tag, smooth)
    if cap_top and len(rings[-1]) > 2:
        m.quad_planar(rings[-1], mat, tag)
    return rings


def box(m, center, size, mat, tag, rot_z=0.0, tilt=(0.0, 0.0), jitter=0.0, seed=0, top_jag=None,
        batter=0.0):
    """Axis box (optionally yaw/tilt/jittered), from build_castle. top_jag: 4 z offsets for the
    top corners; batter: widens the base outward (for battered stone walls)."""
    rng = random.Random(seed)
    sx, sy, sz = (s / 2 for s in size)
    corners = []
    for zi, dz in enumerate((-sz, sz)):
        for (dx, dy) in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
            if zi == 0 and batter:
                dx *= (sx + batter) / sx
            p = Vector((dx, dy, dz))
            if zi == 1 and top_jag:
                p.z += top_jag[len(corners) - 4]
            if jitter:
                p += Vector([(rng.random() - 0.5) * jitter for _ in range(3)])
            corners.append(p)
    cz, sz_, cx, sx_, cy, sy_ = (math.cos(rot_z), math.sin(rot_z), math.cos(tilt[0]),
                                  math.sin(tilt[0]), math.cos(tilt[1]), math.sin(tilt[1]))
    idx = []
    for p in corners:
        y1, z1 = p.y * cx - p.z * sx_, p.y * sx_ + p.z * cx
        x2, z2 = p.x * cy + z1 * sy_, -p.x * sy_ + z1 * cy
        x3, y3 = x2 * cz - y1 * sz_, x2 * sz_ + y1 * cz
        idx.append(m.vert(Vector((x3, y3, z2)) + Vector(center)))
    b0, b1, b2, b3, t0, t1, t2, t3 = idx
    for f in ([b3, b2, b1, b0], [t0, t1, t2, t3], [b0, b1, t1, t0], [b1, b2, t2, t1],
              [b2, b3, t3, t2], [b3, b0, t0, t3]):
        m.quad_planar(f, mat, tag)
    return idx


def beam(m, p0, p1, t, mat, tag):
    t *= TIMBER_MULT                    # chunky toy-siege-engine timbers, not realistic scale
    d = (p1 - p0).normalized()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    s = d.cross(up).normalized() * (t / 2)
    u = d.cross(s).normalized() * (t / 2)
    ring = lambda p: [m.vert(p + s + u), m.vert(p - s + u), m.vert(p - s - u), m.vert(p + s - u)]
    a, b = ring(p0), ring(p1)
    L = (p1 - p0).length / TILE
    for i in range(4):
        j = (i + 1) % 4
        if mat == 'M_wood':
            # u along the beam (the texture's grain), v across one board (rows are 8px = 0.25)
            v0 = 0.25 * i + 0.01
            m.face([a[i], a[j], b[j], b[i]], [(0, v0), (0, v0 + 0.23), (L, v0 + 0.23), (L, v0)], mat, tag)
        else:
            m.quad_planar([a[i], a[j], b[j], b[i]], mat, tag)
    m.quad_planar(a[::-1], mat, tag)
    m.quad_planar(b, mat, tag)


def log_beam(m, p0, p1, r0, r1, sides, mat, tag):
    """Tapered round log/pole from p0 (radius r0) to p1 (radius r1), with end caps."""
    d = (p1 - p0).normalized()
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))
    s = d.cross(ref).normalized()
    u = d.cross(s).normalized()
    ring0 = [m.vert(p0 + (s * math.cos(TAU * i / sides) + u * math.sin(TAU * i / sides)) * r0)
             for i in range(sides)]
    ring1 = [m.vert(p1 + (s * math.cos(TAU * i / sides) + u * math.sin(TAU * i / sides)) * r1)
             for i in range(sides)]
    for i in range(sides):
        j = (i + 1) % sides
        m.quad_planar([ring0[i], ring0[j], ring1[j], ring1[i]], mat, tag)
    m.quad_planar(ring0[::-1], mat, tag)
    m.quad_planar(ring1, mat, tag)
    return ring0, ring1


def poly(m, pts, mat, tag, facing, smooth=False):
    """Flat polygon from world points, wound so its normal points along `facing`."""
    n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
    if n.dot(facing) < 0:
        pts = pts[::-1]
    idx = [m.vert(p) for p in pts]
    m.quad_planar(idx, mat, tag, smooth)


def xform(m, start, mat3, offset):
    for i in range(start, len(m.v)):
        m.v[i] = mat3 @ m.v[i] + offset


def tilt_about(m, start, pivot, mat3):
    """Rotate every vertex added since `start` about a world-space pivot (in place)."""
    for i in range(start, len(m.v)):
        m.v[i] = pivot + mat3 @ (m.v[i] - pivot)


def cyl_point(a_deg, z, r, center=Vector((0, 0, 0))):
    a = math.radians(a_deg)
    return Vector((center.x + r * math.cos(a), center.y + r * math.sin(a), z))


def jag(n, amp, seed, base=0.0):
    rng = random.Random(seed)
    return [base + (rng.random() - 0.5) * 2 * amp for _ in range(n)]


def chain(m, p0, p1, sag, frac=1.0, seed=0):
    """Iron links along a sagging curve p0 -> p1; frac < 1 stops early (snapped). From build_jar."""
    rng = random.Random(seed)
    mid = (p0 + p1) / 2 - Vector((0, 0, sag))
    pts, n = [], 60
    for i in range(n + 1):
        t = i / n
        pts.append((1 - t) ** 2 * p0 + 2 * (1 - t) * t * mid + t ** 2 * p1)
    length = sum((pts[i + 1] - pts[i]).length for i in range(n))
    step, R, r = 0.46, 0.27, 0.09          # oversized chunky links, not fine hardware
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
            s = d.cross(s).normalized()
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


def rubble(m, center, count, spread, height, seed, mats=('M_wall', 'M_stone')):
    rng = random.Random(seed)
    for i in range(count):
        ang = rng.random() * TAU
        d = spread * math.sqrt(rng.random())
        s = 0.22 + rng.random() * 0.34
        z = max(0.0, height * (1 - d / spread)) * rng.random() + s * 0.35
        c = (center[0] + d * math.cos(ang), center[1] + d * math.sin(ang), z)
        box(m, c, (s * 1.3, s, s * 0.8), mats[i % len(mats)], 'rubble',
            rot_z=rng.random() * TAU, tilt=(rng.random() - 0.5, rng.random() - 0.5),
            jitter=s * 0.45, seed=seed * 100 + i)


# ---------------------------------------------------------------- the breached wall + bastions
def wall_and_bastions(m, s):
    """The wall ramps DOWN toward the breach (<=WALL_LOW right at the gap) and back UP toward
    the bastions at the rails, so nothing near the ram ever stands between it and the camera --
    only the short bastion stumps out at y=+-8 read as "wall", well clear of the shed."""
    top_far = WALL_TOP[s]
    segs = [(-LANE_HALF, -BREACH_HALF), (BREACH_HALF, LANE_HALF)]
    n_sub = 4
    for k, (y0, y1) in enumerate(segs):
        for i in range(n_sub):
            ya = y0 + (y1 - y0) * i / n_sub
            yb = y0 + (y1 - y0) * (i + 1) / n_sub
            yc = (ya + yb) / 2
            dist = max(0.0, abs(yc) - BREACH_HALF)
            t = min(1.0, dist / (LANE_HALF - BREACH_HALF))
            top = WALL_LOW + (top_far - WALL_LOW) * t
            jt = jag(4, 0.3, 40 + k * 10 + i + s * 7, base=-0.08 * s)
            box(m, (0.0, yc, top / 2), (WALL_X * 2, yb - ya, top), 'M_wall', 'stone',
                seed=20 + k * 10 + i, top_jag=jt, batter=0.1, jitter=0.03)
            if top > 1.8:                                          # merlons only where tall enough
                rng = random.Random(50 + k * 10 + i)
                n_mer = max(1, int((yb - ya) / 0.9))
                for j in range(n_mer):
                    yy = ya + 0.45 + j * 0.9
                    if yy >= yb or rng.random() < 0.12 * s:
                        continue
                    h = 0.35 + rng.random() * 0.2
                    box(m, (0.0, yy, top + h / 2), (WALL_X * 1.6, 0.5, h), 'M_wall', 'stone',
                        tilt=((rng.random() - 0.5) * 0.15, 0), jitter=0.05,
                        seed=200 + k * 50 + i * 5 + j)
    rubble(m, (0.15, -BREACH_HALF + 0.2), 9 + 2 * s, 1.3, 0.55, 300 + s)
    rubble(m, (0.15, BREACH_HALF - 0.2), 9 + 2 * s, 1.3, 0.55, 310 + s)
    for name, yb in (('near', LANE_HALF), ('far', -LANE_HALF)):
        top_b = BASTION_TOP[s]
        prof = [(BASTION_R, 0.0), (BASTION_R, 0.3), (BASTION_R * 0.9, 0.4),
                (BASTION_R * 0.85, top_b - 0.15), (BASTION_R * 0.95, top_b)]
        lathe(m, prof, 8, Vector((0.0, yb, 0)), 'M_stone', 'stone', jitter=0.03,
              seed=hash(name) % 97, jag_top=jag(8, 0.25, 80) if s >= 2 else None, cap_top=True)
        if s >= 2:
            rubble(m, (0.4, yb - math.copysign(0.6, yb)), 6, 0.9, 0.35, hash(name) % 50 + s)
    gate_debris(m)


def gate_debris(m):
    """The smashed wooden gate door + bent iron straps, lying in and around the breach."""
    rng = random.Random(500)
    for i in range(8):
        x = rng.uniform(-2.3, 2.6)
        y = rng.uniform(-BREACH_HALF + 0.3, BREACH_HALF - 0.3)
        ang = rng.uniform(0, TAU)
        length = rng.uniform(1.4, 3.0)
        p0 = Vector((x, y, 0.08))
        p1 = p0 + Vector((math.cos(ang) * length, math.sin(ang) * length, rng.uniform(0.0, 0.2)))
        beam(m, p0, p1, 0.1 + rng.uniform(0, 0.05), 'M_wood', 'wood')
    for i in range(3):
        x, y = rng.uniform(-1.8, 2.1), rng.uniform(-BREACH_HALF + 0.5, BREACH_HALF - 0.5)
        ang = rng.uniform(0, TAU)
        p0 = Vector((x, y, 0.08))
        p1 = p0 + Vector((math.cos(ang) * 1.2, math.sin(ang) * 1.2, 0.15))
        p2 = p1 + Vector((math.cos(ang + 1.1) * 0.85, math.sin(ang + 1.1) * 0.85, 0.08))
        beam(m, p0, p1, 0.07, 'M_iron', 'iron')
        beam(m, p1, p2, 0.07, 'M_iron', 'iron')


def muzzle_rubble(m):
    """Extra smashed planks + stone rubble right where the log pokes out, so the ram reads as
    having just punched through (not parked politely behind an intact wall)."""
    rng = random.Random(555)
    head_x = NOSE_TIP_X + 0.3            # tracks the log's nose-tip area (low debris only -- the
                                          # x<-1.6 clearance rule only applies to tall geometry)
    for i in range(5):
        x = head_x + rng.uniform(-1.0, 2.0)
        y = rng.uniform(-2.2, 2.2)
        ang = rng.uniform(0, TAU)
        length = rng.uniform(0.9, 1.9)
        p0 = Vector((x, y, 0.05))
        p1 = p0 + Vector((math.cos(ang) * length, math.sin(ang) * length, rng.uniform(0, 0.15)))
        box(m, ((p0 + p1) / 2), (0.7, 0.48, 0.42), 'M_stone' if i % 2 else 'M_wall', 'rubble',
            rot_z=ang, jitter=0.16, seed=560 + i)
    for i in range(4):
        x = head_x + rng.uniform(-0.5, 2.3)
        y = rng.uniform(-2.0, 2.0)
        ang = rng.uniform(0, TAU)
        length = rng.uniform(1.3, 2.5)
        p0 = Vector((x, y, 0.06))
        p1 = p0 + Vector((math.cos(ang) * length, math.sin(ang) * length, rng.uniform(0, 0.2)))
        beam(m, p0, p1, 0.09, 'M_wood', 'wood')


# ---------------------------------------------------------------- the ram tortoise
def wheel(m, center, r, width, broken=False, seed=0):
    rng = random.Random(seed)
    n = 10
    ring0, ring1 = [], []
    for i in range(n):
        a = TAU * i / n
        rr = r * (1 + 0.02 * (rng.random() - 0.5))
        if broken and i in (n - 1, 0, 1):
            rr *= 0.35
        x = center.x + rr * math.cos(a)
        z = center.z + rr * math.sin(a)
        ring0.append(m.vert((x, center.y - width / 2, z)))
        ring1.append(m.vert((x, center.y + width / 2, z)))
    for i in range(n):
        j = (i + 1) % n
        m.quad_planar([ring0[i], ring0[j], ring1[j], ring1[i]], 'M_iron', 'iron')
    poly(m, [m.v[i].copy() for i in ring0], 'M_wood', 'wheel', Vector((0, -1, 0)))
    poly(m, [m.v[i].copy() for i in ring1], 'M_wood', 'wheel', Vector((0, 1, 0)))
    hub_r = r * 0.2
    for side, hub in ((-1, Vector((center.x, center.y - width / 2 - 0.04, center.z))),
                       (1, Vector((center.x, center.y + width / 2 + 0.04, center.z)))):
        pts = [hub + Vector((hub_r * math.cos(TAU * i / 6), 0, hub_r * math.sin(TAU * i / 6))) for i in range(6)]
        poly(m, pts, 'M_iron', 'hub', Vector((0, side, 0)))
    n_spoke = 3 if broken else 5
    for i in range(n_spoke):
        a = TAU * i / n_spoke + (0.3 if broken else 0)
        rr = r * 0.82
        tip = Vector((center.x + rr * math.cos(a), center.y, center.z + rr * math.sin(a)))
        beam(m, center, tip, 0.09, 'M_wood', 'wood')


def side_frame(m, side, x0, x1, wall_top):
    """Open post-and-brace frame (NOT a solid panel): the shed's sides are open so the log ram
    and its chains read clearly from the camera through the framing, tortoise-cage style."""
    y = side * (RAM_W / 2)
    z0 = 0.2
    xm = (x0 + x1) / 2
    for x in (x0, xm, x1):
        beam(m, Vector((x, y, z0 - 0.1)), Vector((x, y, wall_top + 0.15)), 0.16, 'M_wood', 'wood')
    beam(m, Vector((x0, y, wall_top)), Vector((x1, y, wall_top)), 0.12, 'M_wood', 'wood')
    beam(m, Vector((x0, y, z0)), Vector((x1, y, z0)), 0.1, 'M_wood', 'wood')
    for xa, xb in ((x0, xm), (xm, x1)):
        beam(m, Vector((xa, y, z0)), Vector((xb, y, wall_top)), 0.09, 'M_wood', 'wood')
        beam(m, Vector((xa, y, wall_top)), Vector((xb, y, z0)), 0.09, 'M_wood', 'wood')
    midz = (z0 + wall_top) / 2
    box(m, (xm, y + 0.03 * side, midz), (0.55, 0.12, 0.55), 'M_iron', 'iron')


def shield(m, center, w, h, seed):
    """A round-ish pavise hung on the open frame, facing the camera; small team-colour accent
    stripe down the middle so the team read survives even with the roof cloth cut way back."""
    rng = random.Random(seed)
    offs = [(0, h * 0.5), (w * 0.42, h * 0.22), (w * 0.5, -h * 0.05), (w * 0.3, -h * 0.5),
            (0, -h * 0.62), (-w * 0.3, -h * 0.5), (-w * 0.5, -h * 0.05), (-w * 0.42, h * 0.22)]
    pts = [center + Vector((dx + rng.uniform(-0.03, 0.03), 0, dz)) for dx, dz in offs]
    poly(m, pts, 'M_wood', 'shield', Vector((0, 1, 0)))
    boss = [center + Vector((0.18 * math.cos(TAU * i / 6), 0.02, 0.18 * math.sin(TAU * i / 6)))
            for i in range(6)]
    poly(m, boss, 'M_iron', 'iron', Vector((0, 1, 0)))
    stripe = [center + Vector((-w * 0.07, 0.018, h * 0.42)), center + Vector((w * 0.07, 0.018, h * 0.42)),
              center + Vector((w * 0.07, 0.018, -h * 0.5)), center + Vector((-w * 0.07, 0.018, -h * 0.5))]
    poly(m, stripe, 'M_cloth_team', 'cloth', Vector((0, 1, 0)))


def rope_coil(m, center, r, seed):
    lathe(m, [(0.0, 0.0), (r, 0.04), (r, 0.24), (r * 0.7, 0.34), (r * 0.4, 0.4)], 8, center,
          'M_rope', 'rope', jitter=0.05, seed=seed, cap_top=True)


def bucket(m, center, seed):
    lathe(m, [(0.27, 0.0), (0.32, 0.03), (0.36, 0.5), (0.29, 0.58)], 8, center, 'M_wood', 'wood',
          jitter=0.03, seed=seed)


def wedge(m, center, rot_z, seed):
    box(m, center, (0.6, 0.32, 0.28), 'M_wood', 'wood', rot_z=rot_z, jitter=0.03, seed=seed,
        tilt=(0, math.radians(18)))


def crew_gear(m, x0, x1):
    """Big, chunky, few-and-simple props that break up the shed's silhouette and sell "lived-in
    siege engine": a couple of oversized pavises hung on the open near-side frame, a rope coil
    and bucket/wedges on the deck between the wheels."""
    xm = (x0 + x1) / 2
    y = RAM_W / 2 + 0.02
    zb = WALL_TOP_SHED * 0.62
    shield(m, Vector(((x0 + xm) / 2, y, zb)), 1.1, 1.35, 21)
    shield(m, Vector(((xm + x1) / 2 - 0.5, y, zb - 0.1)), 1.05, 1.3, 22)
    rope_coil(m, Vector((x0 + 0.9, -RAM_W / 2 + 0.5, 0.35)), 0.58, 30)
    bucket(m, Vector((x1 - 0.7, -RAM_W / 2 + 0.6, 0.35)), 31)
    wedge(m, Vector((x0 + 1.6, -RAM_W / 2 + 0.9, 0.3)), 0.4, 32)
    wedge(m, Vector((x0 + 2.05, -RAM_W / 2 + 0.85, 0.3)), 2.1, 33)


def slope(m, s, xr, xe, yh, apex, wall_top, name):
    """One long roof slope from the ridge (x=xr, full y width) down to the eave (x=xe). Faces
    +-X (not +-Y): the two slopes (west toward the muzzle/court, east toward the tail) catch the
    fixed camera differently and read as distinct planes meeting at the ridge crease, instead of
    one flat +Y-facing rectangle."""
    ridge0, ridge1 = Vector((xr, -yh, apex)), Vector((xr, yh, apex))
    eave0, eave1 = Vector((xe, -yh, wall_top)), Vector((xe, yh, wall_top))
    facing = Vector((1 if xe > xr else -1, 0, 0.6))
    open_frac = {0: 0.0, 1: 0.0, 2: 0.5 if name == 'west' else 0.0}.get(s, 0.0)
    bare = (s >= 1 and name == 'west') or (s >= 2 and name == 'east')
    if open_frac > 0:
        t = 1 - open_frac
        cut_z = apex + (wall_top - apex) * t
        cut0, cut1 = Vector((xr + (xe - xr) * t, -yh, cut_z)), Vector((xr + (xe - xr) * t, yh, cut_z))
        poly(m, [ridge0, ridge1, cut1, cut0], 'M_wood', 'wood', facing)
        n_r = 3
        for i in range(n_r + 1):
            yy = -yh + 2 * yh * i / n_r
            beam(m, Vector((cut0.x, yy, cut_z - 0.03)), Vector((xe, yy, wall_top + 0.03)), 0.06,
                 'M_wood', 'char')
        poly(m, [cut0, cut1, eave1, eave0], 'M_dark', 'interior', facing)
        return
    poly(m, [ridge0, ridge1, eave1, eave0], 'M_wood', 'wood', facing)
    if not bare:
        p0, p1 = ridge0.lerp(eave0, 0.16), ridge1.lerp(eave1, 0.16)
        p2, p3 = ridge1.lerp(eave1, 0.5), ridge0.lerp(eave0, 0.5)
        poly(m, [p0, p1, p2, p3], 'M_iron', 'iron', facing)
        p4, p5 = ridge1.lerp(eave1, 0.62), ridge0.lerp(eave0, 0.62)
        p6, p7 = ridge1.lerp(eave1, 0.94), ridge0.lerp(eave0, 0.94)
        poly(m, [p5, p4, p6, p7], 'M_iron', 'iron', facing)
    if s == 0 and name == 'west':                     # small dark leather trim near the eave
        h0, h1 = ridge0.lerp(eave0, 0.95), ridge1.lerp(eave1, 0.95)
        poly(m, [h0, h1, eave1, eave0], 'M_hide', 'hide', facing)


def near_gable_truss(m, x0, x1, yh, apex, wall_top):
    """Camera-facing (+Y) gable end: an OPEN king-post truss, no boarding, so the camera looks
    straight into the shed's length and sees the log + chains through the gap."""
    y = yh
    ridge_pt = Vector((RAM_CX, y, apex))
    beam(m, Vector((x0, y, wall_top)), Vector((x1, y, wall_top)), 0.08, 'M_wood', 'wood')
    beam(m, Vector((x0, y, wall_top)), ridge_pt, 0.08, 'M_wood', 'wood')
    beam(m, Vector((x1, y, wall_top)), ridge_pt, 0.08, 'M_wood', 'wood')
    beam(m, Vector((RAM_CX, y, wall_top + 0.04)), ridge_pt, 0.06, 'M_wood', 'wood')


def far_gable(m, x0, x1, yh, apex, wall_top):
    """Far (-Y) gable: simple closed infill -- barely seen from the fixed camera, kept cheap."""
    y = -yh
    ridge_pt = Vector((RAM_CX, y, apex))
    poly(m, [Vector((x0, y, wall_top)), Vector((x1, y, wall_top)), ridge_pt], 'M_wood', 'wood',
         Vector((0, -1, 0.3)))


def roof(m, s, x0, x1):
    apex, wall_top = ROOF_APEX, WALL_TOP_SHED
    yh = ROOF_Y_HALF
    cx = RAM_CX
    beam(m, Vector((cx, -yh, apex)), Vector((cx, yh, apex)), 0.2, 'M_wood', 'wood')
    slope(m, s, cx, x0, yh, apex, wall_top, 'west')
    slope(m, s, cx, x1, yh, apex, wall_top, 'east')
    near_gable_truss(m, x0, x1, yh, apex, wall_top)
    far_gable(m, x0, x1, yh, apex, wall_top)


def cloth_pennant(m, s, x1):
    """A small team-coloured streamer hanging from the ridge near the tail, visible through the
    open near gable -- an accent, not a roof covering (the roof itself reads as wood + iron)."""
    if s >= 3:
        return
    length = {0: 0.85, 1: 0.55, 2: 0.3}[s]
    top = Vector((x1 - 0.5, ROOF_Y_HALF * 0.5, ROOF_APEX - 0.15))
    bot = top - Vector((0, 0, length))
    w = 0.55
    pts = [top - Vector((w / 2, 0, 0)), top + Vector((w / 2, 0, 0)),
           bot + Vector((w * 0.3, 0, 0)), bot - Vector((w * 0.3, 0, 0))]
    poly(m, pts, 'M_cloth_team', 'cloth', Vector((0, 1, 0)))
    poly(m, pts[::-1], 'M_cloth_team', 'cloth', Vector((0, -1, 0)))


def banner(m, s, x1):
    if s >= 3:
        beam(m, Vector((x1 + 0.2, 0, WALL_TOP_SHED)), Vector((x1 + 0.2, 0, WALL_TOP_SHED + 0.7)),
             0.09, 'M_wood', 'char')
        return
    top = ROOF_APEX + (1.6 if s < 2 else 0.7)
    base = Vector((x1 + 0.2, 0, WALL_TOP_SHED - 0.3))
    tilt = 0.0 if s < 2 else math.radians(22)
    tip_local = Vector((0, 0, top - base.z))
    tip = base + Matrix.Rotation(tilt, 3, 'X') @ tip_local
    beam(m, base, tip, 0.11, 'M_wood', 'wood')
    if s < 2:
        flag = [tip, tip - Vector((0, 0, 0.9)), tip + Vector((-1.05, 0.1, -0.55)),
                tip + Vector((-1.75, 0.07, -0.28))]
        poly(m, flag, 'M_cloth_team', 'cloth', Vector((0, 1, 0)))
        poly(m, flag[::-1], 'M_cloth_team', 'cloth', Vector((0, -1, 0)))


def log_and_chains(m, s, x0, x1):
    r0, r1 = 0.85, 0.65              # a massive log -- ~1.7 diameter at the butt (spec: 1.4-1.8)
    # Hooks sit slightly toward the camera side of the ridge/log (not dead-centre on y=0) so the
    # chains read as their own shapes against the open frame instead of hiding behind the ridge
    # beam in silhouette.
    ridge_pt = Vector((RAM_CX - 0.5, 0.5, ROOF_APEX - 0.4))
    if s < 3:
        # The iron nose cone extends 1.1 further than p_head (log_x0) -- see the log_beam calls
        # below -- so p_head is placed exactly NOSE_TIP_X + 1.1 back from the measured target,
        # independent of the shed's own length/position. Most of the log's length still sits
        # inside the shed, seen through the open frame/gable; only the cap + nose cone poke past
        # the muzzle into the open court.
        log_x0 = NOSE_TIP_X + 1.1
        log_x1 = min(x1 - 0.5, RAM_CX + 2.8)
        p_head = Vector((log_x0, 0, 2.7))
        p_tail = Vector((log_x1, 0, 2.7))
        if s == 2:
            p_head = p_head + Vector((0, 0, -0.9))
        log_beam(m, p_head, p_tail, r0, r1, 8, 'M_wood', 'wood')
        log_beam(m, p_head - Vector((0.8, 0, 0)), p_head + Vector((0.38, 0, 0)), r0 * 1.22,
                  r0 * 1.1, 8, 'M_iron', 'iron')
        # blunt iron nose cone -- a huge iron head, the single most eye-catching thing up front
        log_beam(m, p_head - Vector((1.1, 0, 0)), p_head - Vector((0.8, 0, 0)), r0 * 0.7,
                  r0 * 1.22, 8, 'M_iron', 'iron')
        band_c = p_head + Vector((1.7, 0, 0.1))
        log_beam(m, band_c - Vector((0.19, 0, 0)), band_c + Vector((0.19, 0, 0)), r0 * 1.14,
                  r0 * 1.14, 8, 'M_iron', 'iron')
        band_c2 = p_head + Vector((3.0, 0, 0.04))
        log_beam(m, band_c2 - Vector((0.15, 0, 0)), band_c2 + Vector((0.15, 0, 0)), r0 * 1.1,
                  r0 * 1.1, 8, 'M_iron', 'iron')
        att1 = p_head + (p_tail - p_head) * 0.3 + Vector((0, r0 * 0.7, r0 * 0.7))
        att2 = p_head + (p_tail - p_head) * 0.75 + Vector((0, r0 * 0.7, r0 * 0.7))
        if s == 2:
            broken_end = ridge_pt.lerp(att1, 0.45)
            chain(m, ridge_pt, att1, 0.15, frac=0.45, seed=10)
            chain(m, broken_end, broken_end - Vector((0, 0, 1.0)), 0.05, seed=19)
        else:
            chain(m, ridge_pt, att1, 0.15, seed=10)
        chain(m, ridge_pt, att2, 0.15, seed=11)
    else:
        # Fallen log stays clear of the court-side height rule too: its far (iron-capped) end
        # reaches about as far as the intact log's nose did, not further into the open lane.
        p0 = Vector((NOSE_TIP_X + 0.4, 0.5, r0 * 0.8))
        p1 = Vector((NOSE_TIP_X + 4.0, 0.15, r0 * 0.65))
        log_beam(m, p0, p1, r0, r1, 8, 'M_wood', 'char')
        log_beam(m, p0 - Vector((0.35, 0, 0)), p0 + Vector((0.15, 0, 0)), r0 * 1.15, r0 * 1.08, 8,
                  'M_iron', 'iron')
        chain(m, Vector((RAM_CX - 0.5, 0, WALL_TOP_SHED - 0.3)),
              Vector((RAM_CX - 0.15, 0, WALL_TOP_SHED - 1.3)), 0.08, frac=0.4, seed=12)


def roof_collapsed(m, x0, x1, wall_top):
    beam(m, Vector((x0, 0, wall_top + 0.3)), Vector(((x0 + x1) / 2, 0, wall_top + 0.9)), 0.18,
         'M_wood', 'char')
    beam(m, Vector(((x0 + x1) / 2, 0, wall_top + 0.9)), Vector((x1, 0, wall_top + 0.4)), 0.18,
         'M_wood', 'char')
    rng = random.Random(900)
    for i in range(6):
        a = rng.uniform(0, TAU)
        L = rng.uniform(0.9, 2.0)
        p0 = Vector((rng.uniform(x0, x1), rng.uniform(-RAM_W / 2, RAM_W / 2),
                     wall_top + rng.uniform(0, 1.0)))
        p1 = p0 + Vector((math.cos(a) * L, math.sin(a) * L * 0.3, -rng.uniform(0.2, 0.9)))
        beam(m, p0, p1, 0.08, 'M_wood', 'char')


def ram_shed(m, s):
    x0 = RAM_CX - RAM_LEN / 2
    x1 = RAM_CX + RAM_LEN / 2
    start = len(m.v)
    broken_wheel = (1, 0) if s >= 2 else None
    for side in (1, -1):
        for wi, wx in enumerate(WHEEL_XS):
            broken = (s >= 2 and (side, wi) == broken_wheel)
            wheel(m, Vector((wx, side * WHEEL_Y, WHEEL_R)), WHEEL_R, 0.42, broken=broken,
                  seed=700 + wi + (0 if side > 0 else 50))
    wall_top = WALL_TOP_SHED if s < 3 else 1.7
    for side in (1, -1):
        side_frame(m, side, x0 + 0.35, x1, wall_top)
    if s < 3:
        roof(m, s, x0 - 0.2, x1 + 0.3)
        cloth_pennant(m, s, x1)
        crew_gear(m, x0 + 0.35, x1)
    else:
        roof_collapsed(m, x0 - 0.2, x1 + 0.3, wall_top)
    banner(m, s, x1)
    log_and_chains(m, s, x0, x1)
    muzzle_rubble(m)
    if s == 2:
        tilt_about(m, start, Vector((WHEEL_XS[0], WHEEL_Y, 0.0)), Matrix.Rotation(math.radians(-7), 3, 'X'))
    elif s == 3:
        tilt_about(m, start, Vector((RAM_CX, 0, 0.0)), Matrix.Rotation(math.radians(-10), 3, 'X'))


# ---------------------------------------------------------------- the ram, per state
def build_state(s):
    m = MB()
    wall_and_bastions(m, s)
    ram_shed(m, s)
    return m


# ---------------------------------------------------------------- vertex-colour shading
def shade(co, tag, fr):
    if tag == 'cloth':
        return (1.0, 1.0, 1.0)
    if tag in ('iron', 'hub'):
        v = 0.22 + 0.14 * fr                    # dark, strong contrast against the wood/log
        return (v, v, v * 1.05)
    if tag == 'rope':
        v = 0.75 + 0.2 * fr
        return (v, v, v * 0.9)
    if tag == 'char':
        v = 0.16 + 0.1 * fr
        return (v, v * 0.9, v * 0.85)
    if tag == 'interior':
        return (0.18, 0.15, 0.14)
    if tag == 'hide':
        v = 0.42 + 0.16 * fr                    # small dark saturated-brown accent, not the deck
        return (v * 0.85, v * 0.55, v * 0.32)
    v = 0.6 + 0.35 * min(1.0, co.z / 3.0)
    v *= 0.86 + 0.2 * fr
    warm = 0.5 + 0.5 * fr
    return (min(1, v * (1.0 + 0.03 * warm)), min(1, v), min(1, v * (0.95 - 0.04 * warm)))


# Baked light (multiplied into the corner colours). In the core stage the ram stands in the breach,
# backlit by daylight pouring in from behind it (+X, above, slightly away from the camera), and the
# game has no shadow maps -- so the shed's own shadowing is baked here: ambient occlusion (short
# hemisphere rays: the inside of the shed, under the roof, between the wheels go dark) times a
# shadow ray toward that light (anything the ram itself blocks from the breach goes darker still).
BAKE_TO_LIGHT = Vector((1.0, -0.3, 0.75)).normalized()
BAKE_AO_RAYS = 20
BAKE_AO_DIST = 3.6      # reaches the roof from the deck: the inside of the shed reads enclosed
BAKE_AO_MIN = 0.3        # fully enclosed -> 30% brightness
BAKE_SHADOW = 0.55       # blocked from the breach light -> x0.55


def bake_light(me, m, cols):
    from mathutils.bvhtree import BVHTree
    verts = [Vector(v) for v in m.v]
    tree = BVHTree.FromPolygons(verts, [list(f) for f in m.f], epsilon=0.0)

    def blocked(o, d, dist):
        # The model is built from overlapping boxes, so a ray often starts INSIDE a neighbouring
        # plank/beam. Hitting a face from behind, close by, means exactly that: step through it and go on.
        for _ in range(6):
            loc, nrm, _, hd = tree.ray_cast(o, d, dist)
            if loc is None:
                return False
            if nrm.dot(d) < 0 or hd > 0.4:      # a front face, or a back face beyond a plank's thickness
                return True                     # (single-sided roof sheets seen from inside): occluder
            o = loc + d * 0.002
            dist -= hd + 0.002
            if dist <= 0:
                return False
        return False
    rng = random.Random(4242)
    dirs = []                                   # fixed cosine-ish hemisphere set around +Z
    for i in range(BAKE_AO_RAYS):
        u, v = (i + 0.5) / BAKE_AO_RAYS, rng.random()
        r, th = math.sqrt(u), TAU * v
        dirs.append(Vector((r * math.cos(th), r * math.sin(th), math.sqrt(max(0.0, 1 - u)))))
    ci = 0
    for poly_ in me.polygons:
        n = poly_.normal.copy()
        # Tangent frame so the hemisphere set can be rotated onto this face's normal.
        t = n.cross(Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))).normalized()
        b = n.cross(t)
        for li in poly_.loop_indices:
            p = verts[me.loops[li].vertex_index] * 0.97 + poly_.center * 0.03   # nudge off the edge
            o = p + n * 0.03
            hits = 0
            for d in dirs:
                w = t * d.x + b * d.y + n * d.z
                if blocked(o, w, BAKE_AO_DIST):
                    hits += 1
            k = 1.0 - (1.0 - BAKE_AO_MIN) * (hits / BAKE_AO_RAYS)
            if n.dot(BAKE_TO_LIGHT) <= 0 or blocked(o, BAKE_TO_LIGHT, 40.0):
                k *= BAKE_SHADOW
            cols[ci * 4 + 0] *= k
            cols[ci * 4 + 1] *= k
            cols[ci * 4 + 2] *= k
            ci += 1


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
    me.uv_layers.new(name='UVMap')
    me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    rng = random.Random(seed)
    uvs, cols = [], []
    for pi, poly_ in enumerate(me.polygons):
        fr = rng.random()
        for j, li in enumerate(poly_.loop_indices):
            uvs += m.uv[pi][j]
            c = shade(m.v[me.loops[li].vertex_index], m.tag[pi], fr)
            cols += (c[0], c[1], c[2], 1.0)
    bake_light(me, m, cols)
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
    root = bpy.data.objects.new('ram_debris', None)
    bpy.context.scene.collection.objects.link(root)
    spots = [
        (RAM_CX - 1.0, WHEEL_Y + 0.3, 1.6, 'M_wood'),
        (RAM_CX - 1.6, 0.0, ROOF_APEX - 0.3, 'M_iron'),
        (RAM_CX + 0.5, -WHEEL_Y - 0.2, WALL_TOP_SHED, 'M_hide'),
        (RAM_CX - 0.3, WHEEL_Y + 0.1, WALL_TOP_SHED + 0.5, 'M_iron'),
        (RAM_CX + 1.4, 0.0, 1.0, 'M_wood'),
        (0.3, BREACH_HALF - 0.4, 1.0, 'M_wall'),
        (0.3, -BREACH_HALF + 0.4, 1.0, 'M_stone'),
        (RAM_CX + 2.0, WHEEL_Y, WHEEL_R, 'M_iron'),
        (RAM_CX - 2.0, -WHEEL_Y, WHEEL_R, 'M_wood'),
        (RAM_CX, 0.0, WALL_TOP_SHED + 1.0, 'M_wood'),
        (-0.6, 0.6, 0.4, 'M_wood'),
        (-0.6, -0.6, 0.4, 'M_iron'),
    ]
    for i, (x, y, z, mat) in enumerate(spots):
        m = MB()
        s = 0.3 + ((i * 37) % 10) / 20
        box(m, (0, 0, 0), (s * 1.2, s * 0.5, s * 0.6), mat, 'debris', jitter=s * 0.3, seed=800 + i)
        obj = to_object(f'ram_debris_{i:02d}', m, mats, 900 + i)
        obj.location = Vector((x, y, z))
        rng = random.Random(1000 + i)
        obj.rotation_euler = (rng.random() * TAU, rng.random() * TAU, rng.random() * TAU)
        obj.parent = root
    return root


# ---------------------------------------------------------------- scene, export
def reset_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def export(objs):
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, 'ram.blend'), compress=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT_DIR, 'ram.glb'), export_format='GLB',
        export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_apply=True,
        export_yup=True, export_materials='EXPORT', export_image_format='AUTO',
        use_visible=False, export_animations=False)


def main():
    reset_scene()
    mats = build_materials()
    states = []
    for s in range(4):
        m = build_state(s)
        states.append(to_object(f'ram_s{s}', m, mats, 1000 + s))
        print(f'ram_s{s}: {len(m.f)} faces, {sum(len(f) - 2 for f in m.f)} tris', flush=True)
    debris = build_debris(mats)
    for o in states[1:]:
        o.hide_set(True)
    export(states + [debris])
    print('exported', os.path.join(OUT_DIR, 'ram.glb'), flush=True)


main()
