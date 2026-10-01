"""Build the siege CATAPULT (the ATTACKER's tower at a territory stage) in Blender and export it.

Run from the repo root:
    "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" -b --factory-startup ^
        --python tools/blender/build_catapult.py

Writes models/catapult/catapult.blend and models/catapult/catapult.glb. Concept art:
brand/concepts/catapult_v1.png (the catapult itself), brand/concepts/territory_v1.png (the stage
layout: the blue siege camp at top-left).

Same conventions as tools/blender/build_castle.py / build_jar.py (helpers are copied, not
imported, because those scripts build on import):
    Blender +X = away from the court, +Y = toward the game camera, +Z = up.
    Origin = the gate line on the lane's centre line; the red side mirrors this GLB in X at runtime.
    The camera is fixed 30 deg above the ground looking along Blender -Y, so faces pointing along
    +-X are edge-on and never seen. Detail goes on tops and the +Y (camera-facing) side.

SCALE + CHUNKINESS (revised after an in-game lit-scene check against build_castle.py): this is a
BIG hero prop, same size class as the castle (~12 tall, fills the lane end) -- arm tip ~10-11
tall, frame ~7-8 long in X, wheels ~2.2-2.6 diameter. Toy-cartoon proportions throughout: fat
timbers, oversized iron brackets, few big spokes, an oversized bucket + glowing boulder, thick
barricade logs/shields. Nothing thin -- a first pass with realistic-proportioned sticks read as an
invisible line drawing against the lit dirt ground (see the working log for the visibility-under-
the-real-camera lessons baked into this version: give camera-facing decoration real X/Z extent,
never rely on Y-extent, which is nearly the camera's view direction and collapses to ~0 width).

Exported scene graph:
    catapult_s0..catapult_s3  one joined mesh per damage state: pristine, battered, broken, wrecked
    catapult_debris           empty; children are loose chunks for the crumble beat
Materials (looked up by name in the game): M_wood, M_iron, M_rope, M_stone, M_cloth_team,
M_glow_team, M_dark. *_team materials are neutral grey and get tinted per side; M_glow_team also
gets made to glow (the magic boulder loaded in the sling). M_stone (tower_stone.png) is reused for
the plain (non-magic) boulders.
"""
import bpy, math, random, os
from mathutils import Vector, Matrix

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT_DIR = os.path.join(ROOT, 'models', 'catapult')
TEX_DIR = os.path.join(ROOT, 'textures')
TILE = 1.6
TAU = math.tau

# ---------------------------------------------------------------- layout (Blender units)
# Big hero prop: arm tip ~10.7 (castle roof apex is 12.3), frame ~7.4 long in X, wheels 2.4 dia --
# the same "size class" as the castle, not a small prop dwarfed by it.
LANE_HALF = 8.0                      # rail centre line
BAR_X = 0.05                          # barricade centre line (the "gate" the spells cross)
CX, CY = 3.6, 1.1                     # catapult body centre, behind the barricade
WHEEL_R = 1.2
TRACK_HALF = 1.3
AXLE_F_X = CX - 2.6
AXLE_B_X = CX + 2.6
RAIL_Z = WHEEL_R + 0.85                # bed rail height
BED_X0 = AXLE_F_X - 0.9
BED_X1 = AXLE_B_X + 1.3
PIVOT = Vector((CX, CY, 4.6))
ARM_LONG_TIP = Vector((1.9, 1.9, 11.0))              # sling end: high (10-11 tall); kept close to CY --
                                                       # the fixed camera's projection visually shortens
                                                       # tall things that lean far toward +Y (confirmed by
                                                       # a side-by-side render against the castle), so a
                                                       # big +Y lean here would read shorter than its true Z
ARM_SHORT_TIP = Vector((5.1, -1.7, 1.05))            # winch-rope end: low
LEG_L = Vector((CX - 1.5, CY - 1.4, RAIL_Z))
LEG_R = Vector((CX - 1.5, CY + 1.4, RAIL_Z))
BRACE_L = Vector((CX + 1.2, CY - 1.2, RAIL_Z))
BRACE_R = Vector((CX + 1.2, CY + 1.2, RAIL_Z))
WINCH_C = Vector((CX + 1.7, CY, RAIL_Z + 0.6))
PILE_C = Vector((CX - 1.0, CY - 4.4, 0.0))
CRATE_BASE = Vector((CX - 0.5, CY - 6.0, 0.0))
CANOPY_X0, CANOPY_X1 = CX + 0.5, CX + 3.0
CANOPY_Y0, CANOPY_Y1 = CY - 1.6, CY + 1.6
CANOPY_EAVE_Z = RAIL_Z + 0.55
CANOPY_RIDGE_Z = CANOPY_EAVE_Z + 1.6


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


