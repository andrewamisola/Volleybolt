# Wizard customization — design

Date: 2026-09-26 · Status: PARKED (nice-to-have; revisit after the UI / main-menu pass) · Owner decisions so far: no monetization (~$2 game),
everything is earned by playing, keep the pickle wizard as the identity/marketing hook.

## Goal

Let players make the pickle wizard *theirs*: pick a hat, a wand, eyes and a pickle variety, and earn
new pieces by playing. Cosmetic only, never a gameplay advantage.

**Not in scope:** a store, currency, accounts, servers, spell/VFX recolours, gameplay-affecting items.

## The size problem (and the answer)

In a match the wizard is small: ~**38 px** tall in singles, ~**29 px** in doubles (1113×626, 24/32
world units of ortho height; model is 1.70 units). Fine detail is invisible there. So:

1. **In-match, cosmetics must read as silhouette + colour.** Hats and wands are chunky, exaggerated
   PS1 shapes (a tall crooked cone, a wide brim, a mushroom cap, a staff with a big glowing head);
   eyes read as a colour/shape blob, not detail. Every item is judged at 38 px before it ships.
2. **Show them off where the wizard is big.** The main menu is already a ~175 px hero close-up of
   the player's wizard dancing (`MENU_CAMERA`/`MENU_ORTHO`). The wardrobe reuses that exact shot, so
   customizing = dressing the wizard you see on the menu. Later phases add two more close-ups:
   a **winner close-up** on the victory screen (camera eases to the winning wizard behind the
   dimmed overlay) and an optional short **round-intro** push-in. Both are presentation-only camera
   moves, skipped under Reduce Motion.

## Slots and launch set

| Slot | Attaches to | Launch count | Notes |
|---|---|---|---|
| Hat | `Head` / `head_end` bone | 6 | the biggest silhouette read |
| Wand | `RightHand` bone | 5 | visible on every cast |
| Eyes | face texture on `headfront` | 5 | texture swap, cheap |
| Pickle | base body | 4 | dill (default), gherkin, cornichon, spicy (red-speckled), maybe a warty heirloom |

~3 of each unlocked from the start (so everyone personalizes on day one), the rest earned.

## Hard rules

1. **Team colour always wins.** Today the red side is told apart by tinting the whole pickle. With
   pickle varieties that can't stay a whole-body tint: team colour moves to a fixed **robe/sash**
   region (team mask on the body texture), plus a team-coloured hat band on every hat. Blue vs red
   must read at 29 px in doubles, for colourblind presets too (`TEAM_RIGHT`).
2. **No silhouette inflation.** Accessories stay inside a fixed bounding envelope around the model
   (checked by the Blender build script). A wizard never looks bigger than its hitbox.
3. **Spell colours are off-limits.** Fireball orange / frost blue / lightning gold are gameplay info.
4. **Cosmetics never enter the sim.** No sim state, no snapshots, no desync hash, nothing under
   rollback. Determinism goldens must be unchanged.

## Architecture

### Base model rebuild (the big piece)

`models/pickle/pickle_wizard_v1.glb` is one fused Meshy mesh (`char1`, 4.5k verts) with one 2048²
texture: hat, robe and face are baked together, so nothing can be swapped. Rebuild it in the scripted
Blender pipeline (like the castle) as `models/pickle/pickle_base.glb`:

- Same 24-joint rig and **same bone names**, so every existing clip in `models/pickle/clips/` keeps
  retargeting through the `nodeByName` map (index.html ~10966) unchanged.
- Hatless head, no wand; separate UV regions for face, pickle skin and robe; a team mask for the robe.
- Two routes, decided in the plan: (a) import the Meshy mesh, cut the hat away, cap the head, repaint
  the texture; (b) model a new pickle body skinned to the imported armature. (b) is cleaner and on
  style with the castle; (a) is faster. Prototype (a) first; fall back to (b).

### Accessories

- `tools/blender/build_cosmetics.py` → `models/cosmetics/cosmetics.glb`, one node per item
  (`hat_wizard`, `wand_oak`, …), low-poly, vertex/texel style matching the castle, sized in the
  pickle's bone space.
- At load, each wizard clones its equipped hat/wand and parents it to the bone's TransformNode from
  the existing `nodeByName` map (nothing is bone-attached today; that map is the hook).
- Eyes: swap the face texture region (or a small decal quad on `headfront`).
- Pickle variety: albedo/texture variant of the base body; the robe team mask is applied on top.

