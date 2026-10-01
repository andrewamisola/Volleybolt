"""Build the forest-court PROPS (tree, pine, rock) in Blender and export them as small GLBs.

These replace the painted forest backdrop (textures/backdrop_forest.jpg): each GLB is loaded ONCE
in the game and cloned / instanced dozens of times with random Y-rotation + scale, so every prop is
cheap (tree <= ~400 tris, pine <= ~200, rock <= ~120) and reads from any yaw angle.

Run from the repo root:
    "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" -b --factory-startup ^
        --python tools/blender/build_props.py

Writes models/props/tree.glb, pine.glb, rock.glb (+ props.blend).

Conventions (same as build_gatehouse.py / build_castle.py):
    Blender +Z = up (glTF export_yup converts), origin on the ground (z = 0) at the prop's base
    centre, flat-shaded faceted polys, materials looked up BY NAME in the game, roughness 1,
    metallic 0, no textures. Per-corner vertex colours (COLOR_0) are a grey-ish MULTIPLIER over the
    material base colour: bright on up-facing facets, dark on undersides = the two-tone storybook
    look (lighter canopy tops, darker bellies) with zero extra materials.
Materials: M_bark (trunks), M_foliage (round deciduous canopy), M_pine (conifer needles),
           M_rock (boulder). The painted backdrop is graded dark/purple in-game, so these are the
           *lit* colours sampled from its facets, a touch brighter than the picture.
Scale: tree ~5.6 tall / ~3.6 canopy, pine ~5.8 tall / ~2.5 wide, rock ~1.25 x 1.0 x 0.8.
"""
import bpy, bmesh, math, random, os
from mathutils import Vector

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


MATS = ['M_bark', 'M_foliage', 'M_pine', 'M_rock']


def build_materials():
    return {
        'M_bark': make_mat('M_bark', lin('#6b4a30')),
        'M_foliage': make_mat('M_foliage', lin('#6aa04e')),   # lit facet of the round canopies
        'M_pine': make_mat('M_pine', lin('#5b9a62')),         # lit facet of the conifers
        'M_rock': make_mat('M_rock', lin('#9296a6')),         # cool blue-grey boulders
    }


# ---------------------------------------------------------------- mesh accumulator
class MB:
    """Verts + faces, each face tagged with (material, shade-kind, tint-seed)."""

    def __init__(self):
        self.v, self.f, self.mat, self.kind = [], [], [], []

    def vert(self, co):
        self.v.append(Vector(co))
        return len(self.v) - 1

    def face(self, idx, mat, kind):
        self.f.append(list(idx))
        self.mat.append(MATS.index(mat))
        self.kind.append(kind)

    def tri_count(self):
        return sum(len(f) - 2 for f in self.f)


def faceted_blob(m, center, radii, mat, kind, seed, jitter=0.16, subdiv=2):
    """Low-subdiv icosphere with jittered verts (shared jitter per vertex => watertight facets)."""
    rng = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    bm.verts.ensure_lookup_table()
    base = len(m.v)
    for v in bm.verts:
        d = v.co.normalized()
        k = 1.0 + (rng.random() - 0.5) * 2 * jitter
        p = Vector((d.x * radii[0] * k, d.y * radii[1] * k, d.z * radii[2] * k))
        m.vert(p + Vector(center))
    for f in bm.faces:
        m.face([base + v.index for v in f.verts], mat, kind)
    bm.free()


def cone(m, center, r_base, height, sides, mat, kind, seed, jitter=0.10, rot=0.0, tip_off=(0, 0),
         base_cap=True):
    """Faceted cone: ring of `sides` verts + a tip. Jittered radii/heights keep each tier irregular."""
    rng = random.Random(seed)
    cx, cy, cz = center
    ring = []
    for i in range(sides):
        a = rot + TAU * i / sides
        r = r_base * (1 + (rng.random() - 0.5) * 2 * jitter)
        dz = (rng.random() - 0.5) * 0.12 * height
        ring.append(m.vert((cx + r * math.cos(a), cy + r * math.sin(a), cz + dz)))
    tip = m.vert((cx + tip_off[0], cy + tip_off[1], cz + height))
    for i in range(sides):
        j = (i + 1) % sides
        m.face([ring[i], ring[j], tip], mat, kind)
    if base_cap:
        ctr = m.vert((cx, cy, cz))
        for i in range(sides):
            j = (i + 1) % sides
            m.face([ring[j], ring[i], ctr], mat, kind)


