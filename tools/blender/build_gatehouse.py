"""Build the FORTRESS GATEHOUSE (the defender's structure at a TERRITORY stage) in Blender and
export it. Midfield keeps the tall single-keep castle (tools/blender/build_castle.py); at a
territory stage the defender instead fights at the outer wall of their fortress, so this reads as
a WIDE WALL: two squat round flanking towers + a crenellated curtain wall + a raised gate tower
(barbican), lower and broader than the castle's keep.

Run from the repo root:
    "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" -b --factory-startup ^
        --python tools/blender/build_gatehouse.py

Writes models/gatehouse/gatehouse.blend and models/gatehouse/gatehouse.glb.
Concept art: brand/concepts/gatehouse_v1.png (the structure), brand/concepts/territory_v1.png
(the stage, gatehouse on the far right at the game's actual camera angle).

Same conventions as tools/blender/build_castle.py / build_jar.py (helpers are copied, not
imported, because those scripts build on import):
    Blender +X = away from the court, +Y = toward the game camera, +Z = up.
    Origin = the gate line on the lane's centre line; the rails are at Blender y = +-8.0.
    The game places this at the lane end at scale 0.9 and MIRRORS it in X for the red side.
    The camera is fixed, orthographic, 30 deg above the ground, looking along Blender -Y (it sits
    on the +Y side). Faces whose normals point along +-X are edge-on and never seen -- so the
    curtain wall (thin in X, long in Y) mainly reads via its TOP silhouette + crenellations, and
    all gate detail (arch, portcullis, banners, torches) is built as explicit flat polygons whose
    normal is +Y, not as a box face, so it faces the camera head-on regardless of the underlying
    wall's thin X profile.

Exported scene graph:
    gatehouse_s0..gatehouse_s3  one joined mesh per damage state: pristine, battered, breached, ruined
    gatehouse_debris            empty; children are loose chunks (stone blocks, a roof piece, a
                                 plank) for the crumble beat
Materials (looked up by name in the game, reusing the castle's names where they mean the same
thing): M_keep (tower_stone.png, the round towers), M_wall (castle_wall.png, curtain wall +
barbican), M_roof_team (roof_tiles pixel texture, neutral grey, team-tinted -- tower roofs),
M_cloth_team (neutral light grey, team-tinted -- banners), M_wood (procedural wood planks --
doors, beams), M_iron (portcullis lattice, studs, brackets), M_dark (recesses, interiors, char),
M_window (warm; the game makes it glow -- arrow slits), M_flame (warm; the game makes it glow --
torches).
"""
import bpy, math, random, os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT_DIR = os.path.join(ROOT, 'models', 'gatehouse')
TEX_DIR = os.path.join(ROOT, 'textures')

TILE = 1.6
TAU = math.tau

# ---------------------------------------------------------------- layout (Blender units)
# SPECTACLE SCALE: same size class as the castle (~12 tall), not a delicate miniature -- chunky,
# toy-like, oversized proportions throughout (big simple faceted volumes, fat bases, oversized
# merlons/torches/banners, stubby wide-cone roofs, no thin members).
#
# PLAY-AREA RULE (hard constraint, learned from an in-game check): the defending wizard stands at
# the gate line and nothing tall may sit at Blender x < -0.3 (the court side of the gate line) or
# it visually invades the play area / overlaps the character. All tall mass sits at x >= 0.
#
# Composition (matches how build_castle.py avoids the camera's Y/Z screen-coupling: keep the
# things ON the rails SHORT, put the TALL spectacle mass further back in +X, off the rails):
#   - Rail bastions: short, fat drum towers AT y=+-LANE_HALF, x ~ BASTION_X (small, near the gate
#     line) -- like the castle's own drum bastions, just much chunkier per the new art direction.
#   - Curtain wall: thick, x from ~0.15 to ~2.3, rail to rail with a gap in the middle.
#   - Gate towers: the tall spectacle pair, set well back in +X (x ~ GATE_TOWER_X) at y = +-
#     GATE_HALF_Y (inside the wall gap, not on the rails) -- this is the "big twin-towered
#     gatehouse block" the wall opens onto, clearly taller/fatter than the rail bastions.
#   - Gate bridge: a chunky block joining the two gate towers over the actual opening, plus the
#     arch/portcullis face mounted at the wall's near (court-facing) plane between them.
LANE_HALF = 8.0                     # rail centre line; the wall closes the lane end here (fixed --
                                     # matches the game's rails, never rescale this one)
