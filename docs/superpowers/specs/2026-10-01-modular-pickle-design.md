# Modular pickle character — design spec (2026-10-01)

Owner-approved in chat (sections 1–4 + Character Lab). Goal: rebuild the pickle wizard from parts on our own
skeleton so cosmetics can be added later (pickle base → eyes → mouth → clothes). Reference: PEAK (shared base,
painted swappable face, clothes as separate pieces). Look: low-poly, chunky, pixel-first textures.

## 1. Build contract (Blender → game)

Script: `tools/blender/build_pickle.py` (procedural, same conventions as build_props*.py). Blender metres = game
units. Character faces **Blender −Y** (verify in the Lab; the loader owns the facing fix-up).

**Size.** Matches today's pickle: body top (no hat) ≈ 1.70, footprint ≈ 0.9 wide × 0.9 deep, origin on the ground
between the feet.

**Skeleton** (one armature `PickleRig`, identical bone set + order in every export):
`root, hips, body_lo, body_mid, body_hi, head, arm_L_up, arm_L_lo, hand_L, arm_R_up, arm_R_lo, hand_R,
leg_L_up, leg_L_lo, foot_L, leg_R_up, leg_R_lo, foot_R` + socket bones (no body weights):
`sock_hat` (← head), `sock_face` (← head), `sock_staff` (← hand_R), `sock_chest` (← body_mid).

**Base** `models/pickle2/pickle_base.glb`: armature + mesh `pickle_body` with materials
- `M_skin` — pixel-first green cucumber texture (stripes, warts), NEAREST.
- `M_face` — the face patch on the upper third, front; its UVs span 0..1 across a roughly square patch. The game
  paints the face onto this material at runtime.

Animation groups, named exactly: `idle`, `left`, `right`, `cast_loop` (loops), `cast_release` (~0.3 s),
`parry` (~0.25 s), `victory` (~2 s), `defeat` (~1.5 s, ends lying down). Cartoon squash-and-stretch through the
body bones; mitten hands; stubby limbs.

**Parts** `models/pickle2/parts/<id>.glb`: every part is a mesh skinned to the SAME `PickleRig` (same bones, same
order, same rest pose). Body-wrapping parts (outfit, neck) are weighted to body/leg bones; rigid parts (hat,
face accessory, staff) are 100 % weighted to their socket bone. Team-coloured areas use material `M_team`
(white albedo, tinted at runtime). First set: `hat_wizard` (starry purple, team band), `outfit_robe` (purple
cloak, team trim), `staff_classic` (wood + team gem).

## 2. Face

Strips in `textures/face/`, pixel-first, frames side by side:
- `eyes_<id>.png` — 5 frames of 48×20: open, blink, hurt, focus, happy.
- `mouth_<id>.png` — 4 frames of 32×14: neutral, open, grimace, grin.

Per wizard a 64×64 canvas = skin colour fill + eye frame at (8, 10) + mouth frame at (16, 36), applied to `M_face`
(NEAREST). Expressions (visual only): blink every 3–6 s; hurt 0.5 s when their structure takes damage; focus while
casting; open on cast release; happy + grin on victory; hurt on defeat. First set: `eyes_classic`, `mouth_smile`.

## 3. Catalogue, loadouts, team colour

`COSMETICS` (one list in index.html): `{ id, name, slot, file | strip }`. Slots: `hat`, `outfit`, `neck`,
`face_acc`, `staff` (required), `eyes`, `mouth`. Loadout = slot→id in localStorage (`volleybolt_loadout`);
default = `hat_wizard, outfit_robe, staff_classic, eyes_classic, mouth_smile`. AI uses the default. `M_team` takes
the slot's team colour (Blue / Red / back-row variants / colour-blind red). The pickle body is never tinted.

## 4. Runtime

`loadPickleCharacter(slot, loadout)` replaces `loadPickleWizard`'s per-slot body: base loaded per wizard, parts
bound to that wizard's skeleton (`mesh.skeleton = base skeleton`, parented like the base mesh), face canvas,
team tint. Keeps the existing contract: `target.animations` with `idle, left, right, cast_loop, cast_release,
parry, parry_release, victory, defeat, defeat_fall` (parry_release / defeat_fall derived as today), flash meshes,
rendering group 1, PS1 snap off, NEAREST sampling, doubles back-row cache. Behind `CHARACTER_VERSION` (2 = new,
1 = old pickle) until approved. Missing part → that slot's default/empty + warning. Online: loadouts exchanged at
match start, visual only (never in sim/hash/rollback).

## 5. Character Lab

`index.html?lab` (also reachable from the menu later as the wardrobe): one pickle on a small stage with the real
renderer/lighting; drag to spin, wheel to zoom; slot pickers; clip player (loop / step); team toggle; expression
triggers; reload-files button (dev extras only under `?lab`).

## 6. Testing

Lab for every clip/part/expression/team; one real singles, doubles and spectate match; `dbg.determinism` and
`aiDeterminism` unchanged; headless sim skips characters as today.

Out of scope: unlock rules, wardrobe polish, more items, dyes.
