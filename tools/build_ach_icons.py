"""Achievement badge icons: hand-placed 16x16 pixel art (pixel-first, small palette), one sprite strip.

Writes textures/ach/icons.png (16*N x 16, RGBA). Order = ORDER below; index.html's ACH_ICON maps
an achievement id to its column. Run: python tools/build_ach_icons.py
"""
import os
from PIL import Image

PAL = {
    'k': '#1a1420', 'w': '#f4f0e8',
    'g': '#f0c050', 'G': '#ffe39a', 'd': '#a8742a',
    'p': '#5f9e34', 'P': '#9fd060', 'q': '#3f6e22',
    'b': '#a8d8ec', 'B': '#6aa6c8',
    'r': '#e2463c', 'R': '#a8281f', 'o': '#f08a30', 'y': '#ffd84a',
    's': '#c4c8d4', 'S': '#7c8396',
    'i': '#cfeeff', 'I': '#6ab8e8',
    'u': '#c9a8ff', 'U': '#7a5ab8',
    'n': '#8a5a32', 't': '#5d93f0', 'T': '#2f62c8',
}


def grid(rows):
    rows = [r.ljust(16, '.')[:16] for r in rows]
    top = (16 - len(rows)) // 2
    g = [['.'] * 16 for _ in range(16)]
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            g[top + y][x] = c
    return g


def put(g, pts, c):
    for x, y in pts:
        g[y][x] = c
    return g


def jar(n):
    g = grid([
        "................",
        ".....kkkkkk.....",
        "....kssssssk....",
        "....kSSSSSSk....",
        ".....kkkkkk.....",
        "....kbbbbbbk....",
        "...kbwbbbbbbk...",
        "...kbwbbbbbbk...",
        "...kbbbbbbbbk...",
        "...kbbbbbbbbk...",
        "...kbbbbbbbbk...",
        "...kbbbbbbbbk...",
        "...kbbbbbbbbk...",
        "...kBbbbbbbBk...",
        "....kBBBBBBk....",
        ".....kkkkkk.....",
    ])
    cols = {1: [7], 2: [5, 9], 3: [4, 7, 10], 4: [4, 6, 8, 10]}[n]
    for i, x in enumerate(cols):
        top = 8 if (i % 2 == 0 or n < 4) else 9
        for y in range(top, 14):
            g[y][x] = 'P' if y == top else 'p'
            if n < 4:
                g[y][x + 1] = 'q' if y > top else 'p'
    return g