WALL_X0, WALL_X1 = 0.15, 2.35       # curtain wall spans this X range (thickness ~2.2)
WALL_CX = (WALL_X0 + WALL_X1) / 2
WALL_THICK = WALL_X1 - WALL_X0
WALL_H = 6.2                        # curtain wall pristine top height
GATE_HALF_Y = 3.3                   # half-width of the central gap; also the gate towers' |y|
BASTION_X = 2.35                    # rail bastion centre X. A full 360deg drum this fat (radius
                                     # ~2.3) centred much closer to 0 would dip its own court-
                                     # facing hemisphere past x=-0.3 regardless of the "x~0-0.8"
                                     # guideline (radius alone forces that); centring it inside the
                                     # curtain wall's own thickness (WALL_X0..WALL_X1) keeps every
                                     # vertex above 1 unit tall on the correct side of the gate line
                                     # while still reading as "the bastion sits right on the wall".
BASTION_R = 2.35                    # rail bastion drum radius (fat, spec: 2.2-2.6)
GATE_TOWER_X = 3.35                 # gate tower centre X (well back in +X, off the rails)
GATE_TOWER_R = 2.45                 # gate tower drum radius (fat, spec: 2.2-2.6)
BRIDGE_X0, BRIDGE_X1 = 2.05, 4.65   # gate-top bridge X span (overlaps/merges into both wall + towers)
BRIDGE_H0 = 7.6                     # gate bridge top, pristine (big block joining the two towers)


# ---------------------------------------------------------------- textures & materials
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


def roof_tiles(x, y):
    # Scalloped storybook shingles (from build_castle.py), neutral grey so the game can tint them.
    row, yy = divmod(y, 8)
    xx = (x + (4 if row % 2 else 0)) % 8
    edge = abs(xx - 3.5) / 3.5
    if yy < 2 and edge > 0.72:
        return (0.28, 0.28, 0.30)
    if yy == 0:
        return (0.34, 0.34, 0.36)
    v = 0.60 + 0.30 * (yy / 7.0) - 0.10 * edge
    return (v, v, v * 1.02)


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


MAT_ORDER = ['M_keep', 'M_wall', 'M_roof_team', 'M_cloth_team', 'M_wood', 'M_iron', 'M_dark',
             'M_window', 'M_flame']


def build_materials():
    return {
        'M_keep': make_mat('M_keep', load_image('tower_stone.png')),
        'M_wall': make_mat('M_wall', load_image('castle_wall.png')),
        'M_roof_team': make_mat('M_roof_team', pixel_image('roof_tiles_gh', 32, 32, roof_tiles)),
        'M_cloth_team': make_mat('M_cloth_team', color=(0.85, 0.85, 0.85, 1)),
        'M_wood': make_mat('M_wood', pixel_image('wood_planks_gh', 32, 32, wood_planks)),
        'M_iron': make_mat('M_iron', color=(0.24, 0.23, 0.25, 1)),
        'M_dark': make_mat('M_dark', color=(0.10, 0.08, 0.07, 1)),
        'M_window': make_mat('M_window', color=(1.0, 0.72, 0.32, 1)),
        'M_flame': make_mat('M_flame', color=(1.0, 0.75, 0.35, 1)),
    }


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
          cap_top=False, smooth=True, flip=False, skip=()):
    """Revolve (radius, z) rings around `center`. skip: (ring, side) faces to leave out."""
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
            if (k, i) in skip:
                continue
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
        top = rings[-1]
        idx = top[::-1] if flip else top
        m.quad_planar(idx, mat, tag)
    return rings


def box(m, center, size, mat, tag, rot_z=0.0, tilt=(0.0, 0.0), jitter=0.0, seed=0, top_jag=None,
        batter=0.0):
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
    d = (p1 - p0).normalized()
    a = d.cross(Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))).normalized() * t / 2
    b = d.cross(a).normalized() * t / 2
    ring0 = [m.vert(p0 + a + b), m.vert(p0 - a + b), m.vert(p0 - a - b), m.vert(p0 + a - b)]
    ring1 = [m.vert(p1 + a + b), m.vert(p1 - a + b), m.vert(p1 - a - b), m.vert(p1 + a - b)]
    for k in range(4):
        j = (k + 1) % 4
        m.quad_planar([ring0[k], ring0[j], ring1[j], ring1[k]], mat, tag)
    m.quad_planar(ring0[::-1], mat, tag)
    m.quad_planar(ring1, mat, tag)


def poly(m, pts, mat, tag, facing, smooth=False):
    """Flat polygon from world points, wound so its normal points along `facing`."""
    n = (pts[1] - pts[0]).cross(pts[2] - pts[0])
    if n.dot(facing) < 0:
        pts = pts[::-1]
    idx = [m.vert(p) for p in pts]
    m.quad_planar(idx, mat, tag, smooth)


def cyl_point(a_deg, z, r, center):
    a = math.radians(a_deg)
    return Vector((center.x + r * math.cos(a), center.y + r * math.sin(a), z))


