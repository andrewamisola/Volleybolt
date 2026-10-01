"""Pixel-first texture pipeline (owner, 2026-10-01: "pixelate it first, and then down-res" - the Abiotic Factor look).

Our source textures were low-res in pixel count but SMOOTH in content (soft gradients, anti-aliased edges), so at
the game's texel size they read as blurry big pixels. A pixel-first texture is built from crisp, distinct texels:

  1. PIXELATE  - area-average (box) the source into the final texel grid (every texel = the true average of its
                 patch, no interpolation smear),
  2. SHARPEN   - a wrap-aware unsharp mask so neighbouring texels separate instead of blending,
  3. PALETTE   - quantize to a small palette (no dithering): colour comes in crisp steps, never smooth ramps,
  4. MOTTLE    - a deterministic per-texel brightness jitter, the hand-made pixel grain,
  5. save at the final (low) resolution; the game samples it NEAREST (+ nearest mips) so texels stay hard.

Every operation wraps around the edges, so seamless sources stay seamless.

Originals are kept in textures/src/ (copied there on the first run) and are always the input, so re-running is safe.
Run:  python tools/pixelate_textures.py            (all)      python tools/pixelate_textures.py castle_wall rail
"""
import os, sys, shutil, random
from PIL import Image, ImageFilter, ImageEnhance

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'textures')
SRC = os.path.join(ROOT, 'src')

# name: (output size (w, h), palette colours, sharpen %, mottle +-, contrast)
JOBS = {
    'castle_wall':          ((64, 64), 24, 80, 0.06, 1.12),   # 64: fewer and the mortar lines vanish
    'tower_stone':          ((64, 64), 24, 80, 0.06, 1.12),
    'grass_field_seamless': ((128, 128), 24, 80, 0.08, 1.15),   # same count as before: only the look changes
    'dirt_road_seamless':   ((128, 128), 20, 70, 0.06, 1.12),
    'rail':                 ((128, 86), 20, 70, 0.06, 1.1),
}


def wrap_filter(img, flt):
    w, h = img.size
    big = Image.new(img.mode, (w * 3, h * 3))
    for i in range(3):
        for j in range(3):
            big.paste(img, (i * w, j * h))
    return big.filter(flt).crop((w, h, 2 * w, 2 * h))


def pixel_first(src, size, colors, sharpen, mottle, contrast, seed):
    im = src.convert('RGB')
    # 1. pixelate: box-average into the final grid
    im = im.resize(size, Image.BOX)
    # 2. separate neighbouring texels
    im = wrap_filter(im, ImageFilter.UnsharpMask(radius=1.2, percent=sharpen, threshold=0))
    im = ImageEnhance.Contrast(im).enhance(contrast)
    # 3. palette: crisp colour steps, no smooth ramps
    im = im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
    # 4. mottle: per-texel brightness jitter (deterministic)
    rng = random.Random(seed)
    px = im.load()
    for y in range(size[1]):
        for x in range(size[0]):
            k = 1.0 + (rng.random() * 2 - 1) * mottle
            r, g, b = px[x, y]
            px[x, y] = (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)))
    return im


def main(names):
    os.makedirs(SRC, exist_ok=True)
    for name in names:
        out = os.path.join(ROOT, name + '.png')
        src = os.path.join(SRC, name + '.png')
        if not os.path.exists(src):
            shutil.copy2(out, src)              # keep the original once; it's always the input
        size, colors, sharpen, mottle, contrast = JOBS[name]
        im = pixel_first(Image.open(src), size, colors, sharpen, mottle, contrast, seed=hash(name) & 0xffff)
        im.save(out)
        print(f'{name}: {Image.open(src).size} -> {size}, {colors} colours')


if __name__ == '__main__':
    main(sys.argv[1:] or list(JOBS))
