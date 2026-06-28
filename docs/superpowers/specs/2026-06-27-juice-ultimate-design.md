# Juice — Ultimate / Limit-Break System (Design)

**Date:** 2026-06-27
**Project:** Volleybolt
**Status:** Approved — implement directly (user opted to skip the plan/review gate)

## Goal

A third Status-panel bar ("Juice" — pickle-themed limit break) that fills from a
combatant's actions and, when full, can be spent (Q) to enter a short **power
burst window** (8 seconds) with a golden "Super-Saiyan" aura as the tell. Fully
symmetric — the AI has the identical mechanic.

**Burst behavior (post-rework, shipped):** activation resets all cooldowns **once**;
mana and cooldowns are otherwise normal during the burst (this replaced the original
"free mana + halved cooldowns", which was too big a tempo swing). The strength comes
from quality instead: the caster's fireball still has its cast time but comes out at
the **full 6-damage tier** — the size and speed of a maxed-out volley — and the
combatant **auto-perfect-parries** every incoming projectile, ignoring the parry
cooldown and manual-parry timing window.

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

## Juice mode (8s) — post-rework

- **Cooldown reset (once):** on activation, all of the combatant's cooldowns are set
  to 0 a single time. Cooldowns then tick normally for the rest of the burst.
- **Normal mana / cooldowns:** no free casts, no cooldown scaling during the window.
- **Full-tier fireball:** a fireball cast (or spawned) by the juiced combatant comes
  out at `volleyCount = 4` → 6 damage, scaled to full size and launched at `maxSpeed`,
  matching a maxed-out volley. Still has its normal cast time.
- **Auto-perfect-parry:** every projectile that reaches the juiced combatant's paddle
  is parried (reflected) regardless of parry cooldown or manual-parry timing. The
  redundant " parries!" combat-log line is suppressed during the burst to avoid
  flooding the log; the parry sound/VFX still play.
- **Tells:** golden flame aura on the character, a white silhouette outline so the
  model stays readable, gold model tint, gold command-window border, and the COMMAND
  tab title shows "JUICE" while active. "JUICE READY" replaces the tab title when the
  bar is full and not yet spent.
- Per-frame: decrement timer by `dt`; the bar drains as time remaining. At ≤0,
  deactivate — revert aura/outline/tint/border, bar sits empty. Can't re-trigger while
  active or below full. Juice does not carry across matches (cleared in `resetGame`).

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