def jag(n, amp, seed, base=0.0):
    rng = random.Random(seed)
    return [base + (rng.random() - 0.5) * 2 * amp for _ in range(n)]


def merlon_ring(m, center, radius, z, count, seed, mat, missing=(), rot=0.0, size=(0.62, 0.85),
                hrange=(0.85, 1.25)):
    """Oversized, chunky merlons (toy-castle proportions, not delicate crenellation)."""
    rng = random.Random(seed)
    for i in range(count):
        h = hrange[0] + rng.random() * (hrange[1] - hrange[0])
        tilt = ((rng.random() - 0.5) * 0.1, (rng.random() - 0.5) * 0.1)
        if i in missing:
            continue
        a = rot + TAU * i / count
        c = (center.x + radius * math.cos(a), center.y + radius * math.sin(a), z + h / 2)
        box(m, c, (size[0], size[1], h), mat, 'stone', rot_z=a, tilt=tilt, jitter=0.06, seed=seed + i)
        box(m, (center.x + radius * math.cos(a), center.y + radius * math.sin(a), z - 0.16),
            (size[0] * 0.75, size[1] * 1.15, 0.32), mat, 'stone', rot_z=a,
            seed=seed + i + 1000)                                             # corbel bracket


def wall_merlons(m, x, y0, y1, z, seed, lost=(), spacing=1.15, size=(0.6, 0.8), hrange=(0.8, 1.15)):
    """A crenellated line of big, chunky merlons along Y at a fixed X (curtain wall / bridge top)."""
    n = max(1, round((y1 - y0) / spacing))
    rng = random.Random(seed)
    for i in range(n + 1):
        y = y0 + (y1 - y0) * i / n
        h = hrange[0] + rng.random() * (hrange[1] - hrange[0])
        tilt = ((rng.random() - 0.5) * 0.08, (rng.random() - 0.5) * 0.08)
        if i in lost:
            continue
        box(m, (x, y, z + h / 2), (size[0], size[1], h), 'M_wall', 'stone', tilt=tilt, jitter=0.05,
            seed=seed + i)
        box(m, (x, y, z - 0.16), (size[0] * 0.7, size[1] * 1.2, 0.32), 'M_wall', 'stone',
            seed=seed + i + 1000)


def rubble(m, center, count, spread, height, seed, mats=('M_keep', 'M_wall')):
    rng = random.Random(seed)
    for i in range(count):
        ang = rng.random() * TAU
        d = spread * math.sqrt(rng.random())
        s = 0.2 + rng.random() * 0.3
        z = max(0.0, height * (1 - d / spread)) * rng.random() + s * 0.35
        c = (center[0] + d * math.cos(ang), center[1] + d * math.sin(ang), z)
        box(m, c, (s * 1.3, s, s * 0.8), mats[i % len(mats)], 'rubble', rot_z=rng.random() * TAU,
            tilt=(rng.random() - 0.5, rng.random() - 0.5), jitter=s * 0.45, seed=seed * 100 + i)


# ---------------------------------------------------------------- parts: rail bastions (small,
# stay off the play area -- never anything tall at x < -0.3)
TOWER_SIDES = 18


def rail_bastion(m, side, s):
    """Short, fat drum bastion AT the rail (y=+-LANE_HALF), close to the gate line -- same idea as
    the castle's own small drum bastions, just much chunkier. side: +1 / -1."""
    c = Vector((BASTION_X, side * LANE_HALF, 0))
    drum = [(1.85, 0.0), (2.05, 0.35), (2.35, 0.55), (2.30, 1.6), (2.15, 2.6), (2.05, 3.3)]
    lathe(m, drum, TOWER_SIDES, c, 'M_keep', 'stone', jitter=0.03, seed=200 + (1 if side > 0 else 0))
    lathe(m, [(2.05, 3.15), (2.28, 3.28), (2.05, 3.35)], TOWER_SIDES, c, 'M_keep', 'stone',
          seed=205 + (1 if side > 0 else 0), smooth=False)

    merlon_missing = set()
    if s == 1:
        merlon_missing = {3}
    elif s >= 2:
        merlon_missing = {1, 3, 7}
    merlon_ring(m, c, 1.7, 3.35, 10, 260 + (1 if side > 0 else 0), 'M_wall', merlon_missing,
                rot=0.1, size=(0.56, 0.76), hrange=(0.75, 1.05))

    # Stubby wide cone -- a cartoon witch-hat roof, not a spike.
    roof = [(1.75, 3.6), (1.55, 3.8), (0.9, 4.6), (0.35, 5.05), (0.0, 5.3)]
    lathe(m, roof, TOWER_SIDES, c, 'M_roof_team', 'roof', jitter=0.03, seed=220, cap_top=True)
    apex = c + Vector((0, 0, 5.3))
    lathe(m, [(0.0, 0.0), (0.14, 0.2), (0.0, 0.5)], 4, apex, 'M_wood', 'wood', seed=230, smooth=False)

    if s < 3:
        for z in (1.15, 2.05):
            p = cyl_point(88, z, 2.15, c)
            t, up, out = Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))
            poly(m, [p - t * 0.14 - up * 0.4, p + t * 0.14 - up * 0.4, p + t * 0.13 + up * 0.4,
                     p - t * 0.13 + up * 0.4], 'M_dark', 'dark', out)
            p2 = p + out * 0.02
            poly(m, [p2 - t * 0.08 - up * 0.33, p2 + t * 0.08 - up * 0.33, p2 + t * 0.07 + up * 0.33,
                     p2 - t * 0.07 + up * 0.33], 'M_window', 'window', out)

    top = cyl_point(90, 2.7, 2.15, c)
    banner_cloth(m, top.x, c.y + 0.02, 2.7, 1.0, 1.7, torn=(s >= 1 and side > 0),
                 seed=240 + (1 if side > 0 else 0))

    if s >= 2:
        rubble(m, (c.x - 0.3, c.y + 0.35 * side), 5, 0.95, 0.55, 750 + (1 if side > 0 else 0))


