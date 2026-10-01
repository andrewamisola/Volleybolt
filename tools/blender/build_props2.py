"""Build the SECOND batch of storybook PROPS (stump, guard_tower, hall_wall, banner, brazier, rubble,
wall_broken) in Blender and export them as small GLBs.

They replace the painted backdrops on the territory stage (textures/backdrop_territory.jpg: flagstone half
with round guard towers + stumps) and the core stage (textures/backdrop_core.jpg: stone hall with pillared
walls, banners, braziers, a breached end wall with rubble). Each GLB is loaded ONCE and drawn as thin
instances, so everything is cheap (see tri budgets) and reads from a high 3/4 ortho view.

Run from the repo root:
    "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" -b --factory-startup ^
        --python tools/blender/build_props2.py

Writes models/props/{stump,guard_tower,hall_wall,banner,brazier,rubble,wall_broken}.glb (+ props2.blend).

Conventions (same as build_props.py / build_gatehouse.py): Blender +Z up (glTF export_yup converts),
origin on the ground at the prop's base centre (banner: TOP centre of its rod), faces authored CCW from
outside + flat shaded, materials looked up BY NAME in the game, roughness 1, metallic 0, no textures,
flat base colours x COLOR_0 vertex-colour multiplier (baked ambient occlusion: dark at the base and in
crevices, light on tops). Things that "face the camera" face Blender +Y.
Materials: M_bark M_stumpcut | M_stone M_stone_light M_iron M_banner M_sigil M_sigil_dark M_flame M_coal.
"""
import bpy, bmesh, math, random, os
from mathutils import Vector, Euler

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
OUT_DIR = os.path.join(ROOT, 'models', 'props')
TAU = math.tau


# ---------------------------------------------------------------- palette (sRGB hex -> linear)
def lin(hexstr):
    h = hexstr.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (out[0], out[1], out[2], 1.0)


def make_mat(name, color):
    m = bpy.data.materials.new(name)
    if bpy.app.version < (5, 0, 0):
        m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Base Color'].default_value = color
    bsdf.inputs['Roughness'].default_value = 1.0
    bsdf.inputs['Metallic'].default_value = 0.0
    if 'Specular IOR Level' in bsdf.inputs:
        bsdf.inputs['Specular IOR Level'].default_value = 0.0
    m.diffuse_color = color
    return m


PALETTE = {
    'M_bark': '#6b4a30',         # stump sides (same as the trees)
    'M_stumpcut': '#c79a62',     # pale cut wood on top
    'M_stone': '#a49b8e',        # warm grey flagstone / wall block (game darkens with dusk fog)
    'M_stone_light': '#c0b7a8',  # cap / merlon top / coping
    'M_iron': '#4b4a52',         # sconce, brazier bowl, banner rod
    'M_banner': '#a22b2d',       # banner red
    'M_sigil': '#e2b441',        # gold crown
    'M_sigil_dark': '#4b1015',   # dark red / black flame-leaf sigil
    'M_flame': '#ffb347',        # emissive in game
    'M_coal': '#d9501c',         # glowing coals
}
MATS = list(PALETTE)


def build_materials():
    return {k: make_mat(k, lin(v)) for k, v in PALETTE.items()}


# ---------------------------------------------------------------- mesh accumulator
def newell(pts):
    n = Vector((0, 0, 0))
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n


class MB:
    """Verts + faces, each face tagged with (material, shade-kind). ao_h = height of the ground-AO ramp."""

    def __init__(self, ao_h=1.0):
        self.v, self.f, self.mat, self.kind = [], [], [], []
        self.ao_h = ao_h

    def vert(self, co):
        self.v.append(Vector(co))
        return len(self.v) - 1

    def face(self, idx, mat, kind, want=None):
        idx = list(idx)
        if want is not None and newell([self.v[i] for i in idx]).dot(Vector(want)) < 0:
            idx.reverse()
        self.f.append(idx)
        self.mat.append(MATS.index(mat))
        self.kind.append(kind)

    def tri_count(self):
        return sum(len(f) - 2 for f in self.f)