ICONS = {
    'FIRST_BRINE': jar(1), 'SEASONED': jar(2), 'PICKLED': jar(3), 'FERMENTED': jar(4),
    'WALL_OF_DILL': grid([
        "..kkkkkkkkkkkk..",
        "..kssssssssssk..",
        "..ksSSSSSSSSsk..",
        "..ksSSSppSSSsk..",
        "..ksSSpPPpSSsk..",
        "..ksSSpPPpSSsk..",
        "..ksSSpPPpSSsk..",
        "..ksSSSppSSSsk..",
        "...ksSSSSSSsk...",
        "...ksSSSSSSsk...",
        "....ksSSSSsk....",
        ".....ksSSsk.....",
        "......kssk......",
        ".......kk.......",
    ]),
    'PYROMANCER': grid([
        "...........oy...",
        ".........ooy....",
        ".......ooyyo....",
        ".....rooyyo.....",
        "....rrkkkko.....",
        "...rkoyyyyok....",
        "..rkoyywwyyok...",
        "..rkoywwwwyok...",
        "..rkoywwwwyok...",
        "..rkoyywwyyok...",
        "...rkoyyyyok....",
        "....kkoooook....",
        "......kkkk......",
    ]),
    'PICKLE_MONK': grid([
        ".....kkkkkk.....",
        "....kuuuuuuk....",
        "...kuwuuuuuuk...",
        "...kuwuuuuuuk...",
        "...kuuuuuuuuk...",
        "...kuuuuuuuuk...",
        "...kuuuuuuuuk...",
        "...kUuuuuuuUk...",
        "....kUUUUUUk....",
        ".....kkkkkk.....",
        "......knnk......",
        "......knnk......",
        "......knnk......",
        "......kkkk......",
    ]),
    'CLEAN_SWEEP': grid([
        ".............kk.",
        "............knk.",
        "...........knk..",
        "..........knk...",
        ".........knk....",
        "........knk.....",
        ".......kgk......",
        ".....kkggk......",
        "....kyyyykk.....",
        "...kyyyyydk.....",
        "..kyyyydyk......",
        ".kyydyyyk.......",
        ".kydyydk........",
        ".kkkkkk.........",
    ]),
    'COMEBACK_KID': grid([
        ".......kk.......",
        "......kPPk......",
        ".....kPPPPk.....",
        "....kPPPPPPk....",
        "...kPPPPPPPPk...",
        "..kPPPPPPPPPPk..",
        "..kkkkPPppkkkk..",
        ".....kPPppk.....",
        ".....kPPppk.....",
        ".....kPPppk.....",
        ".....kPPppk.....",
        ".....kPPppk.....",
        ".....kkkkkk.....",
    ]),
    'SPEED_BRINE': grid([
        "......kkkk......",
        ".......kk.......",
        ".....kkkkkk.....",
        "....kwwwwwwk....",
        "...kwwwwrwwwk...",
        "..kwwwwwrwwwwk..",
        "..kwwwwwrwwwwk..",
        "..kwwwwwrrrrwk..",
        "..kwwwwwwwwwwk..",
        "..kwwwwwwwwwwk..",
        "...kwwwwwwwwk...",
        "....kwwwwwwk....",
        ".....kkkkkk.....",
    ]),
    'MARATHON': grid([
        "...kkkkkkkkkk...",
        "...knnnnnnnnk...",
        "....kbbbbbbk....",
        "....kyyyyyyk....",
        ".....kyyyyk.....",
        "......kyyk......",
        ".......kk.......",
        "......kbyk......",
        ".....kbbybk.....",
        "....kbbbybbk....",
        "....kbyyyyyk....",
        "....kyyyyyyk....",
        "...knnnnnnnnk...",
        "...kkkkkkkkkk...",
    ]),
    'UNTOUCHED': grid([
        "...kkk.kk.kkk...",
        "...ksk.kk.ksk...",
        "...kskkkkkksk...",
        "...ksssssssSk...",
        "...ksSsssSssk...",
        "...ksssssssSk...",
        "...kssskkssSk...",
        "...ksskwbksSk...",
        "...ksskbbksSk...",
        "...ksssssssSk...",
        "...ksSsssSssk...",
        "...ksssssssSk...",
        "...kkkkkkkkkk...",
    ]),
    'RETURN_TO_SENDER': grid([
        "....kk..........",
        "...koo..........",
        "..kooooooo......",
        "...koo....o.....",
        "....kk....o.....",
        "..kkkkkkkkkkkk..",
        "..kkiiiiiiiikk..",
        "..kikiiiiiikik..",
        "..kiikiiiikiik..",
        "..kiiikiikiiik..",
        "..kiiiikkiiiik..",
        "..kiiiiiiiiiik..",
        "..kIIIIIIIIIIk..",
        "..kkkkkkkkkkkk..",
    ]),
    'COLD_WAR': grid([
        ".kk..........kk.",
        ".kik........kik.",
        "..kiIk....kIik..",
        "...kiIk..kIik...",
        "....kiIkkIik....",
        ".....kiIIik.....",
        "......kiik......",
        ".....kiIIik.....",
        "....kiIkkIik....",
        "...kkIk..kIkk...",
        "..knkk....kknk..",
        ".knk........knk.",
        ".kk..........kk.",
    ]),
    'STORM_CHASER': grid([
        ".........kkkkk..",
        "........kyyyk...",
        ".......kyyyk....",
        "......kyyyk.....",
        ".....kyyyk......",
        "....kyyyykkkk...",
        "...kyyyyyyyyk...",
        "...kkkkkyyyk....",
        ".......kyyk.....",
        "......kyyk......",
        ".....kyyk.......",
        "....kyyk........",
        "...kyk..........",
        "...kk...........",
    ]),
    'MAX_RALLY': grid([
        ".......yy.......",
        "......yyyy......",
        ".....yy..yy.....",
        "....yy....yy....",
        ".......oo.......",
        "......oooo......",
        ".....oo..oo.....",
        "....oo....oo....",
        ".......rr.......",
        "......rrrr......",
        ".....rr..rr.....",
        "....rr....rr....",
    ]),
    'JUICE_CLASH_CHAMPION': grid([
        "......y..y......",
        ".......yy.......",
        "TTTTTyywwyyRRRRR",
        "tttttywwwwyrrrrr",
        "tttttywwwwyrrrrr",
        "TTTTTyywwyyRRRRR",
        ".......yy.......",
        "......y..y......",
    ]),
    'PICKLED_IN_ICE': put(grid([
        "..kkkkkkkkkkkk..",
        "..kiiiiiiiiiik..",
        "..kiwiiiiiiiik..",
        "..kiwiiiiiiiik..",
        "..kiiiiiiiiiik..",
        "..kiiiiiiiiiik..",
        "..kiiiiiiiiiik..",
        "..kiiiiiiiiiik..",
        "..kiiiiiiiiiik..",
        "..kiiiiiiiiiik..",
        "..kiiiiiiiiiIk..",
        "..kIIIIIIIIIIk..",
        "..kkkkkkkkkkkk..",
    ]), [(7, y) for y in range(5, 12)] + [(8, y) for y in range(5, 12)], 'p'),
    'OVERTIME_HERO': grid([
        "....rr....rr....",
        ".....rr..rr.....",
        "......rrrr......",
        ".......rr.......",
        "......kkkk......",
        ".....kggggk.....",
        "....kggGGggk....",
        "...kggGGGGggk...",
        "...kgGGgdGGgk...",
        "...kgGGGGGGgk...",
        "...kggGGGGggk...",
        "....kggGGggk....",
        ".....kggggk.....",
        "......kkkk......",
    ]),
    'DEMOLITION': grid([
        "..kkkkkkkkkkk...",
        "..ksssssssssk...",
        "..kswsssssssk...",
        "..kSSSSSSSSSk...",
        "..kkkkknnkkkk...",
        "......knnk......",
        "......knnk......",
        "......knnk......",
        "......knnk......",
        "......knnk......",
        "......knnk......",
        "......kkkk......",
        "..d..........d..",
        ".d.d..d..d..d.d.",
    ]),
}
# pickle highlight in the ice cube
put(ICONS['PICKLED_IN_ICE'], [(7, 5), (7, 6)], 'P')
put(ICONS['PICKLED_IN_ICE'], [(8, y) for y in range(7, 12)], 'q')

ORDER = list(ICONS)


def hexrgba(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def main():
    out = Image.new('RGBA', (16 * len(ORDER), 16), (0, 0, 0, 0))
    for i, key in enumerate(ORDER):
        g = ICONS[key]
        for y in range(16):
            for x in range(16):
                c = g[y][x]
                if c != '.':
                    out.putpixel((i * 16 + x, y), hexrgba(PAL[c]))
    os.makedirs('textures/ach', exist_ok=True)
    out.save('textures/ach/icons.png')
    print('textures/ach/icons.png', len(ORDER), 'icons:', ', '.join(f"{k}: {i}" for i, k in enumerate(ORDER)))


if __name__ == '__main__':
    main()
