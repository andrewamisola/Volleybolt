"""Face strips for the modular pickle (spec: docs/superpowers/specs/2026-10-01-modular-pickle-design.md §2).

Pixel art drawn directly at native resolution (crisp, no anti-aliasing, tiny palette), transparent background:
  textures/face/eyes_<id>.png  - 5 frames of 48x20: open, blink, hurt, focus, happy
  textures/face/mouth_<id>.png - 4 frames of 32x14: neutral, open, grimace, grin
Run: python tools/build_faces.py
"""
import os
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'textures', 'face')
INK = (28, 22, 30, 255)          # outline / pupils
WHITE = (246, 244, 232, 255)
SHINE = (255, 255, 255, 255)
MOUTH = (92, 28, 38, 255)        # inside of the mouth
TONGUE = (214, 92, 96, 255)
TEETH = (240, 238, 226, 255)

EW, EH = 48, 20                  # eye frame
MW, MH = 32, 14                  # mouth frame


def eyes_classic():
    """Derpy round eyes (the old pickle's): big white ovals, black pupils looking slightly inward, a shine pixel."""
    im = Image.new('RGBA', (EW * 5, EH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    centres = [(13, 10), (35, 10)]
    for f in range(5):
        ox = f * EW
        for i, (cx, cy) in enumerate(centres):
            x, y = ox + cx, cy
            if f == 0:      # open
                d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=INK)
                d.ellipse((x - 7, y - 7, x + 7, y + 7), fill=WHITE)
                px = x + (2 if i == 0 else -2)
                d.ellipse((px - 4, y - 3, px + 3, y + 4), fill=INK)
                d.point((px - 2, y - 2), fill=SHINE); d.point((px - 1, y - 2), fill=SHINE)
            elif f == 1:    # blink: closed lids, a soft curve
                d.line((x - 7, y + 1, x - 3, y + 3, x + 3, y + 3, x + 7, y + 1), fill=INK, width=2)
            elif f == 2:    # hurt: > <
                s = 1 if i == 0 else -1
                d.line((x - 6 * s, y - 5, x + 5 * s, y, x - 6 * s, y + 5), fill=INK, width=2)
            elif f == 3:    # focus: half-lidded, angry brow
                d.ellipse((x - 8, y - 4, x + 8, y + 8), fill=INK)
                d.ellipse((x - 7, y - 3, x + 7, y + 7), fill=WHITE)
                px = x + (2 if i == 0 else -2)
                d.ellipse((px - 3, y - 1, px + 3, y + 5), fill=INK)
                d.rectangle((x - 8, y - 6, x + 8, y), fill=(0, 0, 0, 0))
                if i == 0: d.line((x - 8, y - 4, x + 7, y), fill=INK, width=2)
                else:      d.line((x - 7, y, x + 8, y - 4), fill=INK, width=2)
            elif f == 4:    # happy: ^ ^
                d.line((x - 7, y + 3, x, y - 4, x + 7, y + 3), fill=INK, width=2)
    return im


def mouth_smile():
    im = Image.new('RGBA', (MW * 4, MH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for f in range(4):
        ox = f * MW
        cx, cy = ox + 16, 6
        if f == 0:          # neutral: a small derpy smile
            d.line((cx - 7, cy - 1, cx - 4, cy + 2, cx + 4, cy + 2, cx + 7, cy - 1), fill=INK, width=2)
        elif f == 1:        # open: little O
            d.ellipse((cx - 5, cy - 4, cx + 5, cy + 6), fill=INK)
            d.ellipse((cx - 3, cy - 2, cx + 3, cy + 4), fill=MOUTH)
            d.rectangle((cx - 2, cy + 2, cx + 2, cy + 4), fill=TONGUE)
        elif f == 2:        # grimace: gritted teeth
            d.rectangle((cx - 9, cy - 3, cx + 9, cy + 4), fill=INK)
            d.rectangle((cx - 8, cy - 2, cx + 8, cy + 3), fill=TEETH)
            for tx in range(cx - 5, cx + 8, 4):
                d.line((tx, cy - 2, tx, cy + 3), fill=INK)
            d.line((cx - 8, cy, cx + 8, cy), fill=INK)
        elif f == 3:        # grin: wide open D with tongue
            d.chord((cx - 10, cy - 8, cx + 10, cy + 8), 0, 180, fill=INK)
            d.chord((cx - 8, cy - 6, cx + 8, cy + 6), 0, 180, fill=MOUTH)
            d.rectangle((cx - 7, cy, cx + 7, cy + 1), fill=TEETH)
            d.ellipse((cx - 3, cy + 3, cx + 4, cy + 7), fill=TONGUE)
    return im


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    eyes_classic().save(os.path.join(OUT, 'eyes_classic.png'))
    mouth_smile().save(os.path.join(OUT, 'mouth_smile.png'))
    print('faces written to', OUT)
