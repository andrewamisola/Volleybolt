"""Build the Volleybolt castle (FF9 storybook x PS1) in Blender and export it for the game.

Run from the repo root:
    "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" -b --factory-startup ^
        --python tools/blender/build_castle.py

Writes models/castle/castle.blend (open it to tweak by hand) and models/castle/castle.glb.
Preview every damage state from the game's exact camera in castle_viewer.html (served next to
index.html), which renders with the game's own engine.

Axes (Blender, Z up) -> Babylon, after the glTF loader's handedness flip:
    Blender +X  = away from the court (toward the backdrop)  -> Babylon -X for the BLUE castle
    Blender +Y  = toward the game camera                     -> Babylon -Z
    Blender +Z  = up                                         -> Babylon +Y
Origin = foot of the gate wall's centre line (the old procedural castle's `baseX, 0, 0`).
The red castle is this same GLB mirrored in X at runtime.

The game camera is fixed (30 deg above the ground, looking along Babylon +Z), so faces pointing
along +-X are edge-on and never seen. Like an FF9 pre-rendered set, detail goes on the tops and
the camera-facing (+Y) side.

Exported scene graph:
    castle_s0..castle_s3  one joined mesh per damage state: pristine, battered, breached, ruined
    castle_debris         empty; its children are loose chunks the game drops for the crumble beat
Materials (the game looks these up by name): M_keep, M_wall, M_roof_team, M_cloth_team, M_wood,
M_dark, M_window. *_team materials are neutral grey and get tinted blue/red in the game.
Shading (ground AO, grime, scorch, per-face variation) is baked into the COLOR_0 vertex colors;
the .blend wires textures straight into Base Color (what the glTF exporter recognises), so view
the vertex colors in Blender's viewport with Solid shading > Attribute.
"""
import bpy, math, random, sys, os
from mathutils import Vector

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT_DIR = os.path.join(ROOT, 'models', 'castle')
TEX_DIR = os.path.join(ROOT, 'textures')

TILE = 1.6          # world units per texture repeat (64px bricks -> chunky PS1 texels)
TAU = math.tau

# ---------------------------------------------------------------- layout (game units)
# The game centres the castle on the lane (setTowerOffset upZ 0) at 0.9 scale; the lane's rails sit
# at Babylon z = +-7.2, i.e. Blender y = +-8.0. The gate wall spans rail to rail, so the castle
# closes the whole lane end: no grass gaps at the rails, and every fireball visibly hits wall.
LANE_HALF = 8.0                     # rail centre line (Blender units)
KX, KY = 1.55, 1.26                 # keep centre (behind the gate wall, toward the camera)
KEEP_SIDES = 10
LEAN = Vector((0.032, -0.012, 0))   # keep leans away from the court, slightly away from camera
KEEP_PROFILE = [(2.10, 0.00), (2.10, 0.40), (1.88, 0.52), (1.84, 2.4),
                (1.90, 4.3), (1.80, 6.1), (1.70, 7.55)]          # batter base, belly, taper
WALL_X = 0.62                       # gate wall half-thickness (top); base is battered wider
WALL_H = 4.2
WALL_SEGS = [(-LANE_HALF, 1.0), (1.0, 4.4), (4.4, LANE_HALF)]  # Y ranges; the camera-side middle breaks
BREACH_Y = (WALL_SEGS[1][0] + WALL_SEGS[1][1]) / 2
BASTIONS = {'near': (Vector((-0.05, LANE_HALF, 0)), 4.75), 'far': (Vector((-0.05, -LANE_HALF, 0)), 4.35)}
HOARD_Z = (7.72, 8.55)
ROOF_PROFILE = [(2.62, 8.48), (2.24, 8.70), (1.38, 10.15), (0.62, 11.42), (0.0, 12.30)]


# ---------------------------------------------------------------- materials & textures
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
    # Scalloped storybook shingles, neutral grey so the game can tint them.
    row, yy = divmod(y, 8)
    xx = (x + (4 if row % 2 else 0)) % 8
    edge = abs(xx - 3.5) / 3.5              # 0 centre -> 1 tile edge
    if yy < 2 and edge > 0.72:              # rounded bottom corners -> scallop
        return (0.28, 0.28, 0.30)
    if yy == 0:
        return (0.34, 0.34, 0.36)
    v = 0.60 + 0.30 * (yy / 7.0) - 0.10 * edge
    return (v, v, v * 1.02)


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


_pave_rng = random.Random(21)
_pave_noise = [[_pave_rng.random() for _ in range(32)] for _ in range(32)]


def paving_stone(x, y):
    # Speckled beige-grey flagstone surface (the stones themselves are separate faces).
    n = 0.9 + 0.2 * _pave_noise[y][x]
    return (0.66 * n, 0.62 * n, 0.55 * n)