def hexa(m, P, side, top=None, skip=('bot',)):
    """Hexahedron from 8 corners (0-3 bottom CCW seen from above, 4-7 the matching top corners).
    side/top = (material, kind); skip names: bot top s0 s1 s2 s3 (s0 = -y side, s1 = +x, s2 = +y, s3 = -x)."""
    top = top or side
    ids = [m.vert(p) for p in P]
    faces = {'bot': ((3, 2, 1, 0), side), 'top': ((4, 5, 6, 7), top),
             's0': ((0, 1, 5, 4), side), 's1': ((1, 2, 6, 5), side),
             's2': ((2, 3, 7, 6), side), 's3': ((3, 0, 4, 7), side)}
    for name, (c, (mat, kind)) in faces.items():
        if name in skip:
            continue
        m.face([ids[i] for i in c], mat, kind)
    return ids


def box(m, base, size, side, top=None, rotz=0.0, rot=None, pivot='base', taper=1.0, skip=('bot',),
        jitter=0.0, rng=None):
    """Box with its base-centre at `base`, size (sx, sy, sz); top ring scaled by `taper`; optional rotation
    (rot=(rx, ry, rz) overrides rotz); pivot 'base' or 'centre'; jitter perturbs every corner."""
    sx, sy, sz = size
    loc = []
    for z, k in ((0.0, 1.0), (sz, taper)):
        for (ax, ay) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            loc.append(Vector((ax * sx / 2 * k, ay * sy / 2 * k, z)))
    if jitter and rng:
        loc = [p + Vector([(rng.random() - 0.5) * 2 * jitter for _ in range(3)]) for p in loc]
    eul = Euler(rot if rot is not None else (0, 0, rotz), 'XYZ').to_matrix()
    piv = Vector((0, 0, sz / 2)) if pivot == 'centre' else Vector((0, 0, 0))
    P = [eul @ (p - piv) + piv + Vector(base) for p in loc]
    return hexa(m, P, side, top, skip)


def lathe(m, rings, sides, band, rot=0.0, center=(0.0, 0.0), top=None, bottom=None):
    """Revolved faceted shell. rings [(z, r)] (a band's outward side is the side facing away from the axis when
    z increases); band = (mat, kind) or a per-band list; top/bottom = (mat, kind) n-gon caps."""
    cx, cy = center
    rs = []
    for (z, r) in rings:
        rs.append([m.vert((cx + r * math.cos(rot + TAU * i / sides), cy + r * math.sin(rot + TAU * i / sides), z))
                   for i in range(sides)])
    for k in range(len(rs) - 1):
        b = band[k] if isinstance(band, list) else band
        for i in range(sides):
            j = (i + 1) % sides
            m.face([rs[k][i], rs[k][j], rs[k + 1][j], rs[k + 1][i]], b[0], b[1])
    if top:
        m.face(rs[-1], top[0], top[1])
    if bottom:
        m.face(rs[0][::-1], bottom[0], bottom[1])
    return rs


def annulus(m, z, r_out, r_in, sides, face, rot=0.0):
    """Flat up-facing ring strip between two radii (a ledge top)."""
    a, b = [], []
    for i in range(sides):
        t = rot + TAU * i / sides
        a.append(m.vert((r_out * math.cos(t), r_out * math.sin(t), z)))
        b.append(m.vert((r_in * math.cos(t), r_in * math.sin(t), z)))
    for i in range(sides):
        j = (i + 1) % sides
        m.face([a[i], a[j], b[j], b[i]], face[0], face[1], want=(0, 0, 1))


def ssmooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- vertex-colour shading
def shade(kind, nrm, co, tint, ao_h):
    """RGB multiplier in [0, 1]: ground AO ramp (dark base) x top-light / underside-dark x per-face tint."""
    up = nrm.z * 0.5 + 0.5
    ao = 0.52 + 0.48 * ssmooth(co.z / ao_h)
    tv = 1.0 + 0.16 * (tint - 0.5)
    if isinstance(kind, tuple):                                    # ('blk', z0, z1): masonry course gradient
        _, z0, z1 = kind
        c = 0.70 + 0.30 * ssmooth((co.z - z0) / max(1e-4, z1 - z0))
        v = ao * c * (0.84 + 0.16 * up) * tv
        return (v, v * 0.985, v * 0.96)
    if kind == 'stone':
        v = ao * (0.80 + 0.20 * up) * tv
        if nrm.z < -0.5:
            v *= 0.65
        return (v, v * 0.985, v * 0.96)
    if kind == 'stone_top':                                        # light cap material: keep it bright
        v = (0.62 + 0.38 * ssmooth(co.z / ao_h)) * (0.90 + 0.10 * up) * (1.0 + 0.08 * (tint - 0.5))
        if nrm.z < -0.5:
            v *= 0.62
        return (v, v * 0.985, v * 0.96)
    if kind == 'iron':
        v = (0.70 + 0.30 * up) * (0.7 + 0.3 * ssmooth(co.z / ao_h)) * tv
        return (v, v, v * 1.02)
    if kind == 'bark':
        v = 0.74 + 0.26 * ssmooth(co.z / 0.4) + 0.08 * (tint - 0.5)
        return (v, v * 0.97, v * 0.92)
    if kind == 'cut':
        v = 0.92 + 0.10 * (tint - 0.5)
        return (v, v * 0.97, v * 0.93)
    if kind == 'coal':
        v = 0.70 + 0.30 * tint
        return (v, v * 0.9, v * 0.8)
    if kind == 'cloth':                                            # banner-local z -1.6..0
        t = ssmooth((co.z + 1.6) / 1.6)
        v = (0.70 + 0.30 * t) * (0.93 + 0.14 * nrm.y)
        return (v, v * 0.97, v * 0.97)
    if kind == 'cloth_tower':                                      # tower banner z 1.5..3.9
        t = ssmooth((co.z - 1.4) / 2.5)
        v = (0.72 + 0.28 * t) * (0.93 + 0.14 * nrm.y)
        return (v, v * 0.97, v * 0.97)
    return (1, 1, 1)                                               # flame / sigil / sigil_dark: full bright


def to_object(name, m, mats, seed):
    used = sorted(set(m.mat))
    remap = {old: new for new, old in enumerate(used)}
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in m.v], [], m.f)
    for old in used:
        me.materials.append(mats[MATS[old]])
    me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    me.update()
    rng = random.Random(seed)
    cols = []
    for pi, p in enumerate(me.polygons):
        tint = rng.random()
        nrm = p.normal
        for li in p.loop_indices:
            c = shade(m.kind[pi], nrm, m.v[me.loops[li].vertex_index], tint, m.ao_h)
            cols += (min(1.0, c[0]), min(1.0, c[1]), min(1.0, c[2]), 1.0)
    me.polygons.foreach_set('material_index', [remap[i] for i in m.mat])
    me.polygons.foreach_set('use_smooth', [False] * len(me.polygons))
    me.color_attributes['Col'].data.foreach_set('color', cols)
    me.color_attributes.active_color = me.color_attributes['Col']
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# shorthand (material, kind) pairs
STONE = ('M_stone', 'stone')
LIGHT = ('M_stone_light', 'stone_top')
IRON = ('M_iron', 'iron')


def block(z0, z1):
    return ('M_stone', ('blk', z0, z1))


# ---------------------------------------------------------------- 1. stump
def build_stump(mats):
    """8-sided stump ~0.55 wide, 0.4 tall: flared base, slightly ragged pale cut top, 3 root wedges."""
    rng = random.Random(5)
    m = MB(ao_h=0.35)
    sides = 8
    rot = 0.2
    rings = [(0.0, 0.29), (0.10, 0.255), (0.38, 0.245)]
    rs = []
    for (z, r) in rings:
        ring = []
        for i in range(sides):
            a = rot + TAU * i / sides
            rr = r * (1 + (rng.random() - 0.5) * 0.10)
            ring.append(m.vert((rr * math.cos(a), rr * math.sin(a), z)))
        rs.append(ring)
    for k in range(2):
        for i in range(sides):
            j = (i + 1) % sides
            m.face([rs[k][i], rs[k][j], rs[k + 1][j], rs[k + 1][i]], 'M_bark', 'bark')
    top = []
    for i in range(sides):
        a = rot + TAU * i / sides
        rr = 0.245 * (1 + (rng.random() - 0.5) * 0.10)
        top.append(m.vert((rr * math.cos(a), rr * math.sin(a), 0.40 + (rng.random() - 0.5) * 0.03)))
    for i in range(sides):                                          # short bark band up to the cut
        j = (i + 1) % sides
        m.face([rs[2][i], rs[2][j], top[j], top[i]], 'M_bark', 'bark')
    c = m.vert((0.0, 0.0, 0.415))
    for i in range(sides):
        m.face([top[i], top[(i + 1) % sides], c], 'M_stumpcut', 'cut')
    for k, a in enumerate((0.9, 2.9, 4.8)):                         # three root wedges
        ca, sa = math.cos(a), math.sin(a)
        ta, tb = Vector((-sa, ca, 0)), Vector((ca, sa, 0))
        tip = m.vert(tb * 0.47)
        b1 = m.vert(tb * 0.26 + ta * 0.10)
        b2 = m.vert(tb * 0.26 - ta * 0.10)
        u = m.vert(tb * 0.25 + Vector((0, 0, 0.15)))
        m.face([tip, u, b1], 'M_bark', 'bark', want=(tb.x, tb.y, 0.6))
        m.face([tip, b2, u], 'M_bark', 'bark', want=(tb.x, tb.y, 0.6))
    return to_object('stump', m, mats, 101), m