# ---------------------------------------------------------------- parts: gate towers (the tall,
# fat spectacle mass -- set well back off the rails, never at x < -0.3)
def gate_tower(m, side, s):
    """side: +1 / -1, at y = side*GATE_HALF_Y, x = GATE_TOWER_X. The +Y-side tower (side>0) takes
    the roof damage, matching the single-focused-breach story the rest of the structure tells."""
    c = Vector((GATE_TOWER_X, side * GATE_HALF_Y, 0))
    drum = [(2.1, 0.0), (2.35, 0.45), (2.75, 0.75), (2.7, 3.3), (2.55, 5.6), (2.45, 7.8)]
    lathe(m, drum, TOWER_SIDES, c, 'M_keep', 'stone', jitter=0.03, seed=280 + (1 if side > 0 else 0))
    lathe(m, [(2.45, 7.6), (2.75, 7.75), (2.45, 7.8)], TOWER_SIDES, c, 'M_keep', 'stone',
          seed=285 + (1 if side > 0 else 0), smooth=False)

    damaged_roof = side > 0
    merlon_missing = set()
    if s == 1:
        merlon_missing = {4}
    elif s >= 2:
        merlon_missing = {1, 4, 9} if side > 0 else {7}
    if not (damaged_roof and s == 3):
        merlon_ring(m, c, 2.1, 7.8, 12, 300 + (1 if side > 0 else 0), 'M_wall', merlon_missing,
                    rot=0.12, size=(0.72, 1.0), hrange=(1.1, 1.5))

    if damaged_roof and s == 3:
        rubble(m, (c.x, c.y), 12, 1.5, 1.3, 720, mats=('M_keep', 'M_roof_team'))
        beam(m, c + Vector((-0.45, 0.3, 8.1)), c + Vector((0.75, -0.2, 9.9)), 0.24, 'M_wood', 'char')
    else:
        # Stubby wide cone -- fat base relative to height, a cartoon roof not a needle spire.
        roof = [(2.5, 8.1), (2.2, 8.45), (1.35, 10.1), (0.62, 11.5), (0.0, 12.0)]
        jt, skip = None, ()
        if damaged_roof and s == 2:
            jt = jag(TOWER_SIDES, 0.8, 310, base=-0.25)
            skip = {(2, 5), (2, 6), (2, 7)}
        lathe(m, roof, TOWER_SIDES, c, 'M_roof_team', 'roof', jitter=0.025, seed=320, jag_top=jt,
              skip=skip, cap_top=not skip)
        if damaged_roof and s == 2:
            rubble(m, (c.x - 0.3, c.y - 0.6 * side), 7, 0.95, 0.6, 730)
        apex = c + Vector((0, 0, 12.0))
        lathe(m, [(0.0, 0.0), (0.2, 0.3), (0.0, 0.65)], 4, apex, 'M_wood', 'wood', seed=330,
              smooth=False)

    if s < 3:
        for z in (3.2, 5.4):
            p = cyl_point(88, z, 2.68, c)
            t, up, out = Vector((1, 0, 0)), Vector((0, 0, 1)), Vector((0, 1, 0))
            poly(m, [p - t * 0.17 - up * 0.5, p + t * 0.17 - up * 0.5, p + t * 0.16 + up * 0.5,
                     p - t * 0.16 + up * 0.5], 'M_dark', 'dark', out)
            p2 = p + out * 0.02
            poly(m, [p2 - t * 0.1 - up * 0.42, p2 + t * 0.1 - up * 0.42, p2 + t * 0.09 + up * 0.42,
                     p2 - t * 0.09 + up * 0.42], 'M_window', 'window', out)

    top = cyl_point(90, 6.4, 2.72, c)
    banner_cloth(m, top.x, c.y + 0.02, 6.4, 1.5, 3.1, torn=(s >= 1 and side > 0),
                 seed=340 + (1 if side > 0 else 0))


