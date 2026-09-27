"""Make a tiling texture seamless and flatten its large-scale tone, so repeats don't show.

    python tools/make_seamless.py textures/grass_field.png [more.png ...]

Writes <name>_seamless.png next to each input. Two steps:
  1. Offset blend: the texture is mixed with a copy of itself rolled by half its size. The weight
     is 1 in the middle and 0 at the edges, so the edges come from the rolled copy, whose pixels at
     the wrap boundary were neighbours in the original: the texture wraps without a seam.
  2. Tone flattening: the very low-frequency brightness (a wide wrapped blur) is divided out and
     replaced by the image mean, so one side of a tile isn't darker than the other. That gradient
     is what makes repeats read as a grid of blocks even when the edges match.
"""
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter


def seamless(path):
    im = Image.open(path).convert('RGBA')
    a = np.asarray(im).astype(np.float64)
    rgb, alpha = a[..., :3], a[..., 3:]
    h, w = rgb.shape[:2]

    # 1. offset blend
    rolled = np.roll(np.roll(rgb, h // 2, axis=0), w // 2, axis=1)
    wy = 1 - np.abs(np.linspace(-1, 1, h))[:, None]
    wx = 1 - np.abs(np.linspace(-1, 1, w))[None, :]
    weight = np.clip(np.minimum(wy, wx) * 2.2, 0, 1)[..., None]     # wide plateau of the original
    out = rgb * weight + rolled * (1 - weight)

    # 2. flatten large-scale tone (wrapped blur so the correction itself tiles)
    lum = out.mean(axis=2)
    low = gaussian_filter(lum, sigma=max(h, w) / 6, mode='wrap')
    out = out * (lum.mean() / np.maximum(low, 1))[..., None]

    res = np.concatenate([np.clip(out, 0, 255), alpha], axis=2).astype(np.uint8)
    dst = path.rsplit('.', 1)[0] + '_seamless.png'
    Image.fromarray(res, 'RGBA').save(dst)
    return dst


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print('wrote', seamless(p))
