"""Turn outline-only logo line art into a filled, transparent game logo.

    python tools/make_logo.py textures/logo_dueling_pickles_lineart.png textures/logo_dueling_pickles.png

The source is black outlines on white. Light regions are labelled, then classified by nesting depth
across the outline strokes: the background touching the border is depth 0, the letter bodies it
touches through one stroke are depth 1 (filled), holes inside letters (the counters of D, P, ...) are
depth 2 (transparent), and so on alternating. DUELING (and the divider) get a vertical gold gradient
with a dark warm rim; PICKLES (regions below the divider) get a pickle-green skin (gradient, blotches,
little warts) with a dark green rim. No shadow is baked in (the game adds a crisp offset shadow in CSS).
"""
import sys
from collections import deque

import numpy as np
from PIL import Image
from scipy import ndimage

GOLD_TOP, GOLD_MID, GOLD_BOT = (255, 238, 170), (240, 190, 80), (178, 112, 34)
RIM = (38, 20, 8)
# PICKLES: pickle-skin green, light at the top to deep at the bottom, with blotches and warts.
PICKLE_TOP, PICKLE_MID, PICKLE_BOT = (196, 226, 110), (122, 176, 58), (58, 104, 30)
PICKLE_RIM = (20, 34, 10)
SPLIT = 0.56          # letter regions whose centre sits below this fraction of the art are PICKLES


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

    # Which filled regions are the word PICKLES (below the divider)?
    cy = ndimage.center_of_mass(np.ones_like(light), light, fill_ids)
    pickle_ids = [i for i, c in zip(fill_ids, cy) if c[0] > SPLIT * h]
    pickle = np.isin(light, pickle_ids)
    gold = fill & ~pickle

    def lerp(a, b, k):
        return np.array(a)[None, None, :] * (1 - k[..., None]) + np.array(b)[None, None, :] * k[..., None]

    def gradient(mask, c_top, c_mid, c_bot):
        rows = np.where(mask.any(axis=1))[0]
        y0, y1 = rows.min(), rows.max()
        t = np.broadcast_to(np.clip((np.arange(h) - y0) / max(1, (y1 - y0)), 0, 1)[:, None], (h, w))
        return np.where((t < 0.5)[..., None], lerp(c_top, c_mid, t * 2), lerp(c_mid, c_bot, (t - 0.5) * 2))

    # DUELING (+ divider): gold across its own height.
    rgb = gradient(gold, GOLD_TOP, GOLD_MID, GOLD_BOT)
    # PICKLES: green gradient + soft blotchy skin + raised warts (light bump, dark crescent below-right).
    green = gradient(pickle, PICKLE_TOP, PICKLE_MID, PICKLE_BOT)
    rng = np.random.default_rng(7)
    blotch = ndimage.gaussian_filter(rng.standard_normal((h, w)), 14)
    green = green * (1 + 0.9 * blotch / (np.abs(blotch).max() + 1e-9) * 0.12)[..., None]
    ys, xs = np.nonzero(ndimage.binary_erosion(pickle, iterations=10))
    yy, xx = np.mgrid[0:h, 0:w]
    for k in rng.choice(len(ys), size=min(70, len(ys)), replace=False):
        y, x = ys[k], xs[k]
        r = rng.uniform(4, 8)
        d_hi = (yy[y-12:y+13, x-12:x+13] - y) ** 2 + (xx[y-12:y+13, x-12:x+13] - x) ** 2
        d_lo = (yy[y-12:y+13, x-12:x+13] - y - r * 0.45) ** 2 + (xx[y-12:y+13, x-12:x+13] - x - r * 0.35) ** 2
        patch = green[y-12:y+13, x-12:x+13]
        patch[(d_lo < r * r) & (d_hi >= (r * 0.8) ** 2)] *= 0.72        # crescent shadow under the bump
        patch[d_hi < (r * 0.8) ** 2] = patch[d_hi < (r * 0.8) ** 2] * 1.12 + 10   # the bump catches light
    rgb = np.where(pickle[..., None], green, rgb)
    # Rims: warm dark on the gold word, dark green around PICKLES.
    near_pickle = ndimage.binary_dilation(pickle, iterations=stroke)
    rim = np.where(near_pickle[..., None], np.array(PICKLE_RIM)[None, None, :], np.array(RIM)[None, None, :])
    rgb = np.where(ink[..., None], rim, rgb)
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