def make_mat(name, image=None, color=(1, 1, 1, 1)):
    m = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True                   # always on (and deprecated) from Blender 5
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value = 1.0
    bsdf.inputs['Metallic'].default_value = 0.0
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.0
    if image is not None:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = image
        tex.interpolation = 'Closest'       # -> glTF NEAREST sampler: crisp PS1 texels
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = color
    return m


def build_materials():
    mats = {
        'M_keep': make_mat('M_keep', load_image('tower_stone.png')),
        'M_wall': make_mat('M_wall', load_image('castle_wall.png')),
        'M_roof_team': make_mat('M_roof_team', pixel_image('roof_tiles', 32, 32, roof_tiles)),
        'M_cloth_team': make_mat('M_cloth_team', color=(0.85, 0.85, 0.85, 1)),
        'M_wood': make_mat('M_wood', load_image('wood_planks.png')),   # pixel-first, shared (tools/pixelate_textures.py)
        'M_dark': make_mat('M_dark', color=(0.10, 0.08, 0.07, 1)),
        'M_window': make_mat('M_window', color=(1.0, 0.72, 0.32, 1)),
        'M_paving': make_mat('M_paving', pixel_image('paving_stone', 32, 32, paving_stone)),
    }
    return mats


MAT_ORDER = ['M_keep', 'M_wall', 'M_roof_team', 'M_cloth_team', 'M_wood', 'M_dark', 'M_window',
             'M_paving']


# ---------------------------------------------------------------- mesh accumulator
class MB:
    """Accumulates polygons with per-loop UVs, a material and a shading tag per face."""

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
        """Face with world-planar UVs picked from its dominant axis (boxes, flat decals)."""
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


def lathe(m, profile, sides, center, mat, tag, lean=None, rot=0.0, jitter=0.0, seed=0,
          jag_top=None, cap_top=False, smooth=True, flip=False, skip=()):
    """Revolve (radius, z) rings around `center`. Returns the ring vertex indices.
    skip: (ring, side) faces to leave out, e.g. to punch a hole in a roof."""
    rng = random.Random(seed)
    lean = lean or Vector((0, 0, 0))
    rings = []
    for k, (r, z) in enumerate(profile):
        ring = []
        for i in range(sides):
            a = rot + TAU * i / sides
            rr = r * (1 + jitter * (rng.random() - 0.5)) if r > 0 else 0
            zz = z + (jag_top[i] if (jag_top and k == len(profile) - 1) else 0)
            zz += jitter * 0.6 * (rng.random() - 0.5) if 0 < k < len(profile) - 1 else 0
            p = Vector((center.x + rr * math.cos(a), center.y + rr * math.sin(a), zz)) + lean * zz
            ring.append(m.vert(p))
            if r == 0:
                break
        rings.append(ring)
    for k in range(len(rings) - 1):
        r_avg = (profile[k][0] + profile[k + 1][0]) / 2 or 0.3
        circ = TAU * max(r_avg, 0.3) / TILE
        z0, z1 = profile[k][1] / TILE, profile[k + 1][1] / TILE
        lo, hi = rings[k], rings[k + 1]
        for i in range(sides):
            if (k, i) in skip:
                continue
            j = (i + 1) % sides
            u0, u1 = circ * i / sides, circ * (i + 1) / sides
            if len(hi) == 1:                 # apex on top
                idx = [lo[i], lo[j], hi[0]]
                uvs = [(u0, z0), (u1, z0), ((u0 + u1) / 2, z1)]
            elif len(lo) == 1:               # point at the bottom (corbels, finial)
                idx = [lo[0], hi[j], hi[i]]
                uvs = [((u0 + u1) / 2, z0), (u1, z1), (u0, z1)]
            else:
                idx = [lo[i], lo[j], hi[j], hi[i]]
                uvs = [(u0, z0), (u1, z0), (u1, z1), (u0, z1)]
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
    """Axis box (optionally yaw/tilt/jittered). top_jag: 4 z offsets for the top corners."""
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
        y1, z1 = p.y * cx - p.z * sx_, p.y * sx_ + p.z * cx          # tilt about X
        x2, z2 = p.x * cy + z1 * sy_, -p.x * sy_ + z1 * cy           # tilt about Y
        x3, y3 = x2 * cz - y1 * sz_, x2 * sz_ + y1 * cz              # yaw about Z
        idx.append(m.vert(Vector((x3, y3, z2)) + Vector(center)))
    b0, b1, b2, b3, t0, t1, t2, t3 = idx
    for f in ([b3, b2, b1, b0], [t0, t1, t2, t3], [b0, b1, t1, t0], [b1, b2, t2, t1],
              [b2, b3, t3, t2], [b3, b0, t0, t3]):
        m.quad_planar(f, mat, tag)
    return idx