MAT_ORDER = ['M_wood', 'M_iron', 'M_rope', 'M_stone', 'M_cloth_team', 'M_glow_team', 'M_dark']


def build_materials():
    return {
        'M_wood': make_mat('M_wood', pixel_image('wood_planks_cat', 32, 32, wood_planks)),
        'M_iron': make_mat('M_iron', color=(0.20, 0.19, 0.21, 1)),      # a touch darker: contrast vs lighter wood
        'M_rope': make_mat('M_rope', color=(0.82, 0.70, 0.48, 1)),      # pale tan so it pops
        'M_stone': make_mat('M_stone', load_image('tower_stone.png')),
        'M_cloth_team': make_mat('M_cloth_team', color=(0.85, 0.85, 0.85, 1)),
        'M_glow_team': make_mat('M_glow_team', color=(0.85, 0.85, 0.85, 1)),
        'M_dark': make_mat('M_dark', color=(0.10, 0.08, 0.07, 1)),
    }


# ---------------------------------------------------------------- mesh accumulator
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
    """Revolve (radius, z) rings around the Z axis through `center`."""
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


def box(m, center, size, mat, tag, rot_z=0.0, tilt=(0.0, 0.0), jitter=0.0, seed=0):
    rng = random.Random(seed)
    sx, sy, sz = (s / 2 for s in size)
    corners = []
    for dz in (-sz, sz):
        for (dx, dy) in ((-sx, -sy), (sx, -sy), (sx, sy), (-sx, sy)):
            p = Vector((dx, dy, dz))
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


def tilt_about(m, start, axis, angle_deg, pivot):
    mat3 = Matrix.Rotation(math.radians(angle_deg), 3, axis)
    xform(m, start, mat3, pivot - mat3 @ pivot)


def cyl_point(a_deg, z, r, center=Vector((0, 0, 0))):
    a = math.radians(a_deg)
    return Vector((center.x + r * math.cos(a), center.y + r * math.sin(a), z))


# ---------------------------------------------------------------- small round/flat parts
def boulder(m, center, r, tag, seed=0):
    """Faceted low-poly boulder; tag picks the material ('boulder_stone' or 'boulder_glow')."""
    mat = 'M_glow_team' if tag == 'boulder_glow' else 'M_stone'
    prof = [(0.0, -r), (r * 0.72, -r * 0.55), (r, 0.05 * r), (r * 0.66, r * 0.62), (0.0, r * 0.88)]
    lathe(m, prof, 8, center, mat, tag, jitter=0.14, seed=seed, smooth=False)


def wheel(m, hub, r, n_spokes, seed, thick=0.55):
    """A real 3D chunky toy wheel (axle along Y so it faces the fixed camera): a thick tire band
    (front + back + outer tread faces, not a flat cutout), a few FAT beam spokes, and a fat hub
    drum -- the flat zero-thickness version read as an invisible line under lit shading."""
    rng = random.Random(seed)
    rim_in = r * 0.66
    hub_r = r * 0.28
    sides = 16

    def ring(radius, yoff):
        return [hub + Vector((radius * math.cos(TAU * i / sides), yoff, radius * math.sin(TAU * i / sides)))
                for i in range(sides)]

    of, ob = ring(r, thick / 2), ring(r, -thick / 2)
    inf, inb = ring(rim_in, thick / 2), ring(rim_in, -thick / 2)
    for i in range(sides):
        j = (i + 1) % sides
        poly(m, [inf[i], of[i], of[j], inf[j]], 'M_iron', 'iron', Vector((0, 1, 0)))      # front tire face
        poly(m, [inb[j], ob[j], ob[i], inb[i]], 'M_iron', 'iron', Vector((0, -1, 0)))     # back tire face
        outn = (of[i] - hub); outn.y = 0
        poly(m, [of[i], ob[i], ob[j], of[j]], 'M_iron', 'iron', outn.normalized())        # tread (outer wall)
    for i in range(n_spokes):
        a = TAU * i / n_spokes + rng.uniform(-0.02, 0.02)
        d = Vector((math.cos(a), 0, math.sin(a)))
        p0 = hub + d * hub_r * 0.55
        p1 = hub + d * rim_in * 0.96
        beam(m, p0, p1, r * 0.34, 'M_wood', 'wood')             # fat 3D spoke, not a flat sliver
    hstart = len(m.v)
    lathe(m, [(hub_r, -thick * 0.65), (hub_r, thick * 0.65)], 10, Vector((0, 0, 0)), 'M_iron',
          'iron', cap_top=True, smooth=False)
    xform(m, hstart, Matrix.Rotation(math.radians(90), 3, 'X'), hub)