# ---------------------------------------------------------------- banner cloth (shared by banner + tower)
def banner_cloth(m, x_half, z_bot_side, z_bot_mid, rows, y_fn, kind, mat='M_banner'):
    """Cloth sheet facing +Y: 4 columns x len(rows) bands; the last band's bottom edge is the V point.
    rows = z of the horizontal edges (first = top); y_fn(x, z) = y of the cloth at that point."""
    xs = [-x_half, -x_half / 2, 0.0, x_half / 2, x_half]
    grid = [[m.vert((x, y_fn(x, z), z)) for x in xs] for z in rows]
    vb = []
    for x in xs:
        zb = z_bot_mid + (z_bot_side - z_bot_mid) * abs(x) / x_half
        vb.append(m.vert((x, y_fn(x, zb), zb)))
    grid.append(vb)
    for r in range(len(grid) - 1):
        for c in range(4):
            m.face([grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]], mat, kind, want=(0, 1, 0))


def sigil_leaf(m, cx, cz, y_fn, s=1.0, mat='M_sigil_dark', kind='sigil_dark', lift=0.012):
    """Flame / leaf sigil: central teardrop (4 tris) + two side curls (1 tri each), flat on the cloth (+Y)."""
    def V(x, z):
        X, Z = cx + x * s, cz + z * s
        return m.vert((X, y_fn(X, Z) + lift, Z))
    pts = [(0.0, 0.26), (0.10, 0.08), (0.085, -0.10), (0.0, -0.19), (-0.085, -0.10), (-0.10, 0.08)]
    ids = [V(*p) for p in pts]
    for i in range(1, 5):
        m.face([ids[0], ids[i], ids[i + 1]], mat, kind, want=(0, 1, 0))
    for sx in (1, -1):
        a, b, c = V(sx * 0.07, 0.00), V(sx * 0.25, 0.15), V(sx * 0.11, -0.12)
        m.face([a, b, c], mat, kind, want=(0, 1, 0))


# ---------------------------------------------------------------- 4. banner
def build_banner(mats):
    """Hanging cloth banner 0.9 x 1.6 with a V bottom, a hint of cloth wave, a small iron rod at the top and a
    dark flame/leaf sigil. Origin = TOP centre of the rod; faces +Y; hangs down -Z; rod back touches y~0."""
    m = MB(ao_h=1.0)
    W = 0.45

    def wave(x, z):
        d = min(1.0, -z / 0.55)                                    # clings to the rod, bellies out lower down
        return 0.040 + d * 0.030 * (0.5 + 0.5 * math.sin(z * 4.6 + x * 3.1)) + d * 0.012 * (x / W)
    banner_cloth(m, W, -1.18, -1.60, [-0.07, -0.52, -0.96], wave, 'cloth')
    sigil_leaf(m, 0.0, -0.66, wave, s=1.15)
    box(m, (0, 0.04, -0.07), (1.04, 0.07, 0.07), IRON, skip=('bot',))                  # rod
    for sx in (-1, 1):                                                                 # end knobs
        box(m, (sx * 0.54, 0.04, -0.09), (0.07, 0.09, 0.11), IRON, skip=('bot', 's1' if sx < 0 else 's3', 's0'))
    return to_object('banner', m, mats, 104), m