def beam(m, p0, p1, t, mat, tag):
    """Square timber of thickness t running from p0 to p1 (rafters, snapped poles)."""
    d = (p1 - p0).normalized()
    a = d.cross(Vector((0, 0, 1)) if abs(d.z) < 0.9 else Vector((1, 0, 0))).normalized() * t / 2
    b = d.cross(a).normalized() * t / 2
    ring0 = [m.vert(p0 + a + b), m.vert(p0 - a + b), m.vert(p0 - a - b), m.vert(p0 + a - b)]
    ring1 = [m.vert(p1 + a + b), m.vert(p1 - a + b), m.vert(p1 - a - b), m.vert(p1 + a - b)]
    L = (p1 - p0).length / TILE
    for k in range(4):
        j = (k + 1) % 4
        if mat == 'M_wood':
            # u along the beam (the texture's grain), v across one board (rows are 8px = 0.25)
            v0 = 0.25 * k + 0.01
            m.face([ring0[k], ring0[j], ring1[j], ring1[k]], [(0, v0), (0, v0 + 0.23), (L, v0 + 0.23), (L, v0)], mat, tag)
        else:
            m.quad_planar([ring0[k], ring0[j], ring1[j], ring1[k]], mat, tag)
    m.quad_planar(ring0[::-1], mat, tag)
    m.quad_planar(ring1, mat, tag)


def roof_point(a_deg, z):
    """Point on the roof cone (ROOF_PROFILE, leaning with the keep) at angle a and height z."""
    for (r0, z0), (r1, z1) in zip(ROOF_PROFILE, ROOF_PROFILE[1:]):
        if z <= z1:
            r = r0 + (r1 - r0) * (z - z0) / max(z1 - z0, 1e-6)
            break
    a = math.radians(a_deg)
    return Vector((KX + r * math.cos(a), KY + r * math.sin(a), z)) + LEAN * z


def paving(m, x0, x1, y0, y1, z, cell, seed):
    """Flagstone floor: a dark mortar bed with irregular stone quads on top of it."""
    m.quad_planar([m.vert((x0, y0, z - 0.02)), m.vert((x1, y0, z - 0.02)), m.vert((x1, y1, z - 0.02)),
                   m.vert((x0, y1, z - 0.02))], 'M_dark', 'dark')
    rng = random.Random(seed)
    nx, ny = max(1, round((x1 - x0) / cell)), max(1, round((y1 - y0) / cell))
    cw, ch = (x1 - x0) / nx, (y1 - y0) / ny
    for i in range(nx):
        off = (rng.random() - 0.5) * 0.3 * ch                  # stagger rows like laid stone
        for j in range(ny):
            ax, bx = x0 + i * cw + 0.05, x0 + (i + 1) * cw - 0.05
            ay = max(y0, y0 + j * ch + off) + 0.05
            by = min(y1, y0 + (j + 1) * ch + off) - 0.05
            if by - ay < 0.15:
                continue
            j4 = [(rng.random() - 0.5) * 0.08 for _ in range(4)]
            zz = z + (rng.random() - 0.5) * 0.03
            m.quad_planar([m.vert((ax + j4[0], ay, zz)), m.vert((bx, ay + j4[1], zz)),
                           m.vert((bx + j4[2], by, zz)), m.vert((ax, by + j4[3], zz))],
                          'M_paving', 'paving')


def worn_path(m, seed):
    """Flagstones laid straight on the lane: dense along a worn line from the keep door to the near
    rail, thinning out (sparser, smaller, darker, more sunken) into grass. Plus a light scatter around
    the keep's footing. A beaten-path fade instead of a hard-edged slab."""
    rng = random.Random(seed)
    cell = 0.6
    fx0, fx1, fy0, fy1 = KX - 2.15, KX + 2.15, KY - 2.4, KY + 2.4     # keep footing rectangle
    x_lo, x_hi = 0.85, KX + 3.2                                      # never spill past the wall
    y_lo, y_hi = KY - 3.4, LANE_HALF - 0.15
    nx, ny = int((x_hi - x_lo) / cell), int((y_hi - y_lo) / cell)
    for gx in range(nx):
        for gy in range(ny):
            x = x_lo + (gx + 0.5) * cell + (rng.random() - 0.5) * 0.25
            y = y_lo + (gy + 0.5) * cell + (rng.random() - 0.5) * 0.25
            if fx0 < x < fx1 and fy0 < y < fy1:
                continue                                              # under the footing
            path = max(0.0, 1.65 - abs(x - KX) / 1.35) if y > fy1 - 0.2 else 0.0
            dx = max(fx0 - x, 0, x - fx1)
            dy = max(fy0 - y, 0, y - fy1)
            ring = max(0.0, 0.95 - math.hypot(dx, dy) / 1.2)
            dens = min(1.0, max(path, ring)) * (0.85 + 0.3 * rng.random())
            if rng.random() > dens:
                continue
            size = cell * (0.55 + 0.55 * min(1.0, dens)) - 0.04      # core stones nearly touch
            rot = rng.random() * TAU
            # Edge stones sink lower. Kept >= 0.2 above the ground: the lane's dirt-road decal
            # draws with a polygon offset that paints over anything lying closer to the floor.
            z = 0.2 + 0.06 * min(1.0, dens)
            pts = []
            for k in range(5):                                        # irregular pentagon stone
                a = rot + TAU * k / 5
                r = size / 2 * (0.75 + 0.35 * rng.random())
                pts.append(m.vert((x + r * math.cos(a), y + r * math.sin(a), z)))
            m.quad_planar(pts, 'M_paving', 'paving' if dens > 0.75 else 'paving_worn')


