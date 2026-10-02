"""Face strips for the modular pickle (spec: docs/superpowers/specs/2026-10-01-modular-pickle-design.md §2).

Pixel art drawn directly at native resolution (crisp, no anti-aliasing, tiny palette), transparent background:
  textures/face/eyes_<id>.png  - 5 frames of 48x20: open, blink, hurt, focus, happy
  textures/face/brows_<id>.png - 5 frames of 48x9, same states as the eyes
  textures/face/fhair_<id>.png - 1 frame of 64x32 (facial hair, drawn over the mouth at canvas y 30)
  textures/face/feat_<id>.png  - 1 frame of 64x64 (cheek features, drawn on the skin under everything)
  textures/face/mouth_<id>.png - 4 frames of 32x14: neutral, open, grimace, grin
Run: python tools/build_faces.py
"""
import os
import random
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
            elif f == 3:    # focus: a squint - the lid slants down toward the nose, cut INSIDE the eye
                d.ellipse((x - 8, y - 6, x + 8, y + 8), fill=INK)
                d.ellipse((x - 7, y - 5, x + 7, y + 7), fill=WHITE)
                s = 1 if i == 0 else -1          # +x is toward the nose for the left eye
                px = x + 2 * s
                d.ellipse((px - 3, y + 1, px + 2, y + 6), fill=INK)
                d.point((px - 1, y + 2), fill=SHINE)
                lid = {xx: y - 3 + round(1.5 * s * (xx - x) / 8) for xx in range(x - 8, x + 9)}
                for xx, ly in lid.items():
                    for yy in range(y - 7, ly):
                        im.putpixel((xx, yy), (0, 0, 0, 0))
                    # the 2px lid line only where the eye continues below it (no nubs at the corners)
                    if sum(1 for yy in range(ly, ly + 5) if im.getpixel((xx, yy))[3]) >= 5:
                        for yy in (ly, ly + 1):
                            im.putpixel((xx, yy), INK)
                    else:                       # corner columns: clear down to the lid, keep the outline below
                        for yy in (ly, ly + 1):
                            if im.getpixel((xx, yy))[:3] == WHITE[:3]:
                                im.putpixel((xx, yy), INK)
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


def _poly(d, pts, thick=2):
    """A polyline drawn column by column (thick px tall): clean joints, no horn ticks. Slopes <= 1."""
    pts = [(pts[k], pts[k + 1]) for k in range(0, len(pts), 2)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        for x in range(min(x0, x1), max(x0, x1) + 1):
            y = round(y0 + (y1 - y0) * (x - x0) / (x1 - x0)) if x1 != x0 else y0
            d.line((x, y, x, y + thick - 1), fill=INK)


def _teeth_box(d, x0, y0, x1, y1, gaps):
    """An ink-outlined box of teeth with ink gaps at the given x columns."""
    d.rectangle((x0, y0, x1, y1), fill=INK)
    d.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), fill=TEETH)
    for gx in gaps:
        d.line((gx, y0 + 1, gx, y1 - 1), fill=INK)