# ---------------------------------------------------------------- 2. guard tower
def build_tower(mats):
    """Round guard tower: radius ~2.0 (batter: 2.4 at the plinth, 1.95 under the parapet), 16-sided, a flared
    corbel ring, 10 chunky merlons (top at 5.2), a red banner + gold crown on the +Y face and one wall torch
    beside it."""
    m = MB(ao_h=2.2)
    N = 16
    rot = math.pi / 2 - math.pi / N                                # a face centre points exactly at +Y
    apo = math.cos(math.pi / N)

    def R(z):                                                      # body radius (batter)
        return 2.02 - (z - 0.45) * (0.15 / 3.80) if z >= 0.45 else 2.25
    lathe(m, [(0.0, 2.27), (0.45, 2.16)], N, STONE, rot=rot)                       # plinth
    annulus(m, 0.45, 2.16, R(0.45), N, LIGHT, rot=rot)                             # plinth ledge
    zs = [0.45, 1.30, 2.55, 3.45, 4.25]
    lathe(m, [(z, R(z)) for z in zs], N, STONE, rot=rot)                           # body
    lathe(m, [(0.95, R(0.95) + 0.07), (1.10, R(1.10) + 0.07)], N, STONE, rot=rot)  # proud band (below banner tip)
    annulus(m, 1.10, R(1.10) + 0.07, R(1.10) - 0.02, N, LIGHT, rot=rot)
    lathe(m, [(4.25, R(4.25)), (4.40, R(4.25) + 0.05), (4.62, 2.18)], N, STONE, rot=rot)   # corbel flare
    m.face([m.vert((2.18 * math.cos(rot + TAU * i / N), 2.18 * math.sin(rot + TAU * i / N), 4.62))
            for i in range(N)], 'M_stone_light', 'stone_top', want=(0, 0, 1))      # walkway disc
    for i in range(10):                                            # merlons, light tops
        a = math.pi / 2 + TAU * i / 10
        c = Vector((1.92 * math.cos(a), 1.92 * math.sin(a), 4.62))
        box(m, c, (0.55, 0.86, 0.58), STONE, top=LIGHT, rotz=a, skip=('bot',))
    for k in (-3, 3, 6, -6):                                       # arrow slits (flat dark quads)
        a = math.pi / 2 + k * math.pi / 8
        z0, z1 = 2.0, 2.9
        rr = R((z0 + z1) / 2) * apo + 0.012
        tdir = Vector((-math.sin(a), math.cos(a), 0))
        rdir = Vector((math.cos(a), math.sin(a), 0))
        pts = [rdir * rr + tdir * dx + Vector((0, 0, z)) for (dx, z) in
               ((-0.07, z0), (0.07, z0), (0.07, z1), (-0.07, z1))]
        m.face([m.vert(p) for p in pts], 'M_iron', 'iron', want=(rdir.x, rdir.y, 0))

    def wave(x, z):                                                # banner surface follows the batter + wave
        return R(z) * apo + 0.06 + 0.026 * (0.5 + 0.5 * math.sin(z * 4.2 + x * 3.0))
    banner_cloth(m, 0.45, 1.95, 1.50, [3.90, 3.30, 2.65], wave, 'cloth_tower')

    def Y(x, z): return wave(x, z) + 0.014
    cp = [(-0.25, 3.00), (0.25, 3.00), (0.25, 3.34), (0.125, 3.20), (0.0, 3.40), (-0.125, 3.20), (-0.25, 3.34)]
    ids = [m.vert((x, Y(x, z), z)) for (x, z) in cp]                # gold crown
    for i in range(1, len(ids) - 1):
        m.face([ids[0], ids[i], ids[i + 1]], 'M_sigil', 'sigil', want=(0, 1, 0))
    ids = [m.vert((x, Y(x, z) + 0.002, z)) for (x, z) in ((-0.25, 2.80), (0.25, 2.80), (0.25, 2.90), (-0.25, 2.90))]
    m.face(ids, 'M_sigil', 'sigil', want=(0, 1, 0))                 # gold band under the crown
    zr = 3.90
    box(m, (0, wave(0, zr) - 0.01, zr - 0.07), (1.06, 0.08, 0.08), IRON, skip=('bot',))   # banner rod
    for sx in (-1, 1):
        box(m, (sx * 0.55, wave(0, zr) - 0.01, zr - 0.09), (0.08, 0.10, 0.12), IRON,
            skip=('bot', 's1' if sx < 0 else 's3', 's0'))
    # wall torch sconce: +Y side, beside the banner, bracket pointing radially out
    ta = math.pi / 2 - math.asin(1.30 / 1.95)
    zt = 2.55
    wall = R(zt) * apo
    rd = Vector((math.cos(ta), math.sin(ta), 0))

    def at(rad, z): return Vector((rd.x * rad, rd.y * rad, z))
    box(m, at(wall + 0.025, zt - 0.17), (0.09, 0.20, 0.42), IRON, rotz=ta, skip=('bot',))   # back plate
    box(m, at(wall + 0.20, zt + 0.02), (0.36, 0.07, 0.07), IRON, rotz=ta, skip=('bot',))    # arm
    bx = wall + 0.36
    cx, cy = rd.x * bx, rd.y * bx
    lathe(m, [(zt + 0.02, 0.07), (zt + 0.15, 0.13)], 6, IRON, rot=ta, center=(cx, cy), top=IRON)   # cup
    zf = zt + 0.15
    r0 = [m.vert((cx + 0.10 * math.cos(ta + 0.78 + TAU * i / 4), cy + 0.10 * math.sin(ta + 0.78 + TAU * i / 4), zf))
          for i in range(4)]
    r1 = [m.vert((cx + 0.13 * math.cos(ta + 0.78 + TAU * i / 4), cy + 0.13 * math.sin(ta + 0.78 + TAU * i / 4),
                  zf + 0.15)) for i in range(4)]
    tip = m.vert((cx, cy, zf + 0.42))                              # flame: separate M_flame primitive
    for i in range(4):
        j = (i + 1) % 4
        m.face([r0[i], r0[j], r1[j], r1[i]], 'M_flame', 'flame')
        m.face([r1[i], r1[j], tip], 'M_flame', 'flame')
    return to_object('guard_tower', m, mats, 102), m