def trunk(m, rings, sides, mat, seed, bend=(0.0, 0.0), rot=0.0, jitter=0.07, top_cap=False):
    """Tapered, bent trunk. rings: [(z, radius)], bend = XY lean reached at the top (quadratic)."""
    rng = random.Random(seed)
    H = rings[-1][0]
    rs = []
    for (z, r) in rings:
        t = (z / H) ** 2
        ring = []
        for i in range(sides):
            a = rot + TAU * i / sides
            rr = r * (1 + (rng.random() - 0.5) * 2 * jitter)
            ring.append(m.vert((bend[0] * t + rr * math.cos(a), bend[1] * t + rr * math.sin(a), z)))
        rs.append(ring)
    for k in range(len(rs) - 1):
        for i in range(sides):
            j = (i + 1) % sides
            m.face([rs[k][i], rs[k][j], rs[k + 1][j], rs[k + 1][i]], mat, 'bark')
    if top_cap:
        m.face(rs[-1][::-1], mat, 'bark')
    return rs


# ---------------------------------------------------------------- vertex-colour shading
def shade(kind, nrm, co, tint):
    """Return an RGB multiplier in [0, 1]. nrm = outward face normal (z up), tint = per-face random."""
    up = nrm.z * 0.5 + 0.5                         # 0 underside .. 1 top
    if kind == 'bark':
        v = 0.82 + 0.18 * min(1.0, co.z / 2.2) + 0.08 * (tint - 0.5)
        return (v, v * 0.97, v * 0.92)
    if kind == 'canopy':
        v = 0.52 + 0.48 * up ** 1.1 + 0.10 * (tint - 0.5)
        return (v * 0.97, v, v * 0.90)
    if kind == 'pine':
        # tier undersides very dark, tops bright; also a gentle height ramp up the whole tree
        v = (0.52 + 0.48 * up ** 1.1) * (0.88 + 0.12 * min(1.0, co.z / 5.0)) + 0.12 * (tint - 0.5)
        return (v * 0.96, v, v * 0.98)
    if kind == 'rock':
        v = 0.50 + 0.50 * up ** 1.1 + 0.12 * (tint - 0.5)
        return (v * 0.98, v * 0.99, v)
    return (1, 1, 1)


def to_object(name, m, mats, seed):
    # Orient each face outward: faces are authored CCW-from-outside; double-check against the
    # prop's own centre-ish pivot is unnecessary, but guard against inward windings for blobs.
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in m.v], [], m.f)
    for key in MATS:
        me.materials.append(mats[key])
    me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    me.update()
    rng = random.Random(seed)
    cols = []
    for pi, p in enumerate(me.polygons):
        tint = rng.random()
        nrm = p.normal
        for li in p.loop_indices:
            c = shade(m.kind[pi], nrm, m.v[me.loops[li].vertex_index], tint)
            cols += (c[0], c[1], c[2], 1.0)
    me.polygons.foreach_set('material_index', m.mat)
    me.polygons.foreach_set('use_smooth', [False] * len(me.polygons))
    me.color_attributes['Col'].data.foreach_set('color', cols)
    me.color_attributes.active_color = me.color_attributes['Col']
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def fix_normals_outward(obj, pivot_fn):
    """Flip any polygon whose normal points toward its own local 'inside' reference point."""
    me = obj.data
    flip = []
    for p in me.polygons:
        ref = pivot_fn(p.center)
        if (p.center - ref).dot(p.normal) < 0:
            flip.append(p.index)
    if flip:
        bm = bmesh.new()
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        for i in flip:
            bm.faces[i].normal_flip()
        bm.to_mesh(me)
        bm.free()
        me.update()
    return len(flip)