def bucket_and_load(m, tip, glowing, on_ground=False, boulder_r=0.95):
    """Oversized rope-sling bucket holding a big glowing boulder (the team-coloured focal point)."""
    BK = 2.8
    base = tip if on_ground else tip - Vector((0, 0, 0.42 * BK))
    lathe(m, [(0.05 * BK, 0.0), (0.30 * BK, 0.12 * BK), (0.34 * BK, 0.32 * BK), (0.32 * BK, 0.42 * BK)],
          8, base, 'M_wood', 'wood', smooth=False)
    for ang in (55, 235):
        p = base + Vector((0.26 * BK * math.cos(math.radians(ang)), 0.26 * BK * math.sin(math.radians(ang)),
                            0.4 * BK))
        beam(m, tip, p, 0.13, 'M_rope', 'rope')
    boulder(m, base + Vector((0, 0, boulder_r * 0.4)), boulder_r,
            'boulder_glow' if glowing else 'boulder_stone', 501)


def chevaux(m, y, seed, tag='wood'):
    """Cheval-de-frise unit: two thick sharpened logs crossing in a big X (spans ~1.6-2.0 in X --
    real area from the camera's raking angle, not a lean-in-place stake that collapses to a line)."""
    rng = random.Random(seed)
    h = rng.uniform(2.0, 2.6)
    span = rng.uniform(1.6, 2.0)
    cx = BAR_X + span * 0.3
    yj = rng.uniform(-0.12, 0.12)
    thick = 0.42
    base_a = Vector((cx - span / 2, y + yj, 0.0))
    tip_a = Vector((cx + span / 2, y + yj * 0.4, h))
    base_b = Vector((cx + span / 2, y - yj, 0.0))
    tip_b = Vector((cx - span / 2, y - yj * 0.4, h))
    for base, tip in ((base_a, tip_a), (base_b, tip_b)):
        d = (tip - base).normalized()
        beam(m, base, tip - d * 0.3, thick, 'M_wood', tag)
        lathe(m, [(thick * 0.55, 0.0), (thick * 0.15, 0.22), (0.0, 0.42)], 6, tip - Vector((0, 0, 0.42)),
              'M_wood', tag, smooth=False)
    # iron lashing where the logs cross
    box(m, Vector((cx, y, h * 0.5)), (0.32, 0.5, 0.24), 'M_iron', 'iron', seed=seed)


def stump(m, y, seed, tag='wood'):
    """A single broken-off log stub (what's left of a knocked-down chevaux unit)."""
    rng = random.Random(seed)
    h = rng.uniform(0.5, 1.0)
    lean = rng.uniform(0.12, 0.4)
    base = Vector((BAR_X, y, 0.0))
    tip = Vector((BAR_X - lean, y + rng.uniform(-0.15, 0.15), h))
    beam(m, base, tip, 0.4, 'M_wood', tag)


def mantlet(m, y, seed):
    """A big propped wooden pavise/shield: wide in X (the axis the camera actually shows), thin in
    Y, tall in Z -- built with real thickness so its top/side/face all contribute silhouette."""
    rng = random.Random(seed)
    w, h = rng.uniform(1.5, 1.8), rng.uniform(2.0, 2.4)
    thick = 0.4
    tilt = math.radians(10)
    cx = BAR_X + w * 0.12
    box(m, (cx, y, h / 2), (w, thick, h), 'M_wood', 'wood', tilt=(0.0, tilt), seed=seed)
    top = Vector((cx + h * math.sin(tilt), y, h * math.cos(tilt)))
    strut = Vector((cx + 0.85, y, 0.0))
    beam(m, strut, top, 0.24, 'M_wood', 'wood')
    for dx in (-w * 0.32, w * 0.32):
        box(m, Vector((cx + dx, y + 0.02, h * 0.55)), (0.32, 0.24, 0.32), 'M_iron', 'iron',
            seed=seed + int(dx * 10))