# ---------------------------------------------------------------- 3. hall wall module
def pillar(m, cx, cy=0.0):
    """Square stone pillar ~0.9 wide, 2.8 tall, chunky light cap."""
    box(m, (cx, cy, 0.0), (1.00, 1.00, 0.28), STONE, top=LIGHT)                         # plinth + ledge
    box(m, (cx, cy, 0.28), (0.90, 0.90, 2.12), block(0.28, 2.40), skip=('bot', 'top'))  # shaft (0.9 sq)
    box(m, (cx, cy, 2.40), (0.98, 0.98, 0.12), LIGHT, skip=('bot', 'top'))              # collar
    box(m, (cx, cy, 2.52), (0.98, 0.98, 0.12), LIGHT, taper=1.14 / 0.98, skip=('bot', 'top'))   # chamfer out
    box(m, (cx, cy, 2.64), (1.14, 1.14, 0.16), LIGHT, skip=('bot',))                    # cap slab
    return m


COURSES = [  # (z0, z1, block edges in x)
    (0.28, 0.95, [-2.0, -0.7, 0.6, 2.0]),
    (0.95, 1.58, [-2.0, -1.2, 0.0, 1.3, 2.0]),
    (1.58, 2.00, [-2.0, -0.4, 1.0, 2.0]),
]


def build_hall_wall(mats):
    """Wall module that tiles along X: x -2..+2, 0.8 thick body, 2.2 tall to the top of the coping, a square
    pillar (0.9, 2.8 tall) centred at x=-2 so modules every 4 units give a pillar every 4."""
    m = MB(ao_h=0.9)
    rng = random.Random(3)
    box(m, (0, 0, 0), (4.0, 0.90, 0.28), STONE, top=LIGHT, skip=('bot', 's3'))        # plinth strip + ledge
    for (z0, z1, xs) in COURSES:
        for a, b in zip(xs[:-1], xs[1:]):
            th = 0.80 + 0.03 * (rng.random() - 0.5)
            box(m, ((a + b) / 2, 0, z0), (b - a, th, z1 - z0), block(z0, z1),
                skip=('bot', 'top', 's1', 's3'))
    box(m, (0, 0, 2.0), (4.0, 0.92, 0.20), LIGHT, skip=('bot', 's3'))                 # coping
    pillar(m, -2.0)
    for (z0, z1, w) in ((0.0, 0.28, 0.45), (0.28, 2.0, 0.40), (2.0, 2.2, 0.46)):      # close the +x end
        pts = [Vector((2.0, -w, z0)), Vector((2.0, w, z0)), Vector((2.0, w, z1)), Vector((2.0, -w, z1))]
        m.face([m.vert(p) for p in pts], 'M_stone', 'stone', want=(1, 0, 0))
    return to_object('hall_wall', m, mats, 103), m


