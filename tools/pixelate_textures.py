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
    'grass_field_seamless': ((128, 128), 64, 35, 0.03, 1.04),   # same count as before: only the look changes
    'dirt_road_seamless':   ((128, 128), 64, 30, 0.025, 1.03),
    'rail':                 ((128, 86), 20, 70, 0.06, 1.1),
    'wood_planks':          ((32, 32), 12, 60, 0.05, 1.08),   # generated (wood_source); shared by every structure
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


def wood_source(seed=11):
    """Weathered timber drawn at 4x (128x128, seamless) for the pixel-first pass -> 32x32: u = ALONG the grain;
    four boards (32px bands) with dark seams, a lit top bevel, long wavy grain streaks, a few knots."""
    import math
    rng = random.Random(seed)
    S = 128
    im = Image.new('RGB', (S, S))
    px = im.load()
    tone = [0.86 + 0.24 * rng.random() for _ in range(4)]
    phase = [rng.random() * S for _ in range(S)]
    amp = [0.04 + 0.12 * rng.random() for _ in range(S)]
    knots = [(rng.randrange(S), 32 * b + 8 + rng.randrange(16)) for b in range(4) if rng.random() < 0.7]
    base = (0.50, 0.36, 0.24)
    for y in range(S):
        board, yb = y // 32, y % 32
        for x in range(S):
            if yb >= 29:
                px[x, y] = (43, 28, 18); continue                     # seam
            t = 0.84 if yb < 3 else 1.0                             # lit bevel
            w = math.sin((x + phase[y // 2 * 2]) * 2 * math.pi / S * 2) * amp[y // 2 * 2]
            fine = 0.06 * math.sin(x * 2 * math.pi / S * 9 + y * 0.7)
            k = 1.0
            for kx, ky in knots:
                dx = min(abs(x - kx), S - abs(x - kx)); dy = abs(y - ky)
                q = dx * dx + dy * dy * 4
                if q <= 64: k = min(k, 0.55 + 0.45 * q / 64)
            g = tone[board] * (1.0 + w + fine) * k * t
            px[x, y] = tuple(int(min(1.0, c * g) * 255) for c in base)
    return im


def main(names):
    os.makedirs(SRC, exist_ok=True)
    for name in names:
        out = os.path.join(ROOT, name + '.png')
        if name == 'wood_planks':                 # generated source (no file to keep)
            size, colors, sharpen, mottle, contrast = JOBS[name]
            pixel_first(wood_source(), size, colors, sharpen, mottle, contrast, seed=5).save(out)
            print('wood_planks: generated 128 -> 32')
            continue
        src = os.path.join(SRC, name + '.png')
        if not os.path.exists(src):
            shutil.copy2(out, src)              # keep the original once; it's always the input
        size, colors, sharpen, mottle, contrast = JOBS[name]
        im = pixel_first(Image.open(src), size, colors, sharpen, mottle, contrast, seed=hash(name) & 0xffff)
        im.save(out)
        print(f'{name}: {Image.open(src).size} -> {size}, {colors} colours')


if __name__ == '__main__':
    main(sys.argv[1:] or list(JOBS))