def keep_r(z):
    """Keep radius at height z (piecewise linear through KEEP_PROFILE)."""
    for (r0, z0), (r1, z1) in zip(KEEP_PROFILE, KEEP_PROFILE[1:]):
        if z <= z1:
            return r0 + (r1 - r0) * (z - z0) / max(z1 - z0, 1e-6)
    return KEEP_PROFILE[-1][0]


def keep_surface(a_deg, z, out=0.03):
    """Point on the faceted keep surface at angle a (deg) and height z, plus its facet frame."""
    a = math.radians(a_deg)
    step = TAU / KEEP_SIDES
    fc = (math.floor(a / step) + 0.5) * step          # centre angle of the facet containing a
    apothem = keep_r(z) * math.cos(step / 2)
    r = apothem / math.cos(a - fc) + out
    p = Vector((KX + r * math.cos(a), KY + r * math.sin(a), z)) + LEAN * z
    n = Vector((math.cos(fc), math.sin(fc), 0))
    t = Vector((-math.sin(fc), math.cos(fc), 0))
    return p, n, t


def decal(m, a_deg, z, w, h, mat, tag, arch=True, out=0.03):
    """Flat window/door shape on the keep facet at angle a: rectangle with a pointed top."""
    p, n, t = keep_surface(a_deg, z, out)
    up = Vector((0, 0, 1))
    pts = [p - t * w / 2, p + t * w / 2, p + t * w / 2 + up * h, ]
    if arch:
        pts += [p + up * (h + w * 0.45)]
    pts += [p - t * w / 2 + up * h]
    idx = [m.vert(q) for q in pts]
    m.face(idx, [(0, 0)] * len(idx), mat, tag)


def crack(m, path, width=0.07):
    """Dark crack strip following (angle_deg, z) points over the keep surface."""
    pts = [keep_surface(a, z, 0.035) for a, z in path]
    left, right = [], []
    for k, (p, n, t) in enumerate(pts):
        nxt = pts[min(k + 1, len(pts) - 1)][0]
        prv = pts[max(k - 1, 0)][0]
        d = (nxt - prv).normalized()
        side = d.cross(n).normalized() * width * (0.5 if k in (0, len(pts) - 1) else 1.0)
        left.append(m.vert(p + side))
        right.append(m.vert(p - side))
    for k in range(len(pts) - 1):
        idx = [left[k], right[k], right[k + 1], left[k + 1]]
        p0 = m.v[idx[0]]
        n = (m.v[idx[1]] - p0).cross(m.v[idx[2]] - p0)
        if n.dot(pts[k][1]) < 0:
            idx = idx[::-1]
        m.face(idx, [(0, 0)] * 4, 'M_dark', 'crack')


def rubble(m, center, count, spread, height, seed, mats=('M_keep', 'M_wall')):
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


def merlon_ring(m, center, radius, z, count, seed, mat, missing=(), rot=0.0):
    rng = random.Random(seed)
    for i in range(count):
        h = 0.48 + rng.random() * 0.3
        tilt = ((rng.random() - 0.5) * 0.12, (rng.random() - 0.5) * 0.12)
        if i in missing:
            continue
        a = rot + TAU * i / count
        c = (center.x + radius * math.cos(a), center.y + radius * math.sin(a), z + h / 2)
        box(m, c, (0.36, 0.52, h), mat, 'stone', rot_z=a, tilt=tilt, jitter=0.05, seed=seed + i)


def jag(n, amp, seed, base=0.0):
    rng = random.Random(seed)
    return [base + (rng.random() - 0.5) * 2 * amp for _ in range(n)]


