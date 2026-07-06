# Volleybolt — Brand & Art Direction Pack

Reference pack for artists creating key art / flavor art (itch.io page, splash
illustrations). Everything in this folder is captured from the real game —
this is ground truth, not concept work.

## The game in one line

Two tiny pickle wizards duel across a castle court, volleying elemental spells
back and forth — a fantasy sport where every exchange is pure skill: **no
randomness, ever**.

## Style pillars

1. **PS1-era fantasy.** Low-poly models, low-res render, 15-bit color with
   Bayer dithering, affine-texture charm. Final Fantasy IX menus are the UI
   north star: steel blue-grey panels, light rims, hard offset shadows, gold
   headings.
2. **NES palette discipline.** Team Blue `#0078F8` vs Team Red `#F83800`,
   amber `#FC9838`, cream `#F8F8F8`. Saturated, iconic, few colors.
3. **Cute body, epic magic.** The pickle wizard is small, round, and
   charming; the spells are outsized and dramatic. Key art lives in that
   contrast.
4. **Deterministic duel.** The fiction and the feel are honor-duel, not
   chaos: readable arcs, clean geometry, nothing splattery or random.

## Character — the Pickle Wizard

- 2D concept: `character/pickle-2d-concept.png` (canonical face + proportions;
  the face sprite `character/pickle-face-sprite.png` is applied as a flat,
  always-front FF9-style decal in game)
- 3D turnaround: `character/turn-{front,threequarter,side,back}.png`
- Motion personality: `character/anim-{idle,cast,victory,defeat}.gif`
- In game the two duelists are the SAME pickle tinted per team — blue-side
  player LEFT, red-side opponent RIGHT. **Never reverse the sides.**
- Design nod: the pickle is a wink at Pickleball's character design — keep it
  a wink, not a joke; the character carries real hero energy in key art.

## Palette (authoritative hexes)

| Role | Hex |
|---|---|
| Gold accent (headings, trim) | `#f0c050` |
| Team blue / Team red | `#0078F8` / `#F83800` |
| Fire / Frost / Lightning | `#ffa040` / `#80d0ff` / `#ffff40` |
| Steel panel bg | `rgba(46,56,76,0.94)` |
| Panel rim | `#dfe6f2` |
| Backdrop dark | `#15121b` |
| NES amber / cream | `#FC9838` / `#F8F8F8` |

Full UI system: `docs/design-system/STYLE-GUIDE.md`.

## The world — DRAFT lore (revisable; not yet canon)

Long ago, the wizards of two rival towers settled their disputes the civilized
way: by hurling spells at each other across a garden court until somebody's
gate gave in. The tradition stuck. Now every dispute — territorial, academic,
or purely personal — is settled by **the volley**: magic answered with magic,
bolt for bolt, until one side can no longer return.

The duelists are pickle-folk: small, brined, and utterly fearless
spellcasters who train their whole lives for court day. Their code is strict —
no luck, no tricks, no dice. A volley is won by reading your opponent, not by
fortune. Fire scorches, frost slows, lightning splits the sky, and a
well-timed parry turns your enemy's best shot back at them.

The court sits between the two towers — blue in the west, red in the east — a
worn dirt road flanked by hedges, lit by a dusk that never quite ends.

## Spells

| Spell | Color | Reference | Reads as |
|---|---|---|---|
| Fireball | `#ffa040` | `spells/fireball.gif` | fast streaking comet + trail |
| Frostbolt | `#80d0ff` | `spells/frostbolt.gif` | cold shard, crystalline trail |
| Thunder | `#ffff40` | `spells/thunder.gif` | jagged sky-strike, instant |
| Parry | team color | `spells/parry.gif` | crescent ward + deflection |
| Juice (ultimate) | gold #f0c050 | _coming soon_ | big beam — reference art pending |

> **Juice (beam ultimate) is being reworked — a fifth spell reference (beam GIF) will be added when it lands. Leave room for it in key-art compositions.**

Source in-game textures: `spells/tex-*.png`.

## Key-art brief

**The ask:** splash-style illustration (League of Legends key-art energy) that
looks like THIS game — PS1 fantasy, NES color discipline, cute-vs-epic.

DO
- Low camera angle, pickle wizard mid-cast, spell lighting the scene
- Team colors carrying the composition; gold `#f0c050` for trim/title
- The two-tower standoff as backdrop; dusk purple sky `#15121b`
- Chunky, readable silhouettes (the game reads at 64px — key art should too)

DON'T
- Don't reverse team sides (blue left / red right)
- Don't render the pickle hyper-real or gross — it's a hero, not a gag
- Don't add dice, sparkle-chaos, or randomness motifs — this is a duel of skill
- Don't introduce new spell colors — fire/frost/lightning only

## Folder map

```
character/  2D concept, face sprite, 3D turnaround, animation GIFs
spells/     4 spell GIFs (black plates) + source textures
world/      arena wides (no HUD), tower crops, court biome
ui/         main menu, palette reference
```
