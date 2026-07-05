# Juice Rework — "Overdrive" Beam Ultimate — Design Spec

**Date:** 2026-07-05
**Status:** Draft for Director review
**Author:** Claude (with Andrew)
**Depends on:** the deterministic sim (`simulateNetworkFrame`), the ability/charge system (`JUICE`, `addJuice`, `activateJuice`, `updateJuice`), the projectile system, and the project **symmetry principle** memory (player & AI/opponent mechanically identical).

---

## 1. Problem

The current Juice mechanic underdelivers:
- **Too short / low impact.** Activating a full bar grants an 8-second *buff burst* (reset cooldowns once, full mana, rapid-fire) via `activateJuice`. It reads as a minor tempo boost, not a signature "turn the tide" moment.
- **Charges mostly on damage.** `JUICE.CHARGE` has entries for cast/parry/damage/block, but in practice it fills mainly from taking damage — the action-charge paths don't reliably fire (especially through the unified/MP sim), so it feels like a damage meter rather than a reward for playing actively.

## 2. Goal

Replace the buff burst with a **channeled beam ultimate ("Overdrive")**: a committed 6-second beam that the caster aims by moving, that the opponent survives by staying out of its lane (or by landing a Frostbolt to interrupt it). It should be a genuine tide-turner (~45% of a health bar if fully connected) without being an auto-win. Charging rewards *all* action, not just getting hit.

**Hard invariant (symmetry principle):** both players charge and fire Overdrive identically — same charge table, same beam, same numbers. No side gets a stronger version.

**Hard invariant (determinism):** all Overdrive gameplay (channel state, per-tick damage, the lane-match block test, projectile disintegration, Frostbolt interrupt) lives in the deterministic sim (fixed timestep, no wall-clock, no `Math.random`). The beam *visual* is presentation-only (reads sim state, never writes it). The determinism oracles must stay green and are extended to exercise the beam.

**Scope:** the Juice mechanic only. Does not touch the netcode driver, the AI's non-Juice behavior, or other spells' balance (beyond charging on their cast).

## 3. Charging

Keep the `JUICE.CHARGE`-on-action model; make it fire on **every** meaningful action, through the sim path so it works in SP and MP:

- **Cast a spell** (Fireball / Frostbolt / Thunderstorm) → `CHARGE.cast`
- **Land a parry** → `CHARGE.parry`
- **Deal damage** (per damage point) → `CHARGE.damage`
- **Take damage / get blocked / overpowered** → `CHARGE.minor` (or `damage` on taking a hit)