# ---------------------------------------------------------------- the castle, per state
def build_state(s):
    """Return (MB, scorch list) for damage state s (0 pristine .. 3 ruined)."""
    m = MB()

    # Keep footing (crisp paved stone base), plus a worn flagstone path from the door down to the
    # near rail that thins out into the grass, so the keep is anchored to the lane edge without a
    # hard-edged slab.
    box(m, (1.55, KY, 0.23), (4.3, 4.8, 0.46), 'M_wall', 'stone', seed=2)
    worn_path(m, seed=3)
    paving(m, 1.55 - 2.15, 1.55 + 2.15, KY - 2.4, KY + 2.4, 0.47, 0.8, seed=4)

    # ---- gate wall: three battered segments; the middle one breaks.
    wall_tops = {0: [WALL_H] * 3, 1: [WALL_H] * 3, 2: [WALL_H, 2.35, WALL_H - 0.15],
                 3: [3.05, 1.35, 3.25]}[s]
    for k, ((y0, y1), top) in enumerate(zip(WALL_SEGS, wall_tops)):
        broken = top < WALL_H
        top_jag = jag(4, 0.35, 40 + k) if broken else None
        box(m, (0, (y0 + y1) / 2, top / 2 + 0.4), (WALL_X * 2, y1 - y0, top - 0.4), 'M_wall',
            'stone', seed=30 + k, top_jag=top_jag, batter=0.1, jitter=0.03 if broken else 0.0)
    # Walkway lip on the inner edge and merlons along the court edge (their tops are what reads).
    if s < 3:
        box(m, (WALL_X - 0.12, 0, WALL_H + 0.12), (0.24, 2 * LANE_HALF - 0.2, 0.24), 'M_wall', 'stone',
            seed=50)
    merlon_ys = [-LANE_HALF + 0.9 + 0.9 * i for i in range(17)]
    lost = {0: set(), 1: {3, 11}, 2: {3, 8, 11}, 3: set(range(17))}[s]
    rng = random.Random(60)
    for i, y in enumerate(merlon_ys):
        h = 0.5 + rng.random() * 0.3
        tilt = ((rng.random() - 0.5) * 0.14, (rng.random() - 0.5) * 0.14)
        if i in lost or (s == 2 and WALL_SEGS[1][0] < y < WALL_SEGS[1][1]):
            continue
        box(m, (-WALL_X + 0.16, y, WALL_H + h / 2), (0.34, 0.5, h), 'M_wall', 'stone',
            tilt=tilt, jitter=0.05, seed=70 + i)

    # ---- drum bastions at both ends of the wall.
    for name, (c, h) in BASTIONS.items():
        broken = (name == 'near' and s >= 2) or (name == 'far' and s == 3)
        top = h - (1.6 if broken else 0.0)
        prof = [(1.14, 0.0), (1.14, 0.42), (1.0, 0.54), (0.96, top - 0.2), (1.04, top)]
        lathe(m, prof, 9, c, 'M_wall', 'stone', jitter=0.03, seed=hash(name) % 97,
              jag_top=jag(9, 0.4, 80) if broken else None, cap_top=True)
        if not broken:
            missing = {1, 5} if (s >= 1 and name == 'near') else set()
            merlon_ring(m, c, 0.84, top, 8, 90 if name == 'near' else 91, 'M_wall', missing,
                        rot=0.2)
        else:
            rubble(m, (c.x - 0.6, c.y + 0.3), 7, 1.0, 0.5, 95 if name == 'near' else 96)

    # ---- the keep.
    if s < 3:
        prof = KEEP_PROFILE + [(1.70, 7.95)]
        lathe(m, prof, KEEP_SIDES, Vector((KX, KY, 0)), 'M_keep', 'keep', lean=LEAN,
              jitter=0.025, seed=5, cap_top=True)
        # String course: a thin stone band that breaks up the tall shaft.
        lathe(m, [(1.93, 4.95), (1.97, 5.05), (1.97, 5.2), (1.9, 5.3)], KEEP_SIDES,
              Vector((KX, KY, 0)), 'M_keep', 'keep', lean=LEAN, seed=6)
    else:
        top = 5.3
        prof = KEEP_PROFILE[:5] + [(1.86, top)]
        jt = jag(KEEP_SIDES, 0.75, 7)
        outer = lathe(m, prof, KEEP_SIDES, Vector((KX, KY, 0)), 'M_keep', 'keep', lean=LEAN,
                      jitter=0.025, seed=5, jag_top=jt)
        inner_prof = [(1.5, 4.1), (1.5, top)]
        inner = lathe(m, inner_prof, KEEP_SIDES, Vector((KX, KY, 0)), 'M_dark', 'interior',
                      lean=LEAN, jag_top=[j - 0.1 for j in jt], flip=True)
        o, i_ = outer[-1], inner[-1]
        for k in range(KEEP_SIDES):
            j = (k + 1) % KEEP_SIDES
            m.quad_planar([o[k], i_[k], i_[j], o[j]], 'M_keep', 'keep')
        m.quad_planar(inner[0], 'M_dark', 'interior')                      # rubble floor
        rubble(m, (KX, KY), 9, 1.2, 0.6, 12)
        # Charred beams jutting from the broken top.
        for k, (a, tilt) in enumerate(((40, 0.5), (160, -0.4), (250, 0.7))):
            p, n, _ = keep_surface(a, 4.7, -0.2)
            box(m, p + n * 0.4, (1.6, 0.18, 0.18), 'M_wood', 'char', rot_z=math.radians(a),
                tilt=(0, tilt), seed=130 + k)

    # Door on the camera-facing facet (a=90), with a stone arch.
    decal(m, 90, 0.52, 1.05, 1.25, 'M_dark', 'dark', out=0.03)
    decal(m, 90, 0.52, 0.8, 1.2, 'M_wood', 'wood', out=0.05)
    for k in range(7):
        t = math.pi * k / 6
        p, n, tan = keep_surface(90, 0.52 + 1.25, 0.07)
        c = p + tan * (-math.cos(t) * 0.66) + Vector((0, 0, math.sin(t) * 0.55))
        box(m, c, (0.24, 0.26, 0.26), 'M_keep', 'keep', rot_z=math.radians(90), seed=140 + k)
    # Windows (one warm-lit while the keep stands).
    windows = [(126, 3.3, False), (54, 3.9, False), (90, 3.4, False)]
    if s < 3:
        windows += [(90, 6.2, s < 2), (54, 6.4, False), (126, 6.0, s == 0)]
    for a, z, lit in windows:
        decal(m, a, z, 0.42, 0.62, 'M_window' if lit else 'M_dark', 'window' if lit else 'dark')

    # Side turret, corbelled out toward the camera/court: storybook asymmetry.
    ta = math.radians(140)
    tz0 = 4.6
    tc = Vector((KX + (keep_r(5.5) + 0.35) * math.cos(ta), KY + (keep_r(5.5) + 0.35) * math.sin(ta),
                 0)) + LEAN * 5.5
    if s < 3:
        lathe(m, [(0.1, tz0), (0.62, tz0 + 0.75)], 8, tc, 'M_keep', 'keep', seed=150)
        t_top = 7.25 if s < 2 else 6.4
        lathe(m, [(0.6, tz0 + 0.75), (0.58, t_top)], 8, tc, 'M_keep', 'keep', seed=151,
              jag_top=jag(8, 0.25, 152) if s >= 2 else None, cap_top=True)
        decal_p = tc + Vector((0.6 * math.cos(math.radians(100)), 0.6 * math.sin(math.radians(100)),
                               6.1))
        idx = [m.vert(decal_p + Vector(d)) for d in ((-0.08, 0.02, -0.25), (0.08, 0.02, -0.25),
                                                     (0.08, 0.02, 0.25), (-0.08, 0.02, 0.25))]
        m.face(idx, [(0, 0)] * 4, 'M_dark', 'dark')
        if s < 2:
            lathe(m, [(0.8, t_top), (0.74, t_top + 0.1), (0.0, t_top + 1.35)], 8, tc,
                  'M_roof_team', 'roof', seed=153)

    # Timber hoarding ring under the roof, on corbel brackets.
    if s < 3:
        missing = {0: set(), 1: {3}, 2: {2, 3, 7}}[s]
        rh = keep_r(8.1) + 0.24
        n_seg = KEEP_SIDES
        rng = random.Random(160)
        for k in range(n_seg):
            a = TAU * (k + 0.5) / n_seg
            tilt = (rng.random() - 0.5) * 0.06
            ctr = Vector((KX + rh * math.cos(a), KY + rh * math.sin(a), sum(HOARD_Z) / 2)) + \
                LEAN * 8.1
            w = 2 * rh * math.tan(math.pi / n_seg) * 1.04
            if k not in missing:
                box(m, ctr, (0.16, w, HOARD_Z[1] - HOARD_Z[0]), 'M_wood', 'wood', rot_z=a,
                    tilt=(tilt, 0), seed=170 + k)
            bp = Vector((KX + (rh - 0.2) * math.cos(a), KY + (rh - 0.2) * math.sin(a), 7.55)) + \
                LEAN * 7.55
            box(m, bp, (0.5, 0.16, 0.3), 'M_wood', 'wood', rot_z=a, seed=180 + k)

    # Roof: oversized flared cone with finial + team pennant.
    if s < 3:
        # Breached: a hole punched through the camera-facing slope (the roof is the biggest thing
        # the game camera sees, so this is where damage reads) showing the dark attic + rafters.
        hole = {(1, 1), (1, 2), (2, 2)} if s == 2 else ()
        lathe(m, ROOF_PROFILE, KEEP_SIDES, Vector((KX, KY, 0)), 'M_roof_team', 'roof', lean=LEAN,
              jitter=0.02, seed=190, skip=hole)
        if s == 2:
            attic = [(r * 0.9, z - 0.05) for r, z in ROOF_PROFILE]
            lathe(m, attic, KEEP_SIDES, Vector((KX, KY, 0)), 'M_dark', 'interior', lean=LEAN,
                  flip=True, smooth=False)
            for a, z1 in ((54, 10.1), (72, 11.3), (90, 11.3), (108, 11.3)):
                beam(m, roof_point(a, 8.72), roof_point(a, z1), 0.13, 'M_wood', 'wood')
        apex = Vector((KX, KY, 12.30)) + LEAN * 12.30
        lathe(m, [(0.0, 12.22), (0.16, 12.42), (0.0, 12.68)], 4, apex - Vector((0, 0, apex.z)),
              'M_wood', 'wood', seed=191, smooth=False)
        if s < 2:
            box(m, apex + Vector((0, 0, 0.8)), (0.07, 0.07, 1.0), 'M_wood', 'wood', seed=192)
            tip = apex + Vector((0, 0, 1.28))
            flag = [tip, tip - Vector((0, 0, 0.42)), tip + Vector((-0.5, 0.12, -0.26)),
                    tip + Vector((-0.95, 0.06, -0.18))]
            f = [m.vert(p) for p in flag]
            g = [m.vert(p) for p in flag]            # back side gets its own verts (no dup faces)
            m.face([f[0], f[1], f[2]], [(0, 1), (0, 0), (0.5, 0.4)], 'M_cloth_team', 'cloth')
            m.face([f[0], f[2], f[3]], [(0, 1), (0.5, 0.4), (1, 0.5)], 'M_cloth_team', 'cloth')
            m.face([g[0], g[2], g[1]], [(0, 1), (0.5, 0.4), (0, 0)], 'M_cloth_team', 'cloth')
            m.face([g[0], g[3], g[2]], [(0, 1), (1, 0.5), (0.5, 0.4)], 'M_cloth_team', 'cloth')
        elif s == 2:
            box(m, apex + Vector((-0.2, 0, 0.4)), (0.07, 0.07, 0.6), 'M_wood', 'wood',
                tilt=(0, -0.9), seed=193)

    # ---- battle damage that accumulates.
    cracks = {
        1: [[(84, 7.2), (88, 6.6), (85, 6.0), (91, 5.5)], [(118, 2.6), (122, 2.1), (119, 1.5)]],
        2: [[(84, 7.2), (88, 6.6), (85, 6.0), (91, 5.5), (87, 4.7)],
            [(118, 3.0), (122, 2.1), (119, 1.3)], [(60, 5.9), (57, 5.2), (62, 4.6)],
            [(100, 4.6), (104, 4.0), (101, 3.3)]],
        3: [[(118, 3.0), (122, 2.1), (119, 1.3)], [(60, 4.6), (57, 3.9), (62, 3.1)],
            [(100, 4.4), (104, 3.8), (101, 2.9)], [(76, 2.5), (72, 1.9), (75, 1.2)]],
    }.get(s, [])
    for path in cracks:
        crack(m, path)
    if s >= 2:
        rubble(m, (-0.9, BREACH_Y), 10 if s == 2 else 16, 1.3, 0.7, 200)     # at the wall breach
    if s == 3:
        rubble(m, (-0.7, -3.5), 10, 1.1, 0.6, 201)
        rubble(m, (KX - 1.2, KY + 2.0), 12, 1.3, 0.8, 202)

    scorch = {0: [],
              1: [(Vector((KX, KY + 1.9, 6.0)), 1.3, 0.35), (Vector((KX - 0.4, KY + 2.2, 9.3)), 1.4, 0.45)],
              2: [(Vector((KX, KY + 1.9, 6.0)), 1.5, 0.45), (Vector((0, BREACH_Y, 3.2)), 2.0, 0.5),
                  (Vector((KX, KY + 2.2, 9.6)), 1.9, 0.5)],
              3: [(Vector((KX, KY + 1.9, 4.2)), 2.2, 0.55), (Vector((0, BREACH_Y, 2.0)), 2.6, 0.6),
                  (Vector((0, -3.0, 2.5)), 1.6, 0.5)]}[s]
    return m, scorch


