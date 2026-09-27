"""Turn outline-only logo line art into a filled, transparent game logo.

    python tools/make_logo.py textures/logo_dueling_pickles_lineart.png textures/logo_dueling_pickles.png

The source is black outlines on white. Light regions are labelled, then classified by nesting depth
across the outline strokes: the background touching the border is depth 0, the letter bodies it
touches through one stroke are depth 1 (filled), holes inside letters (the counters of D, P, ...) are
depth 2 (transparent), and so on alternating. Letter bodies get a vertical gold gradient, the strokes
become a dark warm rim. No shadow is baked in (the game adds a crisp offset shadow in CSS).
"""
import sys
from collections import deque

import numpy as np
from PIL import Image
from scipy import ndimage

GOLD_TOP, GOLD_MID, GOLD_BOT = (255, 238, 170), (240, 190, 80), (178, 112, 34)
RIM = (38, 20, 8)


def main(src, dst):
    g = np.asarray(Image.open(src).convert('L')).astype(np.float64)
    ink = g < 140                                    # outline strokes
    light, n = ndimage.label(~ink)
    h, w = g.shape

    # Outside = every component touching the border.
    border = set(np.unique(np.concatenate([light[0], light[-1], light[:, 0], light[:, -1]]))) - {0}
    # Adjacency across a stroke: dilate each component a little past the stroke width.
    stroke = 9
    struct = np.ones((3, 3), bool)
    objs = ndimage.find_objects(light)
    adj = {i: set() for i in range(1, n + 1)}
    for i, sl in enumerate(objs, start=1):
        if sl is None:
            continue
        ys = slice(max(sl[0].start - stroke, 0), min(sl[0].stop + stroke, h))
        xs = slice(max(sl[1].start - stroke, 0), min(sl[1].stop + stroke, w))
        sub = light[ys, xs]
        grown = ndimage.binary_dilation(sub == i, struct, iterations=stroke)
        ring = sub[grown & (sub != i)]
        ring = ring[ring > 0]
        if ring.size == 0:
            continue
        labels, counts = np.unique(ring, return_counts=True)
        # Neighbours only across a real stretch of shared outline: where letters' outlines merge at
        # a pinch point, a pocket touches its far side over a few pixels only, and counting that
        # would flip the pocket and the letter in the nesting (the pocket between I and C filled).
        for j, c in zip(labels, counts):
            if c >= max(80, 0.12 * ring.size):
                adj[i].add(int(j))
                adj.setdefault(int(j), set()).add(i)
    depth = {b: 0 for b in border}
    q = deque(border)
    while q:
        c = q.popleft()
        for j in adj[c]:
            if j not in depth:
                depth[j] = depth[c] + 1
                q.append(j)
    fill_ids = [i for i, d in depth.items() if d % 2 == 1]
    fill = np.isin(light, fill_ids)
    # Tiny specks the classifier missed (anti-alias islands) inherit from their surroundings via closing.
    fill = ndimage.binary_closing(fill | ink, iterations=1) & ~ink | fill
    body = fill | ink
    # Keep strokes that belong to the logo (touching a filled region), not stray marks.
    body = ndimage.binary_closing(body, iterations=1)

    # Colours: vertical gold gradient across the logo's height, dark rim on the strokes.
    rows = np.where(body.any(axis=1))[0]
    y0, y1 = rows.min(), rows.max()
    t = np.clip((np.arange(h) - y0) / max(1, (y1 - y0)), 0, 1)[:, None]
    def lerp(a, b, k):
        return np.array(a)[None, None, :] * (1 - k[..., None]) + np.array(b)[None, None, :] * k[..., None]
    top = np.broadcast_to(t, (h, w))
    grad = np.where((top < 0.5)[..., None], lerp(GOLD_TOP, GOLD_MID, top * 2), lerp(GOLD_MID, GOLD_BOT, (top - 0.5) * 2))
    rgb = np.where(ink[..., None], np.array(RIM)[None, None, :], grad)
    alpha = body.astype(np.float64)

    # No baked halo: the game adds a crisp FF9-style offset shadow in CSS where it's needed.
    out_a = alpha
    out_rgb = rgb
    out = np.dstack([out_rgb, out_a * 255]).clip(0, 255).astype(np.uint8)

    im = Image.fromarray(out, 'RGBA')
    im = im.crop(im.getbbox())
    im.save(dst)
    print('wrote', dst, im.size, 'filled regions', len(fill_ids), 'holes', sum(1 for d in depth.values() if d and d % 2 == 0))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
