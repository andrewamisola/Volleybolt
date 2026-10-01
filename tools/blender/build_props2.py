"""Build the SECOND batch of storybook PROPS (stump, guard_tower, hall_wall, banner, brazier, rubble,
wall_broken, curtain_wall, curtain_wall_end, curtain_wall_end_r) in Blender and export them as small GLBs.

They replace the painted backdrops on the territory stage (textures/backdrop_territory.jpg: flagstone half
with round guard towers + stumps) and the core stage (textures/backdrop_core.jpg: stone hall with pillared
walls, banners, braziers, a breached end wall with rubble). Each GLB is loaded ONCE and drawn as thin
instances, so everything is cheap (see tri budgets) and reads from a high 3/4 ortho view.

Run from the repo root:
    "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" -b --factory-startup ^
        --python tools/blender/build_props2.py

Writes models/props/{stump,guard_tower,hall_wall,banner,brazier,rubble,wall_broken,curtain_wall,
curtain_wall_end,curtain_wall_end_r}.glb (+ props2.blend).

Conventions (same as build_props.py / build_gatehouse.py): Blender +Z up (glTF export_yup converts),
origin on the ground at the prop's base centre (banner: TOP centre of its rod), faces authored CCW from
outside, materials looked up BY NAME in the game, roughness 1, metallic 0, x COLOR_0 vertex-colour
multiplier (baked ambient occlusion: dark at the base and in crevices). Things that "face the camera"
face Blender +Y.

STONE IS TEXTURED exactly like tools/blender/build_gatehouse.py so props and the real gatehouse read as the
same masonry side by side: M_keep = textures/tower_stone.png (round towers; lighter coping/caps),
M_wall = textures/castle_wall.png (walls, pillars, rubble). Texel density = 1 texture repeat per TILE = 1.6
world units (same constant as the gatehouse). Every face carries explicit UVs: lathe surfaces get (u along
the circumference, v = z / TILE), boxes / prisms get world-scale planar UVs (vertical faces: u along the
face, v = z / TILE; horizontal faces: x, y). Wall modules that tile every 4 units use a u phase picked so the
64px brick texture is continuous across the 4.0 seam (2.5 repeats per module).
Materials: M_bark M_stumpcut | M_keep M_wall (textured) | M_iron M_banner M_sigil M_sigil_dark M_flame M_coal.
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


TEX_DIR = os.path.join(ROOT, 'textures')
TILE = 1.6                      # world units per stone texture repeat -- SAME as build_gatehouse.py
SEAM_U = 0.0547                 # u phase that makes castle_wall.png continuous across a 4.0 module seam


def load_image(name):
    img = bpy.data.images.load(os.path.join(TEX_DIR, name))
    img.pack()
    return img


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
    if image is not None:                                  # same wiring as build_gatehouse.make_mat
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = image
        tex.interpolation = 'Closest'
        nt.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = color
    m.diffuse_color = color
    return m


PALETTE = {
    'M_bark': '#6b4a30',         # stump sides (same as the trees)
    'M_stumpcut': '#c79a62',     # pale cut wood on top
    'M_keep': '#a8a49a',         # tower_stone.png (round towers, coping/caps) -- colour only used as a fallback
    'M_wall': '#8a8070',         # castle_wall.png (walls, pillars, rubble)
    'M_iron': '#4b4a52',         # sconce, brazier bowl, banner rod
    'M_banner': '#a22b2d',       # banner red
    'M_sigil': '#e2b441',        # gold crown
    'M_sigil_dark': '#4b1015',   # dark red / black flame-leaf sigil
    'M_flame': '#ffb347',        # emissive in game
    'M_coal': '#d9501c',         # glowing coals
}
MATS = list(PALETTE)


STONE_IMG = {'M_keep': 'tower_stone.png', 'M_wall': 'castle_wall.png'}


def build_materials():
    return {k: make_mat(k, lin(v), load_image(STONE_IMG[k]) if k in STONE_IMG else None)
            for k, v in PALETTE.items()}


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

    def __init__(self, ao_h=1.0, xoff=0.0, ushift=0.0):
        self.v, self.f, self.mat, self.kind, self.uv, self.smooth = [], [], [], [], [], []
        self.ao_h = ao_h
        self.xoff, self.ushift = xoff, ushift      # planar-UV x offset / u phase (tiling wall modules)

    def vert(self, co):
        self.v.append(Vector(co))
        return len(self.v) - 1

    def auto_uv(self, idx):
        """World-scale planar UVs, 1 texture repeat per TILE (the gatehouse's density). Vertical faces: u runs
        along the face (left-to-right as seen from outside), v = z / TILE so brick courses stay horizontal at
        world height; horizontal faces: (x, y). Same idea as build_gatehouse.quad_planar but rotation-proof."""
        pts = [self.v[i] for i in idx]
        n = newell(pts)
        if n.length < 1e-9:
            return [(0.0, 0.0)] * len(idx)
        n.normalize()
        if abs(n.z) > 0.7:
            return [((p.x + self.xoff) / TILE + self.ushift, p.y / TILE) for p in pts]
        t = Vector((-n.y, n.x, 0.0)).normalized()
        return [(((p.x + self.xoff) * t.x + p.y * t.y) / TILE + self.ushift, p.z / TILE) for p in pts]

    def face(self, idx, mat, kind, want=None, uv=None, smooth=False):
        idx = list(idx)
        if want is not None and newell([self.v[i] for i in idx]).dot(Vector(want)) < 0:
            idx.reverse()
            if uv is not None:
                uv = uv[::-1]
        self.f.append(idx)
        self.mat.append(MATS.index(mat))
        self.kind.append(kind)
        self.uv.append(uv if uv is not None else self.auto_uv(idx))
        self.smooth.append(smooth)

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


def lathe(m, rings, sides, band, rot=0.0, center=(0.0, 0.0), top=None, bottom=None, smooth=False):
    """Revolved faceted shell. rings [(z, r)] (a band's outward side is the side facing away from the axis when
    z increases); band = (mat, kind) or a per-band list; top/bottom = (mat, kind) n-gon caps.
    UVs (as build_gatehouse.lathe): u along the circumference at TILE world units per repeat (rounded to a whole
    number of repeats per band so the wrap seam is invisible, <5% density change), v = z / TILE."""
    cx, cy = center
    rs = []
    for (z, r) in rings:
        rs.append([m.vert((cx + r * math.cos(rot + TAU * i / sides), cy + r * math.sin(rot + TAU * i / sides), z))
                   for i in range(sides)])
    for k in range(len(rs) - 1):
        b = band[k] if isinstance(band, list) else band
        r_avg = max((rings[k][1] + rings[k + 1][1]) / 2, 0.3)
        circ = max(1, round(TAU * r_avg / TILE))
        v0, v1 = rings[k][0] / TILE, rings[k + 1][0] / TILE
        for i in range(sides):
            j = (i + 1) % sides
            u0, u1 = circ * i / sides, circ * (i + 1) / sides
            m.face([rs[k][i], rs[k][j], rs[k + 1][j], rs[k + 1][i]], b[0], b[1],
                   uv=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)], smooth=smooth)
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
STONE_KINDS = ('stone', 'stone_top', 'rubble')


def shade(kind, nrm, co, tint, ao_h):
    """RGB multiplier in [0, 1]. Stone uses the gatehouse's formula (dark ground-AO ramp up to ~1.7, +-8% per-face
    variation, slight warm tint) so the textured props sit at the same brightness as the real structures."""
    if kind in STONE_KINDS:
        ramp = max(0.5, min(1.7, ao_h))
        v = 0.62 + 0.38 * min(1.0, co.z / ramp)
        v *= (0.97 + 0.05 * tint) if kind == 'stone_top' else (0.88 + 0.16 * tint)
        if kind == 'rubble':
            v *= 0.85
        if nrm.z < -0.5:
            v *= 0.65
        return (min(1.0, v * (1.0 + 0.03 * tint)), min(1.0, v), min(1.0, v * (0.95 - 0.04 * tint)))
    up = nrm.z * 0.5 + 0.5
    tv = 1.0 + 0.16 * (tint - 0.5)
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
    me.uv_layers.new(name='UVMap')
    me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    me.update()
    assert len(me.polygons) == len(m.f), f'{name}: degenerate faces were dropped'
    rng = random.Random(seed)
    cols, uvs = [], []
    for pi, p in enumerate(me.polygons):
        tint = rng.random()
        nrm = p.normal
        for j, li in enumerate(p.loop_indices):
            uvs += m.uv[pi][j]
            c = shade(m.kind[pi], nrm, m.v[me.loops[li].vertex_index], tint, m.ao_h)
            cols += (min(1.0, c[0]), min(1.0, c[1]), min(1.0, c[2]), 1.0)
    me.polygons.foreach_set('material_index', [remap[i] for i in m.mat])
    me.polygons.foreach_set('use_smooth', m.smooth)
    me.uv_layers['UVMap'].data.foreach_set('uv', uvs)
    me.color_attributes['Col'].data.foreach_set('color', cols)
    me.color_attributes.active_color = me.color_attributes['Col']
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# shorthand (material, kind) pairs
STONE = ('M_wall', 'stone')          # walls, pillars, rubble, pedestals (castle_wall.png)
KEEP = ('M_keep', 'stone')           # round tower masonry (tower_stone.png)
LIGHT = ('M_keep', 'stone_top')      # lighter coping / caps / merlon tops (tower_stone.png is the lighter stone)
IRON = ('M_iron', 'iron')


def prism_x(m, x0, x1, prof, band, caps=(True, True)):
    """Convex (y, z) profile extruded along X from x0 to x1 (wall bodies, cornices). Side faces + optional end
    caps, all wound outward."""
    cy = sum(p[0] for p in prof) / len(prof)
    cz = sum(p[1] for p in prof) / len(prof)
    a = [m.vert((x0, y, z)) for (y, z) in prof]
    b = [m.vert((x1, y, z)) for (y, z) in prof]
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        ym, zm = (prof[i][0] + prof[j][0]) / 2, (prof[i][1] + prof[j][1]) / 2
        m.face([a[i], b[i], b[j], a[j]], band[0], band[1], want=(0, ym - cy, zm - cz))
    if caps[0]:
        m.face(a, band[0], band[1], want=(-1, 0, 0))
    if caps[1]:
        m.face(b, band[0], band[1], want=(1, 0, 0))


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
    """Round guard tower (M_keep / tower_stone.png, same texel density as the gatehouse's drums): radius ~2.0 (batter: 2.4 at the plinth, 1.95 under the parapet), 16-sided, a flared
    corbel ring, 10 chunky merlons (top at 5.2), a red banner + gold crown on the +Y face and one wall torch
    beside it."""
    m = MB(ao_h=2.2)
    N = 16
    rot = math.pi / 2 - math.pi / N                                # a face centre points exactly at +Y
    apo = math.cos(math.pi / N)

    def R(z):                                                      # body radius (batter)
        return 2.02 - (z - 0.45) * (0.15 / 3.80) if z >= 0.45 else 2.25
    lathe(m, [(0.0, 2.27), (0.45, 2.16)], N, KEEP, rot=rot, smooth=True)                       # plinth
    annulus(m, 0.45, 2.16, R(0.45), N, LIGHT, rot=rot)                             # plinth ledge
    zs = [0.45, 1.30, 2.55, 3.45, 4.25]
    lathe(m, [(z, R(z)) for z in zs], N, KEEP, rot=rot, smooth=True)                           # body
    lathe(m, [(0.95, R(0.95) + 0.07), (1.10, R(1.10) + 0.07)], N, KEEP, rot=rot, smooth=True)  # proud band (below banner tip)
    annulus(m, 1.10, R(1.10) + 0.07, R(1.10) - 0.02, N, LIGHT, rot=rot)
    lathe(m, [(4.25, R(4.25)), (4.40, R(4.25) + 0.05), (4.62, 2.18)], N, KEEP, rot=rot, smooth=True)   # corbel flare
    m.face([m.vert((2.18 * math.cos(rot + TAU * i / N), 2.18 * math.sin(rot + TAU * i / N), 4.62))
            for i in range(N)], 'M_keep', 'stone_top', want=(0, 0, 1))      # walkway disc
    for i in range(10):                                            # merlons, light tops
        a = math.pi / 2 + TAU * i / 10
        c = Vector((1.92 * math.cos(a), 1.92 * math.sin(a), 4.62))
        box(m, c, (0.55, 0.86, 0.58), KEEP, top=LIGHT, rotz=a, skip=('bot',))
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
    box(m, (cx, cy, 0.28), (0.90, 0.90, 2.12), STONE, skip=('bot', 'top'))  # shaft (0.9 sq)
    box(m, (cx, cy, 2.40), (0.98, 0.98, 0.12), LIGHT, skip=('bot', 'top'))              # collar
    box(m, (cx, cy, 2.52), (0.98, 0.98, 0.12), LIGHT, taper=1.14 / 0.98, skip=('bot', 'top'))   # chamfer out
    box(m, (cx, cy, 2.64), (1.14, 1.14, 0.16), LIGHT, skip=('bot',))                    # cap slab
    return m


def build_hall_wall(mats):
    """Wall module that tiles along X: x -2..+2, ~0.8 thick body (slight batter, ONE continuous castle_wall.png
    face -- the masonry now comes from the texture, not from stacked block boxes), 2.2 tall to the top of the
    coping (M_keep, the lighter stone), a square pillar (0.9, 2.8 tall) centred at x=-2 so modules every 4 units
    give a pillar every 4. u phase = SEAM_U so the bricks run on unbroken across the 4.0 module seam."""
    m = MB(ao_h=0.9, ushift=SEAM_U)
    box(m, (0, 0, 0), (4.0, 0.90, 0.28), STONE, top=LIGHT, skip=('bot', 's3'))        # plinth strip + ledge
    prism_x(m, -2.0, 2.0, [(-0.43, 0.28), (0.43, 0.28), (0.40, 2.0), (-0.40, 2.0)], STONE, caps=(False, True))
    box(m, (0, 0, 2.0), (4.0, 0.92, 0.20), LIGHT, skip=('bot', 's3'))                 # coping
    pillar(m, -2.0)
    return to_object('hall_wall', m, mats, 103), m


def build_hall_wall_tall(mats):
    """FULL-HEIGHT interior hall wall for the core (owner: inside the fortress it's a real wall, not a knee-high
    rampart). Same tiling as hall_wall (x -2..+2, pillar at x=-2, SEAM_U phase) but 5.6 tall with a string course
    at 2.8 and a corbelled coping, built at true height so the castle_wall texture keeps its real brick size."""
    H = 5.6
    m = MB(ao_h=1.4, ushift=SEAM_U)
    box(m, (0, 0, 0), (4.0, 0.98, 0.36), STONE, top=LIGHT, skip=('bot', 's3'))        # plinth
    prism_x(m, -2.0, 2.0, [(-0.47, 0.36), (0.47, 0.36), (0.42, H - 0.3), (-0.42, H - 0.3)], STONE,
            caps=(False, True))
    box(m, (0, 0, 2.8), (4.0, 0.98, 0.16), LIGHT, skip=('bot', 's3'))                 # string course
    box(m, (0, 0, H - 0.3), (4.0, 1.02, 0.14), LIGHT, skip=('bot', 's3'))             # corbel
    box(m, (0, 0, H - 0.16), (4.0, 1.08, 0.22), LIGHT, skip=('bot', 's3'))            # coping
    cx = -2.0                                                                         # pillar (pilaster)
    box(m, (cx, 0, 0.0), (1.10, 1.30, 0.40), STONE, top=LIGHT)
    box(m, (cx, 0, 0.40), (0.95, 1.18, H - 0.2), STONE, skip=('bot', 'top'))
    box(m, (cx, 0, H + 0.2), (1.10, 1.30, 0.14), LIGHT, skip=('bot', 'top'))
    box(m, (cx, 0, H + 0.34), (1.20, 1.40, 0.18), LIGHT, skip=('bot',))
    return to_object('hall_wall_tall', m, mats, 111), m


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
        hexa(m, P, ('M_wall', 'rubble'), top=('M_wall', 'rubble'), skip=())
    return to_object('rubble', m, mats, 106), m


# ---------------------------------------------------------------- 7. broken wall end
def build_wall_broken(mats):
    """Broken end of a hall wall: same section (0.8 thick, 2.2 tall) from x=0 to +2.5, top steps down jaggedly
    to rubble at +X."""
    rng = random.Random(8)
    m = MB(ao_h=0.9, xoff=2.0, ushift=SEAM_U)   # xoff: continues hall_wall masonry phase from its +x end
    box(m, (1.25, 0, 0.0), (2.5, 0.90, 0.28), STONE, top=LIGHT, skip=('bot', 's3'))   # plinth strip + ledge
    prism_x(m, 0.0, 0.7, [(-0.40, 0.28), (0.40, 0.28), (0.40, 2.0), (-0.40, 2.0)], STONE, caps=(False, False))  # intact stub
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
        hexa(m, P, STONE, top=LIGHT, skip=('bot',))
    for (cx, cy, s, rz) in ((2.30, 0.50, 0.30, 0.6), (1.95, -0.50, 0.26, 1.7)):       # fallen chunks
        box(m, (cx, cy, 0.06), (s, s * 0.85, s * 0.8), ('M_wall', 'rubble'), top=('M_wall', 'rubble'), rot=(0.15, -0.1, rz), skip=())
    return to_object('wall_broken', m, mats, 107), m


# ---------------------------------------------------------------- 8. curtain wall modules
# A crenellated battlement curtain wall in the gatehouse's own language (build_gatehouse.curtain_wall): M_wall
# masonry with a slight batter, a projecting walkway course, chunky merlons on BOTH edges, buttress piers. The
# gatehouse wall is 6.2 tall to the walkway against a 7.8 gate-tower parapet (0.79); here the walkway is 3.7
# against the guard tower's 4.62 parapet (0.80), merlon tops 4.4-4.55, so the wall always sits just under the
# tower's own parapet. 4.0 long on X (x -2..2), tiles every 4.0 with the wall texture continuous across the seam.
CW_HALF = 4.0 / 2
CW_T = 0.60                  # half thickness at the walkway (1.2 thick)
CW_BATTER = 0.09             # extra half-thickness at the base (gatehouse batters its wall the same way)
CW_WALK = 3.70               # walkway (top of the cornice) height
CW_CORN = 0.22               # cornice course height
CW_MERLON = (0.66, 0.38)     # merlon size along the wall / across it (gatehouse: 0.6 x 0.8 on a 2.2 wall)
CW_MERLON_H = [(0.80, 0.72), (0.70, 0.82), (0.78, 0.70), (0.72, 0.78)]    # (+Y edge, -Y edge) heights, 4 / module


def curtain_module(variant):
    """variant 'mid': plain tiling module. 'end_l': the tower end is local x=-2 (first merlon omitted so nothing
    pokes out of the tower body; flat end face). 'end_r': mirror image (tower end at local x=+2)."""
    m = MB(ao_h=1.7, ushift=SEAM_U)
    zc = CW_WALK - CW_CORN
    prism_x(m, -CW_HALF, CW_HALF, [(-(CW_T + CW_BATTER), 0.0), (CW_T + CW_BATTER, 0.0), (CW_T, zc), (-CW_T, zc)], STONE)
    prism_x(m, -CW_HALF, CW_HALF, [(-(CW_T + 0.08), zc), (CW_T + 0.08, zc), (CW_T + 0.08, CW_WALK),
                                   (-(CW_T + 0.08), CW_WALK)], STONE)                  # projecting walkway course
    for i, x in enumerate((-1.5, -0.5, 0.5, 1.5)):                                      # merlons on both edges
        if (variant == 'end_l' and i == 0) or (variant == 'end_r' and i == 3):
            continue
        for side, h in zip((1, -1), CW_MERLON_H[i]):
            box(m, (x, side * (CW_T + 0.08 - CW_MERLON[1] / 2 - 0.04), CW_WALK), (CW_MERLON[0], CW_MERLON[1], h),
                STONE, top=('M_wall', 'stone_top'), skip=('bot',))
    for side in (1, -1):                                                                # buttress pier mid-module
        box(m, (0.0, side * (CW_T + 0.04), 0.0), (0.72, 0.52, 3.1), STONE, top=('M_wall', 'stone_top'), taper=0.86,
            skip=('bot',))
    return m


def build_curtain(name, variant, seed):
    m = curtain_module(variant)
    return to_object(name, m, build_curtain.mats, seed), m


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


BUDGET = {'stump': 80, 'guard_tower': 900, 'hall_wall': 200, 'hall_wall_tall': 260, 'banner': 60, 'brazier': 260,
          'rubble': 160, 'wall_broken': 160, 'curtain_wall': 200, 'curtain_wall_end': 200, 'curtain_wall_end_r': 200}


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
                     (build_hall_wall, 'hall_wall.glb'), (build_hall_wall_tall, 'hall_wall_tall.glb'),
                     (build_banner, 'banner.glb'),
                     (build_brazier, 'brazier.glb'), (build_rubble, 'rubble.glb'),
                     (build_wall_broken, 'wall_broken.glb'),
                     (lambda mt: build_curtain('curtain_wall', 'mid', 108), 'curtain_wall.glb'),
                     (lambda mt: build_curtain('curtain_wall_end', 'end_l', 109), 'curtain_wall_end.glb'),
                     (lambda mt: build_curtain('curtain_wall_end_r', 'end_r', 110), 'curtain_wall_end_r.glb')):
        build_curtain.mats = mats
        obj, m = fn(mats)
        report(obj, m)
        objs.append((obj, name))
    for obj, name in objs:
        export_one(obj, name)
        print('exported', os.path.join(OUT_DIR, name), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, 'props2.blend'), compress=True)


main()