# ---------------------------------------------------------------- vertex-colour shading
def shade(co, tag, face_rand, scorch):
    if tag == 'window':
        return (1.0, 1.0, 1.0)
    if tag in ('crack', 'dark'):
        return (0.85, 0.85, 0.85)
    if tag in ('paving', 'paving_worn'):                  # lit flagstones, no ground occlusion
        v = 0.84 + 0.22 * face_rand
        if tag == 'paving_worn':
            v *= 0.8                                      # scuffed, dirtier stones at the path edge
        for c, rad, k in scorch:
            d = (co - c).length
            if d < rad:
                v *= 1 - k * (1 - d / rad)
        return (min(1, v * 1.02), min(1, v), min(1, v * 0.95))
    v = 0.64 + 0.36 * min(1.0, co.z / 1.7)                 # ground-contact occlusion
    if tag == 'keep' and 6.9 < co.z < 8.0:
        v *= 0.72                                          # shadow under the hoarding/roof
    if tag == 'interior':
        v *= 0.42
    if tag == 'char':
        v *= 0.3
    if tag == 'rubble':
        v *= 0.82
    v *= 0.88 + 0.16 * face_rand                          # faceted hand-painted variation
    for c, rad, k in scorch:
        d = (co - c).length
        if d < rad:
            v *= 1 - k * (1 - d / rad)
    warm = 0.5 + 0.5 * face_rand
    return (min(1, v * (1.0 + 0.03 * warm)), min(1, v), min(1, v * (0.95 - 0.04 * warm)))