# ---------------------------------------------------------------- barricade (x ~ 0, rail to rail)
def barricade(m, s):
    n = 14
    gap_frac = {0: 0.0, 1: 0.18, 2: 0.45, 3: 0.80}[s]
    stump_frac = {0: 0.0, 1: 0.05, 2: 0.22, 3: 0.55}[s]
    for i in range(n):
        y = -LANE_HALF + (2 * LANE_HALF) * (i + 0.5) / n
        rng = random.Random(700 + i)
        roll = rng.random()
        is_mantlet = (i % 4 == 2)
        if roll < gap_frac:
            if roll < stump_frac:
                stump(m, y, 900 + i, tag='char' if s == 3 else 'wood')
            continue
        if is_mantlet:
            mantlet(m, y, 1000 + i)
        else:
            chevaux(m, y, 1100 + i, tag='char' if s == 3 else 'wood')


# ---------------------------------------------------------------- the catapult frame
def frame(m, s):
    start_all = len(m.v)
    missing_wheel = ('bl' if s >= 2 else None)
    wheel_defs = [
        ('fl', Vector((AXLE_F_X, CY - TRACK_HALF, WHEEL_R))),
        ('fr', Vector((AXLE_F_X, CY + TRACK_HALF, WHEEL_R))),
        ('bl', Vector((AXLE_B_X, CY - TRACK_HALF, WHEEL_R))),
        ('br', Vector((AXLE_B_X, CY + TRACK_HALF, WHEEL_R))),
    ]
    for i, (key, pos) in enumerate(wheel_defs):
        if key == missing_wheel:
            continue
        wheel(m, pos, WHEEL_R, 5, 800 + i)

    beam(m, Vector((AXLE_F_X, CY - TRACK_HALF - 0.15, WHEEL_R)),
         Vector((AXLE_F_X, CY + TRACK_HALF + 0.15, WHEEL_R)), 0.4, 'M_iron', 'iron')
    beam(m, Vector((AXLE_B_X, CY - TRACK_HALF - 0.15, WHEEL_R)),
         Vector((AXLE_B_X, CY + TRACK_HALF + 0.15, WHEEL_R)), 0.4, 'M_iron', 'iron')

    beam(m, Vector((BED_X0, CY - TRACK_HALF, RAIL_Z)), Vector((BED_X1, CY - TRACK_HALF, RAIL_Z)),
         0.62, 'M_wood', 'wood')
    beam(m, Vector((BED_X0, CY + TRACK_HALF, RAIL_Z)), Vector((BED_X1, CY + TRACK_HALF, RAIL_Z)),
         0.62, 'M_wood', 'wood')
    for xx in (BED_X0 + 0.5, CX, BED_X1 - 0.5):
        beam(m, Vector((xx, CY - TRACK_HALF, RAIL_Z)), Vector((xx, CY + TRACK_HALF, RAIL_Z)),
             0.46, 'M_wood', 'wood')
    box(m, (CX, CY, RAIL_Z + 0.2), (BED_X1 - BED_X0 - 0.6, TRACK_HALF * 2 + 0.2, 0.3), 'M_wood',
        'wood')
    # oversized bolt heads at the bed/axle junctions -- toy-chunky iron detail
    for xx in (AXLE_F_X, AXLE_B_X):
        for yy in (CY - TRACK_HALF, CY + TRACK_HALF):
            box(m, (xx, yy, RAIL_Z + 0.05), (0.3, 0.3, 0.22), 'M_iron', 'iron', seed=int(xx * 7 + yy))

    if s < 3:
        beam(m, LEG_L, PIVOT, 0.52, 'M_wood', 'wood')
        beam(m, LEG_R, PIVOT, 0.52, 'M_wood', 'wood')
        beam(m, BRACE_L, LEG_R.lerp(PIVOT, 0.55), 0.34, 'M_wood', 'wood')
        beam(m, BRACE_R, LEG_L.lerp(PIVOT, 0.55), 0.34, 'M_wood', 'wood')
        box(m, PIVOT, (1.0, 1.0, 0.75), 'M_iron', 'iron')
    else:
        collapsed = Vector((CX - 0.9, CY + 0.2, 1.5))
        beam(m, LEG_L, collapsed, 0.52, 'M_wood', 'char')
        beam(m, LEG_R, collapsed + Vector((0.3, 0.6, 0.0)), 0.52, 'M_wood', 'char')
        beam(m, BRACE_L, collapsed, 0.34, 'M_wood', 'char')

    # winch drum (lathe built along Z at the origin, rotated 90deg about X to lie along Y)
    wstart = len(m.v)
    lathe(m, [(0.7, -0.6), (0.7, 0.6)], 10, Vector((0, 0, 0)), 'M_rope', 'rope', smooth=False)
    xform(m, wstart, Matrix.Rotation(math.radians(90), 3, 'X'), WINCH_C)
    box(m, WINCH_C + Vector((0, -0.66, 0)), (1.15, 0.22, 1.15), 'M_iron', 'iron')
    box(m, WINCH_C + Vector((0, 0.66, 0)), (1.15, 0.22, 1.15), 'M_iron', 'iron')

    if s < 2:
        beam(m, PIVOT, ARM_LONG_TIP, 0.62, 'M_wood', 'wood')
        beam(m, PIVOT, ARM_SHORT_TIP, 0.46, 'M_wood', 'wood')
        if s == 1:
            mid = PIVOT.lerp(ARM_LONG_TIP, 0.42)
            n = (ARM_LONG_TIP - PIVOT).cross(Vector((0, 1, 0))).normalized() * 0.14
            poly(m, [mid - n, mid + n, mid + n + Vector((0, 0, 0.55)), mid - n + Vector((0.08, 0, 0.5))],
                 'M_dark', 'char', Vector((0, 1, 0.2)))
        beam(m, WINCH_C + Vector((0, 0, 0.6)), ARM_SHORT_TIP, 0.16, 'M_rope', 'rope')
        bucket_and_load(m, ARM_LONG_TIP, glowing=True)
    elif s == 2:
        snap = PIVOT.lerp(ARM_LONG_TIP, 0.5)
        beam(m, PIVOT, snap, 0.62, 'M_wood', 'wood')
        hang = snap + Vector((0.5, -0.25, -2.0))
        beam(m, snap, hang, 0.46, 'M_wood', 'char')
        beam(m, PIVOT, ARM_SHORT_TIP, 0.46, 'M_wood', 'wood')
    else:
        arm_base = Vector((CX - 2.6, CY + 2.0, 0.3))
        arm_tip_ground = arm_base + Vector((-3.2, 1.1, 0.5))
        beam(m, arm_base, arm_tip_ground, 0.55, 'M_wood', 'char')
        bucket_and_load(m, arm_tip_ground, glowing=False, on_ground=True, boulder_r=0.55)

    if s < 3:
        canopy(m, s)
        pennants(m, s)

    if s == 2:
        tilt_about(m, start_all, 'X', -9, Vector((AXLE_B_X, CY - TRACK_HALF, 0.0)))
        fstart = len(m.v)
        wheel(m, Vector((0, 0, 0)), WHEEL_R, 5, 850)
        target = Vector((AXLE_B_X - 0.55, CY - TRACK_HALF - 1.7, WHEEL_R * 0.2))
        xform(m, fstart, Matrix.Rotation(math.radians(92), 3, 'X'), target)
    elif s == 3:
        tilt_about(m, start_all, 'X', -15, Vector((AXLE_B_X, CY - TRACK_HALF, 0.0)))