# ---------------------------------------------------------------- parts: curtain wall
def curtain_wall(m, s):
    runs = [('pos', GATE_HALF_Y, LANE_HALF - 0.02), ('neg', -LANE_HALF + 0.02, -GATE_HALF_Y)]
    for name, y0, y1 in runs:
        breach = (name == 'pos' and s >= 2)
        if breach:
            span = y1 - y0
            cuts = [y0, y0 + span * 0.30, y0 + span * 0.66, y1]
            tops = [WALL_H, (2.6 if s == 2 else 1.3), WALL_H - 0.15]
        elif s == 3:
            cuts = [y0, y1]
            tops = [3.0 if name == 'pos' else 3.4]
        else:
            cuts = [y0, y1]
            tops = [WALL_H]
        for k, top in enumerate(tops):
            sy0, sy1 = cuts[k], cuts[k + 1]
            broken = top < WALL_H - 0.3
            top_jag = jag(4, 0.4, hash((name, k, s)) % 1000) if broken else None
            box(m, (WALL_CX, (sy0 + sy1) / 2, top / 2 + 0.35),
                (WALL_THICK, sy1 - sy0 - 0.04, top - 0.35), 'M_wall', 'stone',
                seed=30 + k + (10 if name == 'pos' else 0), top_jag=top_jag, batter=0.16,
                jitter=0.04 if broken else 0.0)
        if s < 3:
            lost = set()
            n_est = max(1, round((y1 - y0) / 1.15))
            if s == 1:
                lost = {n_est // 3}
            elif s == 2:
                lost = {n_est // 4, n_est // 2}
                if breach:
                    for i in range(n_est + 1):
                        yy = y0 + (y1 - y0) * i / n_est
                        if cuts[1] <= yy <= cuts[2]:
                            lost.add(i)
            # Pull the merlon line back from the gate-adjacent end: a short plain stretch of wall
            # there gives the gate towers' own crenellations room to read instead of crowding them.
            my0, my1 = (y0 + 1.1, y1) if name == 'pos' else (y0, y1 - 1.1)
            # A broad walkway band: big merlons on BOTH edges of the thick wall top.
            wall_merlons(m, WALL_X0 + 0.35, my0, my1, WALL_H, 70 + (1 if name == 'pos' else 0), lost,
                         spacing=1.15)
            wall_merlons(m, WALL_X1 - 0.35, my0, my1, WALL_H, 90 + (1 if name == 'pos' else 0), lost,
                         spacing=1.15)
            # Buttress piers along the run (top + tiny +-Y-normal end caps read; bulk of their
            # mass is silhouette).
            n_b = max(1, round((y1 - y0) / 1.6))
            for i in range(n_b + 1):
                yy = y0 + (y1 - y0) * i / n_b
                if breach and cuts[1] - 0.3 <= yy <= cuts[2] + 0.3:
                    continue
                box(m, (WALL_X1 + 0.32, yy, WALL_H * 0.42), (0.62, 0.55, WALL_H * 0.84 - 0.1),
                    'M_wall', 'stone', batter=0.2, jitter=0.03,
                    seed=110 + i + (5 if name == 'pos' else 0))
        if s >= 2:
            mid = (y0 + y1) / 2 if not breach else (cuts[1] + cuts[2]) / 2
            rubble(m, (WALL_CX, mid), 8 if s == 2 else 16, 1.4, 0.9,
                   400 + (1 if name == 'pos' else 0))
        if s == 3:
            rubble(m, (WALL_CX, y0 + (y1 - y0) * 0.2), 6, 1.2, 0.7,
                   420 + (1 if name == 'pos' else 0))
            rubble(m, (WALL_CX, y0 + (y1 - y0) * 0.8), 6, 1.2, 0.7,
                   430 + (1 if name == 'pos' else 0))


# ---------------------------------------------------------------- parts: gate bridge (the big
# chunky block joining the two gate towers over the actual opening) + the arch/portcullis face
def gate_bridge(m, s):
    core_top = BRIDGE_H0 if s < 2 else (5.6 if s == 2 else 3.3)
    broken = s >= 2
    top_jag = jag(4, 0.4, 510 + s) if broken else None
    bx = (BRIDGE_X0 + BRIDGE_X1) / 2
    box(m, (bx, 0, core_top / 2), (BRIDGE_X1 - BRIDGE_X0, GATE_HALF_Y * 2 - 0.1, core_top),
        'M_wall', 'stone', seed=500, top_jag=top_jag, batter=0.14, jitter=0.03 if broken else 0.0)

    if s < 3:
        lost = {1} if s >= 1 else set()
        wall_merlons(m, BRIDGE_X0 + 0.4, -GATE_HALF_Y + 0.35, GATE_HALF_Y - 0.35, core_top, 540,
                     lost, spacing=0.9, size=(0.68, 0.95), hrange=(1.0, 1.4))
    else:
        rubble(m, (bx, 0.0), 20, 1.7, 1.3, 550)

    gate_face(m, s, core_top)


def gate_face(m, s, bridge_top):
    # The arch's plane sits at a fixed Y (must stay a Y-normal flat feature to be camera-visible,
    # same rule as everywhere else) -- centred between the two gate towers (y=0), proud in X near
    # where the curtain wall meets the bridge, so it reads as the gate "between them".
    ax = BRIDGE_X0 + 0.55
    y0 = 0.0
    w = 2.6
    jamb_h = 3.6
    rise = 0.95
    base_z = 0.15
    apex_z = base_z + jamb_h + rise

    # Stone surround (chunky voussoir fan tracing the arch, like the castle's door rivets).
    steps = 17
    for k in range(steps):
        t = math.pi * k / (steps - 1)
        dx = -math.cos(t) * (w / 2 + 0.24)
        cz = base_z + jamb_h + math.sin(t) * (rise + 0.24)
        if s >= 2 and k in ({4, 12} if s == 2 else set(range(1, 16))):
            continue
        box(m, (ax + dx, y0 - 0.02, cz), (0.4, 0.4, 0.4), 'M_wall', 'stone', seed=600 + k)
    for side in (-1, 1):
        for j, zc in enumerate((base_z + jamb_h * 0.27, base_z + jamb_h * 0.73)):
            box(m, (ax + side * (w / 2 + 0.24), y0 - 0.02, zc), (0.46, 0.46, jamb_h / 2 - 0.05),
                'M_wall', 'stone', seed=610 + side * 3 + j)

    # A stone apron/threshold (paved footing) in front of the gate, toward the court.
    if s < 3:
        rng = random.Random(680)
        for i in range(18):
            axp = ax - 2.6 + rng.random() * 2.4
            ayp = -2.6 + rng.random() * 5.2
            sz = 0.5 + rng.random() * 0.3
            box(m, (axp, ayp, -0.03), (sz, sz * (0.8 + 0.3 * rng.random()), 0.14), 'M_wall',
                'paving', rot_z=rng.random() * TAU, jitter=0.04, seed=690 + i)

    # Dark recess (the opening).
    void = [Vector((ax - w / 2, y0, base_z)), Vector((ax + w / 2, y0, base_z)),
            Vector((ax + w / 2, y0, base_z + jamb_h)), Vector((ax, y0, apex_z)),
            Vector((ax - w / 2, y0, base_z + jamb_h))]
    poly(m, void, 'M_dark', 'dark', Vector((0, 1, 0)))

    yy = y0 + 0.04
    if s < 3:
        # Iron-studded double doors, set slightly proud of the dark recess.
        gap = 0.03 if s < 2 else 0.3                  # bent portcullis: leaves don't quite meet
        bend = 0.0 if s < 2 else 0.22
        for side in (-1, 1):
            x0, x1 = ax + side * gap / 2, ax + side * (w / 2 - 0.08)
            dz = bend if (s >= 2 and side > 0) else 0.0
            pts = [Vector((x0, yy, base_z)), Vector((x1, yy - dz * 0.3, base_z)),
                   Vector((x1, yy - dz, base_z + jamb_h - 0.08)),
                   Vector((x0, yy, base_z + jamb_h - 0.08))]
            poly(m, pts, 'M_wood', 'wood', Vector((0, 1, 0)))
            rng = random.Random(620 + side)
            for _ in range(10):
                rx = x0 + (x1 - x0) * rng.random()
                rz = base_z + 0.3 + (jamb_h - 0.6) * rng.random()
                box(m, (rx, yy + 0.05 - dz * 0.4, rz), (0.14, 0.14, 0.14), 'M_iron', 'iron',
                    seed=630)
            if s < 2:
                beam(m, Vector((x0, yy + 0.04, base_z + jamb_h * 0.3)),
                     Vector((x1, yy + 0.04, base_z + jamb_h * 0.75)), 0.1, 'M_iron', 'iron')
                beam(m, Vector((x0, yy + 0.04, base_z + jamb_h * 0.55)),
                     Vector((x1, yy + 0.04, base_z + jamb_h * 0.15)), 0.1, 'M_iron', 'iron')
            for hz in (base_z + 0.5, base_z + jamb_h - 0.7):
                box(m, (x0, yy + 0.08, hz), (0.14, 0.16, 0.22), 'M_iron', 'iron', seed=635)
        # A chain running up from the portcullis into the bridge above.
        for side in (-1, 1):
            beam(m, Vector((ax + side * (w / 2 + 0.08), yy, base_z + jamb_h - 0.15)),
                 Vector((ax + side * (w / 2 + 0.08), yy, base_z + jamb_h + rise + 0.7)), 0.08,
                 'M_iron', 'iron')
    else:
        rubble(m, (ax, y0 - 0.4), 10, 1.2, 0.75, 640)

    # Banners + torches flanking the arch (kept clear of x < -0.3: the play-area rule).
    torn = s >= 1
    banner_cloth(m, ax - w / 2 - 0.6, y0, bridge_top - 0.9, 0.85, 2.9, torn=(torn and s < 2),
                 seed=650)
    banner_cloth(m, ax + w / 2 + 0.6, y0, bridge_top - 0.9, 0.85, 2.9, torn=False, seed=651)
    torch(m, Vector((ax - w / 2 - 0.6, y0, 1.7)), seed=660)
    torch(m, Vector((ax + w / 2 + 0.6, y0, 1.7)), seed=661)


def banner_cloth(m, cx, y, z_top, w, h, torn, seed):
    hw = w / 2
    if not torn:
        pts2d = [(-hw, 0), (hw, 0), (hw, -0.72 * h), (0, -0.55 * h), (-hw, -0.72 * h)]
    else:
        rng = random.Random(seed)
        pts2d = [(-hw, 0), (hw, 0), (hw, -0.30 * h), (0.15 * hw, -0.62 * h),
                  (-0.2 * hw, -0.40 * h), (-hw, -0.5 * h)]
        pts2d = [(x, z * (0.7 + 0.5 * rng.random())) for x, z in pts2d]
    pts = [Vector((cx + dx, y, z_top + dz)) for dx, dz in pts2d]
    poly(m, pts, 'M_cloth_team', 'cloth', Vector((0, 1, 0)))
    back = [Vector((cx + dx, y - 0.03, z_top + dz)) for dx, dz in pts2d]
    poly(m, back, 'M_cloth_team', 'cloth', Vector((0, -1, 0)))
    beam(m, Vector((cx - hw - 0.1, y - 0.04, z_top + 0.06)),
         Vector((cx + hw + 0.1, y - 0.04, z_top + 0.06)), 0.08, 'M_wood', 'wood')


def torch(m, p, seed):
    # Oversized, chunky sconce -- reads as a clear landmark blob at this scale, not a thin stick.
    box(m, p + Vector((0, -0.09, 0)), (0.2, 0.3, 0.5), 'M_iron', 'iron', seed=seed)
    f = p + Vector((0, 0.04, 0.36))
    rng = random.Random(seed + 1)
    for ang in (0, 62, 124):
        t = Vector((math.cos(math.radians(ang)), 0, math.sin(math.radians(ang)) * 0.3 +
                    math.cos(math.radians(ang)) * 0.02))
        jt = rng.uniform(-0.05, 0.05)
        pts = [f - Vector((0, 0, 0.18)), f + t * 0.15, f + Vector((jt, 0, 0.4)), f - t * 0.15]
        n = t.cross(Vector((0, 1, 0)))
        poly(m, pts, 'M_flame', 'flame', n if n.length > 0.01 else Vector((1, 0, 0)))
        poly(m, pts[::-1], 'M_flame', 'flame', -(n if n.length > 0.01 else Vector((1, 0, 0))))


# ---------------------------------------------------------------- the gatehouse, per state
def build_state(s):
    m = MB()
    curtain_wall(m, s)
    gate_bridge(m, s)
    gate_tower(m, 1, s)
    gate_tower(m, -1, s)
    rail_bastion(m, 1, s)
    rail_bastion(m, -1, s)

    bx = (BRIDGE_X0 + BRIDGE_X1) / 2
    scorch = {
        0: [],
        1: [(Vector((bx, 0.5, BRIDGE_H0 - 0.8)), 1.8, 0.4)],
        2: [(Vector((bx, 0.5, 4.8)), 2.2, 0.5), (Vector((BRIDGE_X0 + 0.5, 0.5, 2.0)), 2.4, 0.45),
            (Vector((GATE_TOWER_X, GATE_HALF_Y, 7.0)), 2.0, 0.45)],
        3: [(Vector((bx, 0.0, 2.6)), 3.0, 0.6), (Vector((BRIDGE_X0 + 0.5, 0.0, 1.6)), 2.8, 0.55),
            (Vector((GATE_TOWER_X, GATE_HALF_Y, 2.5)), 2.4, 0.55),
            (Vector((BASTION_X, LANE_HALF, 2.0)), 1.6, 0.4)],
    }[s]
    return m, scorch


# ---------------------------------------------------------------- vertex-colour shading
def shade(co, tag, face_rand, scorch):
    if tag == 'window':
        return (1.0, 1.0, 1.0)
    if tag == 'flame':
        return (1.0, 1.0, 1.0)
    if tag in ('dark',):
        return (0.85, 0.85, 0.85)
    if tag == 'cloth':
        v = 0.82 + 0.18 * face_rand
        return (v, v, v)
    if tag == 'iron':
        v = 0.65 + 0.3 * face_rand
        return (v, v, v)
    v = 0.62 + 0.38 * min(1.0, co.z / 1.7)
    if tag == 'char':
        v *= 0.32
    if tag == 'rubble':
        v *= 0.82
    v *= 0.88 + 0.16 * face_rand
    for c, rad, k in scorch:
        d = (co - c).length
        if d < rad:
            v *= 1 - k * (1 - d / rad)
    warm = 0.5 + 0.5 * face_rand
    return (min(1, v * (1.0 + 0.03 * warm)), min(1, v), min(1, v * (0.95 - 0.04 * warm)))


def to_object(name, m, mats, scorch, seed):
    nv = len(m.v)
    bad = [f for f in m.f if any(i < 0 or i >= nv for i in f)]
    assert not bad, f'{name}: faces reference missing vertices: {bad[:3]}'
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
            c = shade(m.v[me.loops[li].vertex_index], m.tag[pi], fr, scorch)
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


# ---------------------------------------------------------------- debris for the crumble beat
def build_debris(mats):
    root = bpy.data.objects.new('gatehouse_debris', None)
    bpy.context.scene.collection.objects.link(root)
    rng = random.Random(800)
    bx = (BRIDGE_X0 + BRIDGE_X1) / 2
    spots = [(bx, 1.8, 4.2), (bx, 0.6, 5.6), (bx - 0.6, -0.6, 3.2), (bx, 3.6, 1.8),
             (bx + 0.4, 3.9, 3.2), (GATE_TOWER_X - 0.3, LANE_HALF - 2.2, 2.6),
             (GATE_TOWER_X + 0.4, GATE_HALF_Y - 0.5, 5.8), (WALL_X1 - 0.2, -LANE_HALF + 1.6, 2.4),
             (bx, 4.0, 6.4), (bx - 0.4, -2.0, 6.0), (bx, 5.6, 0.8)]
    for i, p in enumerate(spots):
        m = MB()
        s = 0.4 + rng.random() * 0.32
        box(m, (0, 0, 0), (s * 1.3, s, s * 0.85), 'M_keep' if i % 2 else 'M_wall', 'rubble',
            jitter=s * 0.5, seed=810 + i)
        obj = to_object(f'chunk_{i:02d}', m, mats, [], 900 + i)
        obj.location = p
        obj.parent = root
    # A roof-cone shard (from the gate tower that loses its roof).
    m = MB()
    box(m, (0, 0, 0), (1.3, 1.3, 0.75), 'M_roof_team', 'roof', jitter=0.18, seed=820, batter=-0.5)
    obj = to_object('roof_shard', m, mats, [], 921)
    obj.location = Vector((GATE_TOWER_X, GATE_HALF_Y - 0.6, 7.2))
    obj.rotation_euler = (0.3, 0.2, 0.6)
    obj.parent = root
    # A snapped door plank.
    m = MB()
    box(m, (0, 0, 0), (1.3, 0.24, 0.18), 'M_wood', 'wood', seed=822)
    obj = to_object('plank', m, mats, [], 922)
    obj.location = Vector((BRIDGE_X0 + 0.3, 0.4, 0.5))
    obj.rotation_euler = (0.1, 0.4, 1.1)
    obj.parent = root
    return root


# ---------------------------------------------------------------- scene, export
def reset_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def export(objs):
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, 'gatehouse.blend'), compress=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT_DIR, 'gatehouse.glb'), export_format='GLB',
        export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_apply=True,
        export_yup=True, export_materials='EXPORT', export_image_format='AUTO',
        use_visible=False, export_animations=False)


def main():
    reset_scene()
    mats = build_materials()
    states = []
    for s in range(4):
        m, scorch = build_state(s)
        states.append(to_object(f'gatehouse_s{s}', m, mats, scorch, 1000 + s))
        print(f'gatehouse_s{s}: {len(m.f)} faces, {sum(len(f) - 2 for f in m.f)} tris', flush=True)
    debris = build_debris(mats)
    for o in states[1:]:
        o.hide_set(True)
    export(states + [debris])
    print('exported', os.path.join(OUT_DIR, 'gatehouse.glb'), flush=True)


main()