def mouth_buck():
    """Goofy smile with two big front teeth hanging over the lip."""
    im = Image.new('RGBA', (MW * 4, MH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for f in range(4):
        cx, cy = f * MW + 16, 5
        if f == 0:          # neutral: smile + the two teeth
            _poly(d, (cx - 7, cy - 1, cx - 4, cy + 2, cx + 4, cy + 2, cx + 7, cy - 1))
            _teeth_box(d, cx - 4, cy + 2, cx + 4, cy + 7, [cx])
        elif f == 1:        # open: an O with the teeth at the top
            d.ellipse((cx - 6, cy - 3, cx + 6, cy + 8), fill=INK)
            d.ellipse((cx - 4, cy - 1, cx + 4, cy + 6), fill=MOUTH)
            d.rectangle((cx - 2, cy + 4, cx + 2, cy + 6), fill=TONGUE)
            _teeth_box(d, cx - 4, cy - 2, cx + 4, cy + 3, [cx])
        elif f == 2:        # grimace: a nervous frown, the teeth biting the bottom lip
            _poly(d, (cx - 8, cy + 4, cx - 4, cy + 1, cx + 4, cy + 1, cx + 8, cy + 4))
            _teeth_box(d, cx - 4, cy + 1, cx + 4, cy + 6, [cx])
        elif f == 3:        # grin: wide D, the teeth front and centre
            d.chord((cx - 10, cy - 7, cx + 10, cy + 9), 0, 180, fill=INK)
            d.chord((cx - 8, cy - 5, cx + 8, cy + 7), 0, 180, fill=MOUTH)
            d.ellipse((cx - 3, cy + 4, cx + 4, cy + 8), fill=TONGUE)
            _teeth_box(d, cx - 4, cy, cx + 4, cy + 5, [cx])
    return im


def mouth_smirk():
    """Lopsided: one corner hooked up. Cocky."""
    im = Image.new('RGBA', (MW * 4, MH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for f in range(4):
        cx, cy = f * MW + 16, 6
        if f == 0:          # neutral: flat, hooking up on the right, a dimple dot
            _poly(d, (cx - 6, cy + 1, cx + 2, cy + 1, cx + 5, cy - 2))
            d.point((cx + 8, cy - 3), fill=INK)
        elif f == 1:        # open: a small off-centre O
            d.line((cx - 6, cy + 1, cx - 2, cy + 1), fill=INK, width=2)
            d.ellipse((cx - 2, cy - 3, cx + 6, cy + 5), fill=INK)
            d.ellipse((cx, cy - 1, cx + 4, cy + 3), fill=MOUTH)
        elif f == 2:        # grimace: teeth bared on one side only
            _poly(d, (cx - 7, cy + 1, cx - 3, cy + 1))
            _teeth_box(d, cx - 3, cy - 3, cx + 8, cy + 3, [cx + 1, cx + 5])
            d.line((cx - 2, cy, cx + 7, cy), fill=INK)
        elif f == 3:        # grin: a lopsided D
            d.chord((cx - 5, cy - 6, cx + 11, cy + 8), 0, 180, fill=INK)
            d.chord((cx - 3, cy - 4, cx + 9, cy + 6), 0, 180, fill=MOUTH)
            d.rectangle((cx - 2, cy + 1, cx + 8, cy + 2), fill=TEETH)
    return im


def mouth_cat():
    """The :3 / w mouth. Smug-cute."""
    W_PTS = lambda cx, cy: (cx - 6, cy - 1, cx - 4, cy + 1, cx - 2, cy + 1, cx, cy - 1, cx + 2, cy + 1, cx + 4, cy + 1, cx + 6, cy - 1)   # two round-bottomed U's
    im = Image.new('RGBA', (MW * 4, MH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for f in range(4):
        cx, cy = f * MW + 16, 4
        if f == 0:          # neutral: w
            _poly(d, W_PTS(cx, cy))
        elif f == 1:        # open: the w opens into a little mouth below
            d.ellipse((cx - 4, cy, cx + 4, cy + 8), fill=INK)
            d.ellipse((cx - 2, cy + 2, cx + 2, cy + 6), fill=MOUTH)
            d.point((cx, cy + 5), fill=TONGUE); d.point((cx + 1, cy + 5), fill=TONGUE)
            _poly(d, W_PTS(cx, cy))
        elif f == 2:        # grimace: a wobbly zigzag
            _poly(d, (cx - 8, cy + 3, cx - 5, cy + 1, cx - 2, cy + 3, cx + 1, cy + 1, cx + 4, cy + 3, cx + 7, cy + 1))
        elif f == 3:        # grin: a big open mouth hanging off the w
            d.chord((cx - 8, cy - 5, cx + 8, cy + 10), 0, 180, fill=INK)
            d.chord((cx - 6, cy - 3, cx + 6, cy + 8), 0, 180, fill=MOUTH)
            d.ellipse((cx - 3, cy + 4, cx + 3, cy + 8), fill=TONGUE)
            _poly(d, W_PTS(cx, cy + 1))
    return im


# ------------------------------------------------------------------ more eyes (2026-10-01)
def eyes_angry():
    """Permanently cross: slanted lids that drop toward the nose, pupils pinned low and inward."""
    im = Image.new('RGBA', (EW * 5, EH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    centres = [(13, 10), (35, 10)]
    for f in range(5):
        ox = f * EW
        for i, (cx, cy) in enumerate(centres):
            x, y = ox + cx, cy
            s = 1 if i == 0 else -1                      # +x is toward the nose for the left eye
            if f in (0, 3):
                d.ellipse((x - 8, y - 6, x + 8, y + 8), fill=INK)
                d.ellipse((x - 7, y - 5, x + 7, y + 7), fill=WHITE)
                px = x + 2 * s
                d.ellipse((px - 3, y + 1, px + 2, y + 6), fill=INK)
                slope = 4.0 if f == 0 else 5.5
                lift = -3 if f == 0 else -1
                for xx in range(x - 8, x + 9):
                    ly = y + lift + round(slope * s * (xx - x) / 8)
                    for yy in range(0, max(0, ly)):
                        im.putpixel((xx, yy), (0, 0, 0, 0))
                    for yy in (ly, ly + 1):
                        if 0 <= yy < EH and im.getpixel((xx, yy))[3]:
                            im.putpixel((xx, yy), INK)
            elif f == 1:
                d.line((x - 7, y + 1 - 2 * s, x + 7, y + 1 + 2 * s), fill=INK, width=2)   # a cross squint
            elif f == 2:
                _hurt(d, x, y, i)
            elif f == 4:
                d.line((x - 7, y + 3, x, y - 4, x + 7, y + 3), fill=INK, width=2)
    return im


def eyes_wide():
    """Huge round staring eyes with tiny pupils: permanently startled."""
    im = Image.new('RGBA', (EW * 5, EH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    centres = [(12, 10), (36, 10)]
    for f in range(5):
        ox = f * EW
        for i, (cx, cy) in enumerate(centres):
            x, y = ox + cx, cy
            if f in (0, 3):
                d.ellipse((x - 10, y - 9, x + 10, y + 9), fill=INK)
                d.ellipse((x - 9, y - 8, x + 9, y + 8), fill=WHITE)
                r = 2 if f == 0 else 3
                d.ellipse((x - r, y - r, x + r, y + r), fill=INK)
                if f == 3:                               # focus: the lid drops a bit
                    d.rectangle((x - 10, y - 10, x + 10, y - 4), fill=(0, 0, 0, 0))
                    d.line((x - 9, y - 4, x + 9, y - 4), fill=INK, width=2)
            elif f == 1:
                d.line((x - 9, y + 1, x - 4, y + 4, x + 4, y + 4, x + 9, y + 1), fill=INK, width=2)
            elif f == 2:
                _hurt(d, x, y, i, 8)
            elif f == 4:
                d.line((x - 9, y + 4, x, y - 5, x + 9, y + 4), fill=INK, width=2)
    return im


def eyes_button():
    """Shiny black button eyes, two highlights each: a plush-toy stare."""
    im = Image.new('RGBA', (EW * 5, EH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    centres = [(14, 10), (34, 10)]
    for f in range(5):
        ox = f * EW
        for i, (cx, cy) in enumerate(centres):
            x, y = ox + cx, cy
            if f in (0, 3):
                top = y - 6 if f == 0 else y - 2
                d.ellipse((x - 6, top, x + 6, y + 6), fill=INK)
                d.rectangle((x - 3, top + 2, x - 1, top + 3), fill=SHINE)
                d.point((x + 2, y + 3), fill=SHINE)
            elif f == 1:
                d.line((x - 6, y + 2, x - 2, y + 4, x + 2, y + 4, x + 6, y + 2), fill=INK, width=2)
            elif f == 2:
                _hurt(d, x, y, i, 6)
            elif f == 4:
                d.line((x - 6, y + 3, x, y - 3, x + 6, y + 3), fill=INK, width=3)
    return im


# ------------------------------------------------------------------ more mouths (2026-10-01)
def mouth_blep():
    """A little smile with the tongue poking out."""
    im = Image.new('RGBA', (MW * 4, MH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for f in range(4):
        cx, cy = f * MW + 16, 5
        def tongue(x, y, w=3, h=5):
            d.rounded_rectangle((x - w - 1, y - 1, x + w + 1, y + h + 1), radius=3, fill=INK)
            d.rounded_rectangle((x - w, y, x + w, y + h), radius=3, fill=TONGUE)
            d.line((x, y + 1, x, y + h - 2), fill=(170, 60, 70, 255))
        if f == 0:
            tongue(cx + 2, cy + 1)
            _poly(d, (cx - 7, cy - 1, cx - 4, cy + 1, cx + 4, cy + 1, cx + 7, cy - 1))
        elif f == 1:
            d.ellipse((cx - 5, cy - 3, cx + 5, cy + 7), fill=INK)
            d.ellipse((cx - 3, cy - 1, cx + 3, cy + 5), fill=MOUTH)
            tongue(cx, cy + 4, 3, 4)
        elif f == 2:
            _poly(d, (cx - 8, cy + 2, cx - 4, cy, cx + 4, cy, cx + 8, cy + 2))
            tongue(cx - 3, cy + 1, 3, 4)
        elif f == 3:
            d.chord((cx - 9, cy - 6, cx + 9, cy + 8), 0, 180, fill=INK)
            d.chord((cx - 7, cy - 4, cx + 7, cy + 6), 0, 180, fill=MOUTH)
            tongue(cx + 1, cy + 3, 4, 5)
    return im


def mouth_fangs():
    """A grin with two little vampire fangs."""
    im = Image.new('RGBA', (MW * 4, MH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    def fangs(y, l=4):
        for fx in (-4, 4):
            d.polygon([(cx + fx - 2, y), (cx + fx + 2, y), (cx + fx, y + l)], fill=TEETH, outline=INK)
    for f in range(4):
        cx, cy = f * MW + 16, 5
        if f == 0:
            _poly(d, (cx - 8, cy - 1, cx - 5, cy + 1, cx + 5, cy + 1, cx + 8, cy - 1))
            fangs(cy + 2)
        elif f == 1:
            d.ellipse((cx - 6, cy - 3, cx + 6, cy + 8), fill=INK)
            d.ellipse((cx - 4, cy - 1, cx + 4, cy + 6), fill=MOUTH)
            fangs(cy - 1, 4)
        elif f == 2:
            _teeth_box(d, cx - 9, cy - 2, cx + 9, cy + 4, [cx - 5, cx, cx + 5])
            fangs(cy + 4, 4)
        elif f == 3:
            d.chord((cx - 10, cy - 7, cx + 10, cy + 9), 0, 180, fill=INK)
            d.chord((cx - 8, cy - 5, cx + 8, cy + 7), 0, 180, fill=MOUTH)
            fangs(cy + 1, 5)
    return im


def mouth_ooh():
    """A small round 'ooh' - permanently impressed."""
    im = Image.new('RGBA', (MW * 4, MH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for f in range(4):
        cx, cy = f * MW + 16, 6
        if f == 0:
            d.ellipse((cx - 3, cy - 3, cx + 3, cy + 4), fill=INK)
            d.ellipse((cx - 1, cy - 1, cx + 1, cy + 2), fill=MOUTH)
        elif f == 1:
            d.ellipse((cx - 5, cy - 5, cx + 5, cy + 6), fill=INK)
            d.ellipse((cx - 3, cy - 3, cx + 3, cy + 4), fill=MOUTH)
        elif f == 2:
            _poly(d, (cx - 5, cy + 1, cx - 3, cy - 1, cx - 1, cy + 1, cx + 1, cy - 1, cx + 3, cy + 1, cx + 5, cy - 1))
        elif f == 3:
            d.ellipse((cx - 7, cy - 6, cx + 7, cy + 7), fill=INK)
            d.ellipse((cx - 5, cy - 4, cx + 5, cy + 5), fill=MOUTH)
            d.ellipse((cx - 3, cy + 1, cx + 3, cy + 5), fill=TONGUE)
    return im


# ------------------------------------------------------------------ facial hair (one frame, 64x32, drawn at canvas y 30)
FHW, FHH = 64, 32
HAIR = (66, 42, 26, 255)
HAIR_HI = (104, 70, 44, 255)


def _blob(d, pts):
    d.polygon(pts, fill=HAIR, outline=INK)


def fh_handlebar():
    im = Image.new('RGBA', (FHW, FHH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for s in (1, -1):                                    # two lobes curling up at the tips
        pts = [(32, 6), (32 + 4 * s, 4), (32 + 10 * s, 5), (32 + 15 * s, 6), (32 + 19 * s, 3), (32 + 20 * s, 0),
               (32 + 22 * s, 2), (32 + 21 * s, 6), (32 + 16 * s, 10), (32 + 9 * s, 10), (32 + 3 * s, 9), (32, 8)]
        _blob(d, pts)
        d.line((32 + 5 * s, 7, 32 + 12 * s, 7), fill=HAIR_HI)
    return im


def fh_goatee():
    """The owner's combo: a long thin mustache right across the lip (as wide as the full beard's) and a small,
    sparse chin patch under the lip - not a solid beard."""
    im = Image.new('RGBA', (FHW, FHH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # mustache: thin, wide, drooping a touch at the ends
    d.polygon([(19, 8), (24, 5), (32, 6), (40, 5), (45, 8), (44, 9), (40, 8), (32, 8), (24, 8), (20, 9)], fill=HAIR)
    d.line((20, 9, 24, 7, 31, 7), fill=INK)
    d.line((33, 7, 40, 7, 44, 9), fill=INK)
    # chin patch: a soft little triangle of hair dots under the lip, denser in the middle
    rng = random.Random(8)
    for _ in range(260):
        x, y = rng.randrange(25, 40), rng.randrange(17, 31)
        w = 1 - abs(x - 32) / 8.5 - (y - 17) / 20
        if w > rng.random() * 0.55:
            im.putpixel((x, y), HAIR if rng.random() < 0.7 else INK)
    return im


def fh_beard():
    im = Image.new('RGBA', (FHW, FHH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(4, 0), (12, 0), (14, 10), (20, 19), (44, 19), (50, 10), (52, 0), (60, 0), (58, 14), (50, 26),
               (40, 31), (24, 31), (14, 26), (6, 14)], fill=HAIR, outline=INK)
    for k in range(9):                                   # curls
        d.point((10 + k * 5, 18 + (k % 3) * 3), fill=HAIR_HI)
    _blob(d, [(22, 5), (32, 3), (42, 5), (44, 9), (36, 9), (32, 7), (28, 9), (20, 9)])   # mustache
    return im


def fh_stubble():
    im = Image.new('RGBA', (FHW, FHH), (0, 0, 0, 0))
    rng = random.Random(3)
    dot = (40, 30, 24, 170)
    for _ in range(140):
        x, y = rng.randrange(6, 58), rng.randrange(2, 31)
        inside = ((x - 32) / 26) ** 2 + ((y - 4) / 27) ** 2 < 1.0 and (y > 18 or abs(x - 32) > 12 or y < 6)
        if inside and (x + y) % 2 == 0:
            im.putpixel((x, y), dot)
    return im


# ------------------------------------------------------------------ cheek features (one frame, 64x64 overlay under the eyes)
def feat_blush():
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for cx in (13, 51):
        d.ellipse((cx - 7, 30, cx + 7, 37), fill=(255, 84, 120, 175))
        d.line((cx - 3, 32, cx - 1, 35), fill=(255, 190, 200, 200))
        d.line((cx + 1, 32, cx + 3, 35), fill=(255, 190, 200, 200))
    return im


def feat_freckles():
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    col = (110, 70, 34, 210)
    for cx in (15, 49):
        for dx, dy in ((-4, 0), (0, -2), (3, 1), (-1, 3), (4, 4), (-5, 4), (1, 6)):
            im.putpixel((cx + dx, 32 + dy), col)
            im.putpixel((cx + dx + 1, 32 + dy), col)
    return im


def feat_cheekbones():
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    shade = (20, 40, 10, 90)
    d.line((5, 27, 9, 33, 15, 38), fill=shade, width=2)
    d.line((59, 27, 55, 33, 49, 38), fill=shade, width=2)
    return im


def feat_bags():
    im = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bag = (60, 40, 70, 120)
    for cx in (21, 43):
        d.arc((cx - 8, 22, cx + 8, 34), 20, 160, fill=bag, width=2)
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
    mouth_buck().save(os.path.join(OUT, 'mouth_buck.png'))
    mouth_smirk().save(os.path.join(OUT, 'mouth_smirk.png'))
    mouth_cat().save(os.path.join(OUT, 'mouth_cat.png'))
    for name, fn in (('eyes_angry', eyes_angry), ('eyes_wide', eyes_wide), ('eyes_button', eyes_button),
                     ('mouth_blep', mouth_blep), ('mouth_fangs', mouth_fangs), ('mouth_ooh', mouth_ooh),
                     ('fhair_handlebar', fh_handlebar), ('fhair_goatee', fh_goatee), ('fhair_beard', fh_beard),
                     ('fhair_stubble', fh_stubble),
                     ('feat_blush', feat_blush), ('feat_freckles', feat_freckles), ('feat_cheekbones', feat_cheekbones),
                     ('feat_bags', feat_bags)):
        fn().save(os.path.join(OUT, name + '.png'))
    print('faces written to', OUT)