def canopy(m, s):
    for (px, py) in ((CANOPY_X0, CANOPY_Y0), (CANOPY_X0, CANOPY_Y1),
                      (CANOPY_X1, CANOPY_Y0), (CANOPY_X1, CANOPY_Y1)):
        if s >= 2 and px == CANOPY_X1 and py == CANOPY_Y1:
            continue                                           # one post knocked away
        beam(m, Vector((px, py, RAIL_Z)), Vector((px, py, CANOPY_EAVE_Z)), 0.22, 'M_wood', 'wood')
    segs = 4
    skip = {0: set(), 1: {segs - 1}, 2: {segs - 2, segs - 1}}[s]
    for i in range(segs):
        if i in skip:
            continue
        xa = CANOPY_X0 + (CANOPY_X1 - CANOPY_X0) * i / segs
        xb = CANOPY_X0 + (CANOPY_X1 - CANOPY_X0) * (i + 1) / segs
        mat = 'M_cloth_team' if i % 2 == 0 else 'M_dark'
        ridge_a, ridge_b = Vector((xa, CY, CANOPY_RIDGE_Z)), Vector((xb, CY, CANOPY_RIDGE_Z))
        eave_na, eave_nb = Vector((xa, CANOPY_Y0, CANOPY_EAVE_Z)), Vector((xb, CANOPY_Y0, CANOPY_EAVE_Z))
        eave_fa, eave_fb = Vector((xa, CANOPY_Y1, CANOPY_EAVE_Z)), Vector((xb, CANOPY_Y1, CANOPY_EAVE_Z))
        poly(m, [eave_na, eave_nb, ridge_b, ridge_a], mat, 'cloth', Vector((0, -1, 0.4)))
        poly(m, [eave_fa, ridge_a, ridge_b, eave_fb], mat, 'cloth', Vector((0, 1, 0.4)))