# ---------------------------------------------------------------- 5. brazier
def build_brazier(mats):
    """Square stone pedestal 0.8 x 0.8 x 0.9 (light cap) + iron bowl + glowing coals + small faceted flame."""
    rng = random.Random(9)
    m = MB(ao_h=0.6)
    box(m, (0, 0, 0), (0.80, 0.80, 0.16), STONE, top=STONE)                           # base step
    box(m, (0, 0, 0.16), (0.64, 0.64, 0.56), STONE, skip=('bot', 'top'))              # waist
    box(m, (0, 0, 0.72), (0.80, 0.80, 0.18), STONE, top=LIGHT, skip=('bot',))         # cap
    rot = TAU / 16
    lathe(m, [(0.90, 0.17), (0.99, 0.30), (1.15, 0.40)], 8, IRON, rot=rot)            # bowl shell
    annulus(m, 1.15, 0.40, 0.31, 8, IRON, rot=rot)                                    # rim
    lathe(m, [(1.15, 0.31), (1.03, 0.25)], 8, IRON, rot=rot)                          # inner wall (faces inward)
    ring = []
    for i in range(8):                                                                # coals: lumpy fan
        a = rot + TAU * i / 8
        ring.append(m.vert((0.27 * math.cos(a), 0.27 * math.sin(a), 1.06 + (rng.random() - 0.5) * 0.03)))
    c = m.vert((0.0, 0.0, 1.14))
    for i in range(8):
        m.face([ring[i], ring[(i + 1) % 8], c], 'M_coal', 'coal', want=(0, 0, 1))

    def tongue(cx, cy, z0, r, h, tilt, rr):                                           # faceted flame tongue
        base = [m.vert((cx + r * math.cos(rr + TAU * i / 6), cy + r * math.sin(rr + TAU * i / 6), z0))
                for i in range(6)]
        mid = [m.vert((cx + 1.15 * r * math.cos(rr + TAU * i / 6) + tilt[0] * 0.5,
                       cy + 1.15 * r * math.sin(rr + TAU * i / 6) + tilt[1] * 0.5, z0 + h * 0.38))
               for i in range(6)]
        tip = m.vert((cx + tilt[0], cy + tilt[1], z0 + h))
        for i in range(6):
            j = (i + 1) % 6
            m.face([base[i], base[j], mid[j], mid[i]], 'M_flame', 'flame')
            m.face([mid[i], mid[j], tip], 'M_flame', 'flame')
    tongue(0.0, 0.0, 1.12, 0.17, 0.62, (0.03, -0.02), 0.3)
    tongue(0.16, 0.05, 1.12, 0.07, 0.30, (0.07, 0.02), 0.1)
    tongue(-0.14, -0.06, 1.12, 0.07, 0.26, (-0.05, -0.03), 0.5)
    return to_object('brazier', m, mats, 105), m


# ---------------------------------------------------------------- 6. rubble
def build_rubble(mats):
    """Pile of 6 chunky tumbled cut-stone blocks (largest ~0.7), ~1.6 wide footprint."""
    rng = random.Random(21)
    m = MB(ao_h=0.7)
    specs = [  # ((x, y), size, tumble rotation, extra z lift)
        ((0.00, 0.00), (0.70, 0.55, 0.42), (0.10, -0.15, 0.5), 0.0),
        ((0.62, 0.30), (0.50, 0.42, 0.36), (-0.2, 0.18, 1.9), 0.0),
        ((-0.58, -0.20), (0.46, 0.40, 0.32), (0.12, 0.3, 2.6), 0.0),
        ((0.30, -0.48), (0.38, 0.34, 0.30), (0.3, -0.1, 0.9), 0.0),
        ((-0.12, 0.42), (0.34, 0.30, 0.26), (-0.15, 0.2, 0.2), 0.0),
        ((0.12, 0.08), (0.34, 0.30, 0.28), (0.25, 0.45, 1.2), 0.30),      # perched on top of the big one
    ]
    for (cx, cy), size, rt, lift in specs:
        eul = Euler(rt, 'XYZ').to_matrix()
        sx, sy, sz = size
        loc = []
        for z in (0.0, sz):
            for (ax, ay) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                loc.append(Vector((ax * sx / 2, ay * sy / 2, z - sz / 2)) +
                           Vector([(rng.random() - 0.5) * 0.05 for _ in range(3)]))
        P = [eul @ p for p in loc]
        zmin = min(p.z for p in P)
        P = [p + Vector((cx, cy, -zmin + lift)) for p in P]
        hexa(m, P, STONE, top=STONE, skip=())
    return to_object('rubble', m, mats, 106), m