# ---------------------------------------------------------------- the props
def build_tree(mats):
    """Round, puffy deciduous tree: bent tapered trunk + a big faceted canopy blob with 3 smaller
    satellite blobs (like the painting's clustered canopies). ~5.6 tall, ~3.6 canopy."""
    m = MB()
    trunk(m, [(0.0, 0.42), (0.35, 0.30), (1.4, 0.22), (2.5, 0.19), (3.3, 0.17)], 6, 'M_bark', 11,
          bend=(0.30, -0.12), rot=0.3)
    # (centre, radii, seed)  -- bottoms stay high enough to show trunk, tops dome out
    faceted_blob(m, (0.20, -0.05, 3.85), (1.55, 1.50, 1.30), 'M_foliage', 'canopy', 21, jitter=0.12)
    faceted_blob(m, (1.05, 0.35, 3.05), (0.95, 0.95, 0.80), 'M_foliage', 'canopy', 22, jitter=0.14)
    faceted_blob(m, (-0.95, -0.50, 3.10), (0.90, 0.90, 0.78), 'M_foliage', 'canopy', 23, jitter=0.14)
    faceted_blob(m, (-0.05, 0.25, 4.80), (0.95, 0.90, 0.76), 'M_foliage', 'canopy', 24, jitter=0.14)
    obj = to_object('tree', m, mats, 311)
    return obj, m


def build_pine(mats):
    """Faceted conifer: short trunk + 4 stacked 8-sided cone tiers, shrinking upward."""
    m = MB()
    trunk(m, [(0.0, 0.34), (0.3, 0.24), (1.4, 0.19)], 6, 'M_bark', 31, bend=(0.06, 0.04), rot=0.2)
    # (z base, base radius, height)
    tiers = [(0.95, 1.30, 1.85), (2.20, 1.05, 1.70), (3.40, 0.80, 1.60), (4.50, 0.52, 1.40)]
    for i, (z, r, h) in enumerate(tiers):
        cone(m, (0.0, 0.0, z), r, h, 8, 'M_pine', 'pine', 40 + i, jitter=0.09, rot=0.4 * i,
             tip_off=(0.04 * (i % 2 - 0.5), 0.04 * (0.5 - i % 2)))
    obj = to_object('pine', m, mats, 411)
    return obj, m


def build_rock(mats):
    """Faceted boulder: icosphere (Blender subdivisions=2 = 80 tris), jittered, squashed, bottom flattened so it
    sits on the ground. ~1.25 wide."""
    rng = random.Random(7)
    m = MB()
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    bm.verts.ensure_lookup_table()
    pts = []
    for v in bm.verts:
        d = v.co.normalized()
        k = 1.0 + (rng.random() - 0.5) * 2 * 0.22
        pts.append(Vector((d.x * 0.58 * k, d.y * 0.52 * k, d.z * 0.46 * k)))
    # lean the whole thing a hair so it isn't axis-symmetric, flatten the bottom, rest on z=0
    zs = [p.z for p in pts]
    zmin = min(zs)
    floor = zmin * 0.55                             # chop the bottom 45% -> a flat contact patch
    pts = [Vector((p.x + 0.05 * p.z, p.y, max(p.z, floor) - floor)) for p in pts]
    for p in pts:
        m.vert(p)
    for f in bm.faces:
        m.face([v.index for v in f.verts], 'M_rock', 'rock')
    bm.free()
    obj = to_object('rock', m, mats, 511)
    print('rock flipped faces:', fix_normals_outward(obj, lambda c: Vector((0.0, 0.0, 0.3))))
    return obj, m


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


def report(obj, m):
    xs = [v.x for v in m.v]
    ys = [v.y for v in m.v]
    zs = [v.z for v in m.v]
    print(f'{obj.name}: {len(m.f)} faces, {m.tri_count()} tris, verts {len(m.v)}, '
          f'size x {max(xs) - min(xs):.2f} y {max(ys) - min(ys):.2f} z {max(zs) - min(zs):.2f}, '
          f'z range {min(zs):.2f}..{max(zs):.2f}, x {min(xs):.2f}..{max(xs):.2f}, '
          f'y {min(ys):.2f}..{max(ys):.2f}', flush=True)


def main():
    reset_scene()
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    mats = build_materials()
    objs = []
    for fn, name in ((build_tree, 'tree.glb'), (build_pine, 'pine.glb'), (build_rock, 'rock.glb')):
        obj, m = fn(mats)
        report(obj, m)
        objs.append((obj, name))
    for obj, name in objs:
        export_one(obj, name)
        print('exported', os.path.join(OUT_DIR, name), flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, 'props.blend'), compress=True)


main()