def pennant(m, base, h, seed):
    """Flag flutters along X (the camera's clean screen-horizontal axis), not Y (nearly edge-on to
    the fixed camera) -- same fix as build_castle.py's roof flag / build_jar.py's banners."""
    rng = random.Random(seed)
    top = base + Vector((0, 0, h))
    beam(m, base, top, 0.22, 'M_wood', 'wood')
    flap = rng.uniform(-0.25, 0.25)
    pts = [top, top - Vector((0, 0, 1.3)), top + Vector((-2.1 + flap, 0.1, -0.55)),
           top + Vector((-1.25 + flap, 0.06, -1.05))]
    poly(m, pts, 'M_cloth_team', 'cloth', Vector((1, 0.3, 0.1)))


def pennants(m, s):
    if s >= 2:
        return
    pennant(m, LEG_R, 5.4 - 0.2 * s, 21)
    pennant(m, BRACE_R, 4.5 - 0.3 * s, 22)


def boulder_pile(m, s):
    if s < 2:
        offsets = [(-0.4, -0.3, 0.42), (0.38, -0.22, 0.42), (0.0, 0.38, 0.42), (-0.08, 0.0, 1.05),
                   (0.45, 0.3, 0.42)]
        for i, (dx, dy, dz) in enumerate(offsets):
            boulder(m, PILE_C + Vector((dx, dy, dz)), 0.45, 'boulder_stone', 900 + i)
    else:
        rng = random.Random(910)
        n = 6 if s == 2 else 4
        for i in range(n):
            ang, rad = rng.uniform(0, 360), rng.uniform(0.4, 3.2)
            p = cyl_point(ang, 0.38, rad, PILE_C)
            boulder(m, p, rng.uniform(0.32, 0.48), 'boulder_stone', 920 + i)


def crates(m, s):
    defs = {0: [(0.0, 0.0, 0.5, 0), (0.9, 0.08, 0.44, 18)],
            1: [(0.0, 0.0, 0.5, 4), (0.9, 0.15, 0.42, 30)],
            2: [(0.3, 0.38, 0.44, 40)],
            3: [(0.3, 0.45, 0.38, 55)]}[s]
    tag = 'char' if s == 3 else 'wood'
    for (dx, dy, sz, rot) in defs:
        box(m, CRATE_BASE + Vector((dx, dy, sz / 2)), (sz, sz, sz), 'M_wood', tag,
            rot_z=math.radians(rot))


# ---------------------------------------------------------------- the catapult, per state
def build_state(s):
    m = MB()
    barricade(m, s)
    frame(m, s)
    boulder_pile(m, s)
    crates(m, s)
    return m