No charging while Overdrive is active. Tune `CHARGE` and `JUICE.MAX` so a full bar takes roughly **1–2 rounds of active play** (fast enough to see it, slow enough that it's a moment). Exact values are a tuning pass.

## 4. Activation → the beam

When the bar is full and the caster is not frozen / not already channeling, pressing the ult input starts **Overdrive**:
- Consumes the **full** Juice bar (the bar becomes the channel timer, draining 100→0 over the duration — reuse the existing drain-as-duration pattern).
- Sets a channel state on the combatant (reuse `juiceActive` = "channeling", `juiceTimer` = remaining channel seconds).
- The old buff effects (reset all cooldowns, grant full mana, rapid-fire `cooldown = 0`) are **removed**.

While channeling, the caster **cannot cast other spells** (the ult is a full commitment) but **can move up/down** (Z) at normal speed to aim the beam.

## 5. The beam (deterministic sim mechanic)

- **Duration:** `OVERDRIVE.DURATION = 6` seconds.
- **Geometry:** a beam along the caster's forward axis (+X for the left combatant, −X for the right) at the caster's **current paddle Z** — i.e. it occupies the caster's lane and sweeps up/down as the caster moves.
- **Lane-match block (per sim tick):** the beam is **blocked** while the opponent's paddle Z is within `OVERDRIVE.BLOCK_TOL` of the beam's Z; otherwise it **connects**.
  - `BLOCK_TOL` ≈ the paddle's effective block half-width (tune so "on their paddle = safe, off it = hit").
- **Damage (DoT, only while connecting):** ramps with **sustained connection** — weak on first contact, strong if held on target; **being blocked resets the ramp**. Direct damage to the opponent's `towerHealth`.
  - Starting curve (TUNABLE, anchored on the total below): rate ramps from `~4%/s` to `~10%/s` of max health over ~2.5s of continuous connection.
  - **Anchor:** a **fully-connected 6s beam ≈ 45%** of a health bar; a **well-defended beam ≈ 15–25%**. The total is the balance anchor; the per-second rate is derived and tuned to hit it.
- **Projectile interaction:**
  - **Fireballs** the beam touches are **disintegrated** (vaporized, no effect) — so the caster is immune to fireball damage during the channel.
  - **Frostbolt is NOT disintegrated.** It passes through the beam and, if it reaches the caster's paddle (standard frostbolt-vs-paddle hit), **freezes the caster and interrupts Overdrive** (channel ends, freeze applies). This is the intended counter: hard to land because the caster is moving, but it shuts the beam down.
  - (Thunderstorm is a projectile-clear; it does not affect the beam itself.)
- **Interruption:** the channel ends early only on a **Frostbolt freeze** (or round end). Fireballs cannot interrupt it (they're disintegrated).
- **End of channel:** clears the channel state, returns the caster to normal (can cast again).

## 6. What is removed

| Removed | Reason |
|---|---|
| Buff burst in `activateJuice` (reset cooldowns, full mana) | Replaced by the beam |
| Rapid-fire `cooldown = 0` during `juiceActive` (~line 13889 and similar) | No buff mode anymore |
| `JUICE.DURATION = 8` buff timer semantics | Repurposed as the 6s channel timer (`OVERDRIVE.DURATION`) |

The juice *aura* visual may be repurposed as the beam's caster FX; the drain-as-timer bar logic is reused for the channel.

## 7. Symmetry & determinism

- Both combatants use the identical charge table and beam. The AI can charge and fire Overdrive under the same rules (the AI decision to fire it is a later, separate concern — for now the AI may simply fire when full, symmetric to the player's option).
- **All beam gameplay is in the sim** (`simulateNetworkFrame` path): channel tick, connect/block test (reads paddle Z from sim state), ramp accumulator, per-tick `towerHealth` damage, fireball disintegration, Frostbolt interrupt. No wall-clock, no `Math.random`.
- **The beam visual is presentation-only** (`updateMatchPresentation`), reading `juiceActive`/`juiceTimer`/caster Z; it never writes sim state (mirrors the existing FX read-only rule so MP can't desync on visuals).
- **Determinism oracles:** `dbg.determinism(180,12345)` and `dbg.aiDeterminism(50,42)` must stay green. The sim-hash (`hashGameState`) must include any new *simulated* channel state that affects outcomes (channel timer, ramp accumulator) so a desync in the beam is caught. Extend `dbg.determinism`'s scripted sequence to fire an Overdrive so the beam path is covered; re-pin its golden.

## 8. Tunable values (starting points)

```
OVERDRIVE.DURATION   = 6        // seconds
OVERDRIVE.BLOCK_TOL  = <paddle block half-width>  // Z tolerance for "blocked"
OVERDRIVE.DMG_START  = 0.04     // fraction of max HP / sec on first connect
OVERDRIVE.DMG_MAX    = 0.10     // fraction / sec at full ramp
OVERDRIVE.RAMP_TIME  = 2.5      // seconds of sustained connection to reach DMG_MAX
JUICE.MAX / CHARGE   = tuned so a full bar ~= 1–2 rounds of active play
```
All are first guesses; final values come from playtest. The **~45% fully-connected total** is the anchor.

## 9. Verification & acceptance

- **Determinism:** oracles green after the change (sim golden re-pinned once, AI golden unaffected unless the AI's Juice decision changes — keep it out of `decideAI` scope for now).
- **SP smoke:** bar charges from casting/parrying/hitting (not just taking damage); pressing ult fires a 6s beam; moving aims it; the AI standing in the lane blocks it, off-lane takes ramping damage; a fully-connected beam does ~45%; a Frostbolt to the moving caster freezes and interrupts it; Fireballs into the beam vaporize.
- **MP:** in a 2-peer match, both peers see the same beam, same damage, same interrupt — `sync` stays green (this is the reason the beam state is in the hash). To be confirmed in the live cross-network test alongside the netcode fixes.
- **Symmetry audit:** confirm no Juice value differs between the two combatants.