def to_object(name, m, mats, scorch, seed):
    # Drop degenerate faces (repeated vertices / < 3 corners): from_pydata can crash on them.
    nv = len(m.v)
    bad = [f for f in m.f if any(i < 0 or i >= nv for i in f)]
    assert not bad, f'{name}: faces reference missing vertices: {bad[:3]}'
    keep = [i for i, f in enumerate(m.f) if len(f) >= 3 and len(set(f)) == len(f)]
    if len(keep) != len(m.f):
        print(f'  {name}: dropped {len(m.f) - len(keep)} degenerate faces', flush=True)
        for attr in ('f', 'uv', 'mat', 'smooth', 'tag'):
            setattr(m, attr, [getattr(m, attr)[i] for i in keep])
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in m.v], [], m.f)
    for key in MAT_ORDER:
        me.materials.append(mats[key])
    # Create both layers BEFORE touching either: adding a layer can reallocate the mesh's
    # attribute storage, and a stale layer reference then writes into freed memory (native crash).
    me.uv_layers.new(name='UVMap')
    me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    rng = random.Random(seed)
    uvs, cols = [], []
    for pi, poly in enumerate(me.polygons):
        fr = rng.random()
        for j, li in enumerate(poly.loop_indices):
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
    root = bpy.data.objects.new('castle_debris', None)
    bpy.context.scene.collection.objects.link(root)
    rng = random.Random(300)
    spots = [(KX - 0.6, KY + 1.6, 7.6), (KX + 0.4, KY + 1.8, 7.9), (KX - 1.2, KY + 1.2, 6.8),
             (KX, KY + 1.9, 5.8), (0.0, BREACH_Y, 4.5), (0.0, -1.5, 4.5), (-0.1, 6.5, 4.9),
             (0.1, -5.5, 4.4), (KX - 1.5, KY + 0.8, 8.2), (KX + 0.9, KY + 1.4, 6.4)]
    for i, p in enumerate(spots + [(KX - 0.9, KY + 1.6, 8.0), (KX + 0.3, KY + 1.9, 8.3)]):
        m = MB()
        if i >= len(spots):
            box(m, (0, 0, 0), (0.9, 0.16, 0.14), 'M_wood', 'wood', seed=320 + i)
        else:
            s = 0.28 + rng.random() * 0.22
            box(m, (0, 0, 0), (s * 1.2, s, s * 0.85), 'M_keep' if i % 2 else 'M_wall', 'rubble',
                jitter=s * 0.4, seed=310 + i)
        print(f'  debris_{i:02d}: {len(m.v)} verts {len(m.f)} faces', flush=True)
        obj = to_object(f'debris_{i:02d}', m, mats, [], 400 + i)
        obj.location = p
        obj.parent = root
    return root


# ---------------------------------------------------------------- scene, export
def reset_scene():
    # Run with --factory-startup; just clear its default cube/camera/light. (Calling
    # read_factory_settings from inside a running script crashes Blender.)
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def export(objs):
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0   # no castle.blend1 backups in the repo
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, 'castle.blend'), compress=True)
    print('blend saved', flush=True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT_DIR, 'castle.glb'), export_format='GLB',
        export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_apply=True,
        export_yup=True, export_materials='EXPORT', export_image_format='AUTO',
        use_visible=False, export_animations=False)


def main():
    reset_scene()
    mats = build_materials()
    states = []
    for s in range(4):
        m, scorch = build_state(s)
        print(f'building castle_s{s}: {len(m.f)} faces', flush=True)
        states.append(to_object(f'castle_s{s}', m, mats, scorch, 1000 + s))
        print(f'castle_s{s}: {len(m.f)} faces, {sum(len(f) - 2 for f in m.f)} tris', flush=True)
    debris = build_debris(mats)
    print('debris built', flush=True)
    for o in states[1:]:
        o.hide_set(True)
    export(states + [debris])
    print('exported', os.path.join(OUT_DIR, 'castle.glb'))


main()