# ---------------------------------------------------------------- vertex-colour shading
def shade(co, tag, fr):
    if tag in ('boulder_glow', 'cloth'):
        return (1.0, 1.0, 1.0)
    if tag == 'char':
        v = 0.16 + 0.10 * fr
        return (v, v * 0.92, v * 0.85)
    if tag == 'iron':
        v = 0.42 + 0.20 * fr                                  # darker than wood -- contrast, not camouflage
        return (v, v, v)
    if tag == 'rope':
        v = 0.92 + 0.08 * fr                                  # pale tan, near white so it pops
        return (v, v * 0.95, v * 0.82)
    if tag == 'wood':
        v = 0.82 + 0.24 * min(1.0, co.z / 3.0)                # bright floor -- lit scene darkens this a lot
        v *= 0.88 + 0.20 * fr
        warm = 0.5 + 0.5 * fr
        return (min(1, v * (1.0 + 0.05 * warm)), min(1, v), min(1, v * (0.82 - 0.05 * warm)))
    v = 0.6 + 0.36 * min(1.0, co.z / 3.0)                     # fallback (boulder_stone etc.)
    v *= 0.85 + 0.22 * fr
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
    root = bpy.data.objects.new('catapult_debris', None)
    bpy.context.scene.collection.objects.link(root)
    rng = random.Random(300)
    i = 0

    def add(name, m, loc, rot=(0, 0, 0)):
        nonlocal i
        obj = to_object(f'{name}_{i:02d}', m, mats, 400 + i)
        obj.location = Vector(loc)
        obj.rotation_euler = rot
        obj.parent = root
        i += 1

    m = MB(); wheel(m, Vector((0, 0, 0)), WHEEL_R, 5, 851)
    add('wheel', m, (CX + 1.5, CY - 4.4, 0.1), (math.radians(85), 0, 0.3))

    for k in range(4):
        m = MB(); stump(m, 0.0, 950 + k, tag='char')
        add('stake', m, (BAR_X + rng.uniform(-0.4, 0.6), rng.uniform(-6, 6), 0.0),
            (rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(0, TAU)))

    for k in range(2):
        m = MB()
        poly(m, [Vector((0, -0.9, 0)), Vector((0, 0.9, 0)), Vector((0.14, 0.9, 1.6)),
                 Vector((0.14, -0.9, 1.6))], 'M_wood', 'wood', Vector((1, 0, 0.2)))
        add('plank', m, (CX - 1.5 + k * 0.9, CY - 2.4 - k * 0.6, 0.0),
            (rng.uniform(0, TAU), rng.uniform(0, TAU), 0))

    m = MB(); boulder(m, Vector((0, 0, 0)), 0.5, 'boulder_stone', 502)
    add('boulder', m, (CX + 0.7, CY + 3.2, 0.45))

    for k in range(2):
        m = MB(); box(m, (0, 0, 0), (0.5, 0.46, 0.46), 'M_wood', 'char', seed=600 + k)
        add('crate', m, (CRATE_BASE.x + k * 0.6, CRATE_BASE.y - 1.0, 0.24),
            (0, 0, rng.uniform(0, TAU)))

    for k in range(3):
        m = MB(); beam(m, Vector((0, 0, 0)), Vector((1.5, 0.08, 0.12)), 0.28, 'M_wood', 'char')
        add('splinter', m, (CX - 0.3 + k * 0.5, CY + 1.6 - k * 0.8, 0.15 + k * 0.08),
            (rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5), rng.uniform(0, TAU)))

    m = MB()
    poly(m, [Vector((0, 0, 0)), Vector((0.85, 0.08, 0)), Vector((0.75, 0, 0.68)), Vector((-0.08, -0.08, 0.6))],
         'M_cloth_team', 'cloth', Vector((0, 0, 1)))
    add('canvas', m, (CX + 1.5, CY - 0.5, 0.08), (0.4, 0.2, 1.1))

    return root


# ---------------------------------------------------------------- scene, export
def reset_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def export(objs):
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, 'catapult.blend'), compress=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT_DIR, 'catapult.glb'), export_format='GLB',
        export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_apply=True,
        export_yup=True, export_materials='EXPORT', export_image_format='AUTO',
        use_visible=False, export_animations=False)


def main():
    reset_scene()
    mats = build_materials()
    states = []
    for s in range(4):
        m = build_state(s)
        states.append(to_object(f'catapult_s{s}', m, mats, 1000 + s))
        print(f'catapult_s{s}: {len(m.f)} faces, {sum(len(f) - 2 for f in m.f)} tris', flush=True)
    debris = build_debris(mats)
    for o in states[1:]:
        o.hide_set(True)
    export(states + [debris])
    print('exported', os.path.join(OUT_DIR, 'catapult.glb'), flush=True)


main()
