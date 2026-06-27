# Juice — Ultimate / Limit-Break System (Design)

**Date:** 2026-06-27
**Project:** Volleybolt
**Status:** Approved — implement directly (user opted to skip the plan/review gate)

## Goal

A third Status-panel bar ("Juice" — pickle-themed limit break) that fills from a
combatant's actions and, when full, can be spent (Q) to enter a short **rapid-fire
burst window**: free mana + halved cooldowns for 8 seconds, with a golden
"Super-Saiyan" aura as the tell. Fully symmetric — the AI has the identical mechanic.

## Core principle

Per [[volleybolt-symmetry-principle]]: built symmetric for both combatants. Same charge
values, same activation, same effects. The only AI-specific piece is *when* the bot
activates (competence/timing), never different numbers.

## The bar

- The reserved **3rd Status-panel column** becomes the Juice gauge: 0→100, thin bar in
  the HP/MP style but **gold**. Per combatant (player + AI rows).
- Status panel re-spaced to fit Name + HP + MP + **Juice** within the 360px box
  (narrower bars, even columns).

## Charging — additive, never decreases until spent

`addJuice(side, amount)`, capped at `JUICE_MAX = 100`. Mild **catch-up lean** — taking
damage is the biggest source, so a player on the back foot builds toward a comeback.

| Event | Charge |
|---|---|
| Take tower damage | **+12 per damage point** (biggest — catch-up engine) |
| Cast a spell | **+8** |
| Clean / perfect parry | **+10** |
| Block / overpower / cancel | **+4** |

Tuned so a full bar is roughly a round or two of active play. All values are dials.

## Activation

- At 100, a **"JUICE READY"** indicator appears next to the COMMAND window title.
- Press **Q** → only if `juice >= JUICE_MAX && !juiceActive` and gameplay is active →
  bar resets to 0, enter Juice mode for `JUICE_DURATION = 8s`.
- A power-up SFX fires on activation.

## Juice mode (8s)

- **Free mana:** while active, casting deducts 0 mana (cost check bypassed).
- **Halved cooldowns:** cooldowns set after a cast during the window are × 0.5.
- **No damage change.**
- **Tells:** golden particle aura on the combatant's character (Super-Saiyan), the
  command-window border animates gold, COMMAND tab can pulse.
- Per-frame: decrement timer by `dt`; at ≤0, deactivate — revert aura/border, bar
  refills from 0. Can't re-trigger while active or below full.

## Symmetry / AI

Identical data + effects for the AI combatant. AI activates on competence-based timing
(bar full + has pressure/targets to apply); higher difficulty = smarter timing, never
faster charge or cheaper cost.

## Touch points (implementation map)

- **Data:** `combatant.juice`, `combatant.juiceActive`, `combatant.juiceTimer`.
- **Charge hooks:** tower-damage application, cast (startCasting / castFrostbolt /
  castChainLightning / fireball), perfect-parry path, block/overpower/cancel resolution.
- **Effects:** mana-cost check + cooldown-set in the cast path gated on `juiceActive`.
- **Input:** keydown `KeyQ` → `activateJuice('player')`.
- **UI:** Status panel 3rd column + `setStatus`; "JUICE READY" near COMMAND title;
  command-box border animation.
- **VFX/SFX:** gold aura particle system parented to the character mesh; activation sound.
- **AI:** activation check in the AI decision loop.

## Out of scope (this pass)

- Per-spell Juice-cost variation; multiple ultimate types; Juice carrying across matches.
