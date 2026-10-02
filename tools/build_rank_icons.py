"""Rank emblems: hand-placed 16x16 pixel art, one strip (spec: docs/superpowers/specs/2026-10-02-ranked-design.md).

Writes textures/rank/emblems.png (16*7 x 16, RGBA) in the order UNRANKED, BRONZE, SILVER, GOLD, PLATINUM, DIAMOND,
MASTER (index.html RANK.TIERS uses the same order). Run: python tools/build_rank_icons.py
"""
import os
from PIL import Image

OUTLINE = '#1a1420'
WHITE = '#f8f4ec'
GOLD = ('#ffe39a', '#f0c050', '#a8742a')
TIERS = {   # light, mid, dark
    'UNRANKED': ('#9aa0b3', '#5c6378', '#3a4050'),
    'BRONZE':   ('#e8a878', '#b8743e', '#7a4a22'),
    'SILVER':   ('#f0f2f8', '#b8bfcc', '#7c8396'),
    'GOLD':     GOLD,
    'PLATINUM': ('#c8fff0', '#6fd8c8', '#2f8a8a'),
    'DIAMOND':  ('#d8f0ff', '#6ab8f0', '#2f62c8'),
    'MASTER':   ('#ecd8ff', '#b07ae8', '#6a3ab8'),
}

SHIELD = [
    "..kkkkkkkkkkkk..",
    "..kLLLLLLLLLLk..",
    "..kLMMMMMMMMDk..",
    "..kLMMMMMMMMDk..",
    "..kLMMMMMMMMDk..",
    "..kLMMMMMMMMDk..",
    "..kLMMMMMMMMDk..",
    "..kLMMMMMMMMDk..",
    "...kLMMMMMMDk...",
    "...kLMMMMMMDk...",
    "....kLMMMMDk....",
    ".....kLMMDk.....",
    "......kMDk......",
    ".......kk.......",
]
GEM = [
    "....kkkkkkkk....",
    "...kLLwLLLLMk...",
    "..kLLwLLLLMMDk..",
    ".kkkkkkkkkkkkkk.",
    ".kLLMMMMMMMMDDk.",
    "..kLMMMMMMMMDk..",
    "...kLMMMMMMDk...",
    "....kLMMMMDk....",
    ".....kLMMDk.....",
    "......kMDk......",
    ".......kk.......",
]
CROWN = [
    "..g....gg....g..",
    "..gg..gggg..gg..",
    "..gGgggGGgggGg..",
    "..gggggggggggg..",
]
# symbols stamped on the shield face (8 wide, at column 4)
SYM = {
    'UNRANKED': ["..wwww..", ".w....w.", ".....w..", "....w...", "........", "....w..."],
    'BRONZE':   ["........", "...DD...", "..D..D..", ".D....D.", "........"],
    'SILVER':   ["...DD...", "..D..D..", ".D.DD.D.", "..D..D..", ".D....D."],
    'GOLD':     ["...ww...", "...ww...", "wwwwwwww", ".wwwwww.", "..wwww..", ".ww..ww.", ".w....w."],
    'PLATINUM': ["...ww...", "...ww...", "wwwwwwww", ".wwwwww.", "..wwww..", ".ww..ww.", ".w....w."],
}
WING = [(1, 2), (0, 3), (1, 3), (0, 4), (1, 4), (1, 5), (0, 6), (1, 6), (1, 7)]


def compose(tier):
    g = [['.'] * 16 for _ in range(16)]

    def stamp(rows, top, left=0):
        for y, r in enumerate(rows):
            for x, c in enumerate(r):
                if c != '.':
                    g[top + y][left + x] = c

    if tier == 'DIAMOND':
        stamp(GEM, 2)
    elif tier == 'MASTER':
        stamp(CROWN, 1)
        stamp(GEM, 5)
    else:
        stamp(SHIELD, 1)
        stamp(SYM[tier], 3 if tier != 'UNRANKED' else 2, 4)
        if tier == 'PLATINUM':
            for x, y in WING:
                g[y + 1][x] = 'L' if (x + y) % 2 else 'M'
                g[y + 1][15 - x] = 'L' if (x + y) % 2 else 'M'
    return g


def hexrgba(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def main():
    order = list(TIERS)
    out = Image.new('RGBA', (16 * len(order), 16), (0, 0, 0, 0))
    for i, tier in enumerate(order):
        L, M, D = TIERS[tier]
        pal = {'k': OUTLINE, 'w': WHITE, 'L': L, 'M': M, 'D': D, 'g': GOLD[1], 'G': GOLD[0]}
        for y, row in enumerate(compose(tier)):
            for x, c in enumerate(row):
                if c != '.':
                    out.putpixel((i * 16 + x, y), hexrgba(pal[c]))
    os.makedirs('textures/rank', exist_ok=True)
    out.save('textures/rank/emblems.png')
    print('textures/rank/emblems.png:', ', '.join(f'{t}: {i}' for i, t in enumerate(order)))


if __name__ == '__main__':
    main()
