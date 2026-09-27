"""Strip a GLB down to its node hierarchy + animations (no meshes, skins, materials, images).

The pickle animation clips (models/pickle/pickle_*.glb) each embed a ~6.7 MB texture and a
decimated mesh, but the game only ever calls ImportAnimations on them — Babylon still downloads,
parses and uploads that texture before throwing it away. The stripped copies keep every node
(same names, same TRS) so clips still retarget by node name exactly as before.

Usage:  python tools/strip_anim_glb.py            # models/pickle/pickle_*.glb -> models/pickle/clips/
The originals are left untouched (capture_viewer.html renders their meshes directly).
"""
import json, struct, pathlib, sys

SRC = pathlib.Path('models/pickle')
DST = SRC / 'clips'
CLIPS = ['pickle_left', 'pickle_right', 'pickle_cast', 'pickle_cast_release', 'pickle_victory', 'pickle_defeat']


def read_glb(path):
    b = path.read_bytes()
    magic, version, _ = struct.unpack('<III', b[:12])
    assert magic == 0x46546C67 and version == 2, f'{path}: not a glTF 2.0 binary'
    off, gltf, bin_chunk = 12, None, b''
    while off < len(b):
        length, ctype = struct.unpack('<II', b[off:off + 8])
        data = b[off + 8:off + 8 + length]
        if ctype == 0x4E4F534A:
            gltf = json.loads(data)
        elif ctype == 0x004E4942:
            bin_chunk = data
        off += 8 + length
    return gltf, bin_chunk


def write_glb(path, gltf, bin_chunk):
    js = json.dumps(gltf, separators=(',', ':')).encode()
    js += b' ' * (-len(js) % 4)
    bin_chunk += b'\0' * (-len(bin_chunk) % 4)
    body = struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(bin_chunk), 0x004E4942) + bin_chunk
    path.write_bytes(struct.pack('<III', 0x46546C67, 2, 12 + len(body)) + body)


def strip(gltf, bin_chunk):
    # Keep only the accessors the animation samplers read, re-packed into a fresh buffer.
    used = sorted({i for a in gltf['animations'] for s in a['samplers'] for i in (s['input'], s['output'])})
    remap, accessors, views, blob = {}, [], [], bytearray()
    for old in used:
        acc = dict(gltf['accessors'][old])
        assert 'sparse' not in acc, 'sparse accessors not supported'
        view = gltf['bufferViews'][acc['bufferView']]
        start = view.get('byteOffset', 0)
        blob += b'\0' * (-len(blob) % 4)
        views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': view['byteLength']})
        blob += bin_chunk[start:start + view['byteLength']]
        acc['bufferView'] = len(views) - 1
        remap[old] = len(accessors)
        accessors.append(acc)

    animations = []
    for a in gltf['animations']:
        a = json.loads(json.dumps(a))
        for s in a['samplers']:
            s['input'], s['output'] = remap[s['input']], remap[s['output']]
        animations.append(a)

    nodes = [{k: v for k, v in n.items() if k not in ('mesh', 'skin')} for n in gltf['nodes']]
    out = {'asset': gltf['asset'], 'scenes': gltf['scenes'], 'nodes': nodes, 'animations': animations,
           'accessors': accessors, 'bufferViews': views, 'buffers': [{'byteLength': len(blob)}]}
    if 'scene' in gltf:
        out['scene'] = gltf['scene']
    return out, bytes(blob)


def main():
    DST.mkdir(exist_ok=True)
    for name in CLIPS:
        src = SRC / f'{name}.glb'
        gltf, bin_chunk = read_glb(src)
        out, blob = strip(gltf, bin_chunk)
        dst = DST / f'{name}.glb'
        write_glb(dst, out, blob)
        print(f'{src} ({src.stat().st_size:,} B) -> {dst} ({dst.stat().st_size:,} B)')


if __name__ == '__main__':
    sys.exit(main())
