"""Face strips for the modular pickle (spec: docs/superpowers/specs/2026-10-01-modular-pickle-design.md §2).

Pixel art drawn directly at native resolution (crisp, no anti-aliasing, tiny palette), transparent background:
  textures/face/eyes_<id>.png  - 5 frames of 48x20: open, blink, hurt, focus, happy
  textures/face/brows_<id>.png - 5 frames of 48x9, same states as the eyes
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
LID = (28, 22, 30, 96)           # translucent: darkens whatever skin is under it

EW, EH = 48, 20                  # eye frame
BW, BH = 48, 9                   # brow frame (same 5 states as the eyes, drawn above them)
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


def _hurt(d, x, y, i, r=6):
    """> < squeeze, shared by every eye style."""
    s = 1 if i == 0 else -1
    d.line((x - r * s, y - r + 1, x + (r - 1) * s, y, x - r * s, y + r - 1), fill=INK, width=2)


def eyes_beady():
    """Small dot eyes, wide apart: deadpan. Tiny shine."""
    im = Image.new('RGBA', (EW * 5, EH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    centres = [(12, 11), (36, 11)]
    for f in range(5):
        ox = f * EW
        for i, (cx, cy) in enumerate(centres):
            x, y = ox + cx, cy
            if f == 0:      # open: a black bead
                d.ellipse((x - 3, y - 4, x + 3, y + 4), fill=INK)
                d.point((x - 1, y - 2), fill=SHINE)
            elif f == 1:    # blink
                d.line((x - 4, y + 1, x + 4, y + 1), fill=INK, width=2)
            elif f == 2:
                _hurt(d, x, y, i, 5)
            elif f == 3:    # focus: a narrower bead (the brows layer does the frown)
                d.ellipse((x - 3, y - 2, x + 3, y + 5), fill=INK)
                d.point((x - 1, y), fill=SHINE)
            elif f == 4:    # happy: small arcs
                d.line((x - 4, y + 2, x, y - 2, x + 4, y + 2), fill=INK, width=2)
    return im


def eyes_sleepy():
    """Heavy-lidded: the top of each eye is cut by a thick lid line, pupils sit low. Unbothered."""
    im = Image.new('RGBA', (EW * 5, EH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    centres = [(13, 10), (35, 10)]
    for f in range(5):
        ox = f * EW
        for i, (cx, cy) in enumerate(centres):
            x, y = ox + cx, cy
            if f in (0, 3):  # open / focus: a shaded lid over the top half, pupils sit low
                d.ellipse((x - 8, y - 7, x + 8, y + 8), fill=INK)
                d.ellipse((x - 7, y - 6, x + 7, y + 7), fill=WHITE)
                px = x + (2 if i == 0 else -2)
                d.ellipse((px - 3, y + 2, px + 3, y + 7), fill=INK)
                d.point((px - 1, y + 3), fill=SHINE)
                # the lid: translucent ink, so it reads as darker skin whatever the pickle's colour
                tilt = 0 if f == 0 else (2 if i == 0 else -2)   # focus tilts the lid toward the nose
                for xx in range(x - 7, x + 8):
                    ly = y + 1 + round(tilt * (xx - x) / 8)
                    for yy in range(y - 6, ly + 2):     # +2: no white specks where the tilted lid line steps
                        if im.getpixel((xx, yy))[3]:
                            im.putpixel((xx, yy), LID)
                d.arc((x - 8, y - 7, x + 8, y + 8), 180, 360, fill=INK)
                d.line((x - 8, y + 1 - tilt, x + 8, y + 1 + tilt), fill=INK, width=2)
            elif f == 1:    # blink: droopy closed curve
                d.line((x - 7, y + 2, x - 3, y + 4, x + 3, y + 4, x + 7, y + 2), fill=INK, width=2)
            elif f == 2:
                _hurt(d, x, y + 1, i)
            elif f == 4:    # happy: content closed smile-eyes
                d.line((x - 7, y + 1, x - 3, y - 2, x + 3, y - 2, x + 7, y + 1), fill=INK, width=2)
    return im


def eyes_shiny():
    """Big tall anime eyes: coloured iris, two shine dots. Cute and earnest."""
    IRIS = (54, 84, 150, 255)
    IRIS_LO = (98, 150, 210, 255)
    im = Image.new('RGBA', (EW * 5, EH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    centres = [(13, 10), (35, 10)]
    for f in range(5):
        ox = f * EW
        for i, (cx, cy) in enumerate(centres):
            x, y = ox + cx, cy
            if f in (0, 3):  # open / focus
                top = y - 9 if f == 0 else y - 5
                d.ellipse((x - 7, top, x + 7, y + 9), fill=INK)
                d.ellipse((x - 6, top + 1, x + 6, y + 8), fill=WHITE)
                px = x + (1 if i == 0 else -1)
                d.ellipse((px - 5, top + 2, px + 5, y + 8), fill=IRIS)
                d.rectangle((px - 4, y + 4, px + 4, y + 7), fill=IRIS_LO)        # lit lower iris
                d.ellipse((px - 2, y - 2, px + 2, y + 3), fill=INK)               # pupil
                d.rectangle((px - 4, top + 3, px - 2, top + 5), fill=SHINE)       # big shine
                d.point((px + 3, y + 5), fill=SHINE)                              # small shine
            elif f == 1:    # blink
                d.line((x - 7, y + 2, x - 3, y + 4, x + 3, y + 4, x + 7, y + 2), fill=INK, width=2)
            elif f == 2:
                _hurt(d, x, y, i, 7)
            elif f == 4:    # happy: tall ^ ^
                d.line((x - 7, y + 4, x, y - 5, x + 7, y + 4), fill=INK, width=2)
    return im


# Brow shapes per eye state, for the LEFT brow as (outer, mid, inner) heights in the 9px frame (0 = top);
# the right brow mirrors it. Brows carry most of the emotion: worried when hurt, a frown when focusing.
BROW_POSE = {
    0: (5, 4, 5),   # open: a soft arch
    1: (6, 5, 6),   # blink: relaxed, a touch lower
    2: (6, 4, 2),   # hurt: inner ends up (worried)
    3: (2, 4, 6),   # focus: inner ends down (frown)
    4: (3, 1, 3),   # happy: raised arch
}
BROW_CX = (13, 35)


def _curve(pts):
    """Per-column top y along a polyline of (x, y) control points, sorted by x: a quadratic through each
    run of three (a smooth arch), linear for two. Clean pixel columns, no line-joint ticks."""
    pts = sorted(pts)
    cols = {}
    for k in range(0, len(pts) - 1, 2):
        seg = pts[k:k + 3]
        x0, x1 = seg[0][0], seg[-1][0]
        for x in range(x0, x1 + 1):
            if len(seg) == 3:
                (a, ya), (m, ym), (c, yc) = seg
                la = (x - m) * (x - c) / ((a - m) * (a - c))
                lm = (x - a) * (x - c) / ((m - a) * (m - c))
                lc = (x - a) * (x - m) / ((c - a) * (c - m))
                y = ya * la + ym * lm + yc * lc
            else:
                (a, ya), (c, yc) = seg
                y = ya + (yc - ya) * (x - a) / (c - a)
            cols[x] = round(y)
    return cols


def _brow_pts(ox, i, pose, half=6):
    """The brow control points for eye i (0 = left) in frame ox: outer, mid, inner."""
    outer, mid, inner = pose
    x = ox + BROW_CX[i]
    s = 1 if i == 0 else -1          # +x points to the nose for the left brow
    return [(x - half * s, outer), (x, mid), (x + half * s, inner)]


def _fill_cols(d, cols, thick):
    """thick: int, or f(x) -> int."""
    for x, y in cols.items():
        t = thick(x) if callable(thick) else thick
        d.line((x, y, x, y + t - 1), fill=INK)


def brows_classic():
    """Thin 2px arched brows."""
    im = Image.new('RGBA', (BW * 5, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for f in range(5):
        for i in range(2):
            _fill_cols(d, _curve(_brow_pts(f * BW, i, BROW_POSE[f])), 2)
    return im


def brows_bushy():
    """Chunky brows: 4px at the inner end tapering to 2px at the outer."""
    im = Image.new('RGBA', (BW * 5, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for f in range(5):
        for i in range(2):
            pts = _brow_pts(f * BW, i, BROW_POSE[f], 7)
            outer_x, inner_x = pts[0][0], pts[2][0]
            thick = lambda x: 2 + round(2 * (x - outer_x) / (inner_x - outer_x))
            _fill_cols(d, _curve(pts), thick)
    return im


def brows_unibrow():
    """One continuous brow across both eyes: dips at the middle when frowning, peaks when worried."""
    im = Image.new('RGBA', (BW * 5, BH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for f in range(5):
        lo, lm, li = _brow_pts(f * BW, 0, BROW_POSE[f], 7)
        ri, rm, ro = list(reversed(_brow_pts(f * BW, 1, BROW_POSE[f], 7)))
        ri, ro = ro, ri                                   # _brow_pts gives outer->inner; want left->right
        mid_y = li[1] + (1 if f == 3 else -1 if f in (2, 4) else 0)
        cols = _curve([lo, lm, li])
        cols.update(_curve([li, (f * BW + 24, mid_y), ri]))
        cols.update(_curve([ri, rm, ro]))
        _fill_cols(d, cols, 3)
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
    eyes_beady().save(os.path.join(OUT, 'eyes_beady.png'))
    eyes_sleepy().save(os.path.join(OUT, 'eyes_sleepy.png'))
    eyes_shiny().save(os.path.join(OUT, 'eyes_shiny.png'))
    brows_classic().save(os.path.join(OUT, 'brows_classic.png'))
    brows_bushy().save(os.path.join(OUT, 'brows_bushy.png'))
    brows_unibrow().save(os.path.join(OUT, 'brows_unibrow.png'))
    mouth_smile().save(os.path.join(OUT, 'mouth_smile.png'))
    print('faces written to', OUT)