### Data + persistence

- `COSMETICS` registry: `{ id, slot, name, node|texture, unlock: {stat, careerValue} | 'starter' | 'secret' }`.
- New key `volleybolt_cosmetics` (house pattern `volleybolt_<snake>`, IIFE + try/catch like `Settings`):
  `{ equipped: {hat, wand, eyes, pickle}, unlocked: [ids] }`.

### Unlocks

- `StatTracker.registerThreshold(id, {stat, careerValue, onReached, once})` already exists (index.html
  ~1463) with **zero callers**; it's the hook. Register one threshold per locked item at boot; on
  reach → add to `unlocked`, save, queue a toast. Threshold state is in-memory only, so on boot also
  re-check all rules against saved career totals (the unlocked list is the persistent truth).
- Show "New item unlocked!" on the victory screen after `StatTracker.commitMatch()` (~24313/24354).

### Multiplayer sync (presentation only)

- **1v1:** today nothing (not even names) is exchanged. Add a `HELLO {name, cosmetics}` sent by both
  peers on connection open (alongside `PLAYER_READY`); store the opponent's loadout for model load.
  Fixes the opponent-name fallback ('Red') for free.
- **Doubles:** add `cosmetics` to `JOIN_HELLO_D` and to the slot object `{kind, peerId, name, ready}`
  broadcast in `LOBBY_STATE_D`; `START_MATCH_D` already carries slots.
- Unknown ids → default item (version skew between builds must never break a match).
- AI opponents: themed preset looks (e.g. "the Red Gherkin"), drawn from the full set.

### Wardrobe UI

- New `#wardrobeScreen` DOM overlay (`arcane-overlay crt-screen`, opened via `showMenuScreen`),
  reached from a main-menu button. Left: slot tabs + item grid (locked items show the unlock rule,
  e.g. "Land 100 perfect parries"); right: the live menu hero shot of your wizard, updated instantly.
- Career screen gains an "Unlocks" count.

## Draft unlock list (all from existing StatTracker keys)

| Item | Rule |
|---|---|
| Starter hat / wand / eyes ×3 each, dill pickle | starter |
| Frost-tipped wand | `frostbolt_casts` ≥ 100 career |
| Ember hat | `fireball_casts` ≥ 250 |
| Storm-rod wand | `projectiles_zapped` ≥ 50 |
| Duelist eyes | `parries_successful` ≥ 150 |
| Crown of perfection | `parries_perfect` ≥ 25 |
| Gherkin pickle | `matches_won` ≥ 5 |
| Cornichon pickle | `perfect_rounds` ≥ 3 |
| Spicy pickle | `damage_dealt` ≥ 2000 |
| Iceblock hat | `freeze_time_inflicted` ≥ 120 s |
| Combo shades (eyes) | `max_combo` ≥ 8 |
| Secret: soggy hat | `matches_lost` ≥ 10 ("it's not about winning") |

Numbers are placeholders to tune so a casual player unlocks most things in a few hours.

## Phases

1. **Base rebuild:** hatless pickle on the same rig; in-game it must look the same as today with the
   default hat + wand attached (regression gate).
2. **First hat + wand + wardrobe screen**, local save, menu hero preview.
3. **MP sync** (1v1 `HELLO`, doubles slots) + AI preset looks.
4. **Unlocks** (thresholds, boot re-check, toasts, career count).
5. **Content:** fill out the launch set; readability pass at 38/29 px.
6. **Polish:** victory winner close-up, optional round-intro push-in.

## Testing

- Determinism goldens unchanged after every phase (singles a90063b5 / 5e5eca1b / e6fdfae9; doubles
  baseline c736299e / 85eecc3f / 0e029492).
- Readability check: screenshot each item on both teams at singles + doubles scale, incl. colourblind presets.
- Two-peer MP test with mismatched loadouts, and with an unknown item id.
- Unlock flow: fresh profile → starters only; forced stats → unlock + toast; reload → persists.

## Open questions

1. Base rebuild route: cut the Meshy mesh (a) or new Blender body (b)?
2. Should the default look stay exactly today's pickle wizard (hat + staff) so nothing changes for
   players until they customize? (Recommended: yes.)
3. Unlock pace: a few hours to unlock most, or longer-tail?
4. Doubles back-row wizards: their own loadout, or mirror the front player's?