# ---------------------------------------------------------------- 7. broken wall end
def build_wall_broken(mats):
    """Broken end of a hall wall: same section (0.8 thick, 2.2 tall) from x=0 to +2.5, top steps down jaggedly
    to rubble at +X."""
    rng = random.Random(8)
    m = MB(ao_h=0.9)
    box(m, (1.25, 0, 0.0), (2.5, 0.90, 0.28), STONE, top=LIGHT, skip=('bot', 's3'))   # plinth strip + ledge
    for (z0, z1) in ((0.28, 0.95), (0.95, 1.58), (1.58, 2.0)):                        # intact stub, courses
        box(m, (0.35, 0, z0), (0.7, 0.8, z1 - z0), block(z0, z1), skip=('bot', 'top', 's1', 's3'))
    box(m, (0.35, 0, 2.0), (0.7, 0.92, 0.20), LIGHT, skip=('bot', 's3'))              # coping on the stub
    cols = [(0.70, 1.25, 1.98, 1.55, 0.00, 0.02),                                     # jagged columns:
            (1.25, 1.72, 1.55, 1.72, 0.04, 0.00),                                     # x0, x1, h(x0), h(x1),
            (1.72, 2.08, 1.72, 1.02, 0.00, 0.08),                                     # front inset, back inset
            (2.08, 2.40, 1.02, 1.18, 0.10, 0.03),
            (2.40, 2.50, 1.18, 0.46, 0.04, 0.10)]
    for (x0, x1, h0, h1, fi, bi) in cols:
        yf, yb = -0.4 + fi, 0.4 - bi
        dz = 0.14 * (1 if rng.random() > 0.5 else -1)                                 # diagonal break through depth
        P = [(x0, yf, 0.28), (x1, yf, 0.28), (x1, yb, 0.28), (x0, yb, 0.28),
             (x0, yf, h0 + dz), (x1, yf, h1 + dz), (x1, yb, h1 - dz), (x0, yb, h0 - dz)]
        hexa(m, P, block(0.28, 2.0), top=LIGHT, skip=('bot',))
    for (cx, cy, s, rz) in ((2.30, 0.50, 0.30, 0.6), (1.95, -0.50, 0.26, 1.7)):       # fallen chunks
        box(m, (cx, cy, 0.06), (s, s * 0.85, s * 0.8), STONE, top=STONE, rot=(0.15, -0.1, rz), skip=())
    return to_object('wall_broken', m, mats, 107), m


# ---------------------------------------------------------------- scene, export
def reset_scene():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)


def export_one(obj, fname):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT_DIR, fname), export_format='GLB', use_selection=True,
        export_vertex_color='ACTIVE', export_all_vertex_colors=False, export_apply=True,
        export_yup=True, export_materials='EXPORT', export_image_format='AUTO',
        export_animations=False)


BUDGET = {'stump': 80, 'guard_tower': 900, 'hall_wall': 200, 'banner': 60, 'brazier': 260,
          'rubble': 160, 'wall_broken': 160}


def report(obj, m):
    xs = [v.x for v in m.v]
    ys = [v.y for v in m.v]
    zs = [v.z for v in m.v]
    mats = sorted({MATS[i] for i in m.mat})
    print(f'{obj.name}: {m.tri_count()} tris (budget {BUDGET[obj.name]}), '
          f'size x {max(xs) - min(xs):.2f} y {max(ys) - min(ys):.2f} z {max(zs) - min(zs):.2f} | '
          f'x {min(xs):.2f}..{max(xs):.2f} y {min(ys):.2f}..{max(ys):.2f} z {min(zs):.2f}..{max(zs):.2f} | {mats}',
          flush=True)
    assert m.tri_count() <= BUDGET[obj.name], f'{obj.name} over tri budget'


def main():
    reset_scene()
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    mats = build_materials()
    objs = []
    for fn, name in ((build_stump, 'stump.glb'), (build_tower, 'guard_tower.glb'),
                     (build_hall_wall, 'hall_wall.glb'), (build_banner, 'banner.glb'),
                     (build_brazier, 'brazier.glb'), (build_rubble, 'rubble.glb'),
                     (build_wall_broken, 'wall_broken.glb')):
        obj, m = fn(mats)
        report(obj, m)
        objs.append((obj, name))
    for obj, name in objs:
        export_one(obj, name)
        print('exported', os.path.join(OUT_DIR, name), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, 'props2.blend'), compress=True)


main()
