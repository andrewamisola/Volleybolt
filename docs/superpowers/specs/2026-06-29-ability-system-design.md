# Ability System — Design Spec (Phase 1)

**Date:** 2026-06-29
**Status:** Draft for Director review
**Author:** Claude (with Andrew)
**Depends on:** the extracted deterministic sim (`js/sim.js`), the `dbg.determinism` oracle (golden seed 12345 → `b1df6797`), and the project **game-design-philosophy** memory (no randomness; simple deterministic abilities).

## 1. Problem

Adding or changing an ability today means surgery across the codebase. The architecture maps found:

- **Four overlapping registries** holding ability data — `spells`/`SpellRegistry`, `ABILITY_REGISTRY`, `AbilityRegistry`, `UpgradeRegistry` — with **contradictory values** (e.g. frostbolt cooldown 7 vs 14; chain-lightning costs 2 mana in code but "0" in the loadout UI) and a large `AbilityRegistry` layer (`damageScaling`, `canParry`, `effects`) that **nothing reads**.
- **~50 hardcoded per-ability branch sites** (`if (abilityId === 'fireball')`, `proj.type === 'frostbolt'`, …) spread across **three** game loops: single-player `updateGameLogic`, the PvP sim (`js/sim.js`), and a separate doubles-AI loop.
- Only **`UpgradeRegistry` stores actual behavior** (its `onSpawn`/`onUpdate`/`shouldSplit`/`onSplit` callbacks) — but those callbacks are **Babylon-coupled** (they read/write `proj.mesh.position`, call `playSound` directly), so they are not determinism-safe as written.

The goal: **one canonical ability definition, where each ability declares its own stats and behavior**, so adding an ability is one self-contained entry and the hardcoded branches disappear — without ever breaking determinism.

## 2. Scope

**In scope (Phase 1):**
- **1A — Canonical data registry.** Collapse the four registries into one `ABILITIES` source of truth; resolve the contradictory values; derive/replace all consumers; delete dead duplicate data. *Behavior-neutral* (the oracle golden must not change).
- **1B — Behavior interface + PvP migration.** Define a deterministic ability-behavior interface and migrate the **PvP sim's** per-ability branches (`js/sim.js`) to call it. Done **one ability at a time, oracle-verified**. Also wires **chain lightning into multiplayer** (today PvP has no chain lightning — a feature gap).

**Out of scope (later phases):**
- **Phase 2 — Sim unification.** Folding single-player + doubles onto the one deterministic engine (and converting the AI to deterministic input). Single-player keeps its own hardcoded behavior branches until then; Phase 1 does **not** touch `updateGameLogic`. The behavior *interface* built in 1B is what Phase 2 will reuse so there is ultimately one place per ability.
- **Phase 3 — Board entities** (Stone Wall and other placed/HP abilities).

**Why PvP-first (Director-approved):** the PvP sim is small, pure, and guarded by the oracle — the safest surface to prove the interface on. The cost is *temporary* duplication (PvP behavior declarative, single-player behavior still hardcoded) until Phase 2 removes the single-player copy. Accepted.

## 3. The canonical registry

`ABILITY_REGISTRY` already wins in practice: the live `abilities` object the gameplay code reads is **derived** from it (`for (id in ABILITY_REGISTRY) abilities[id] = {...gameplay}`), and it cleanly separates `gameplay` from `ui`. So consolidation = **promote `ABILITY_REGISTRY` to the single source of truth, add a `behavior` block, and make every other consumer derive from it (or delete the dead copy).**

Canonical shape per ability:

```js
ABILITIES = {
  fireball: {
    gameplay: { cooldown, castTime, baseSpeed, maxSpeed, damage, manaCost, freezeDuration?, maxZaps? },
    ui:       { name, key, iconClass, manaCostLabel, castLabel, cooldownLabel, description },
    behavior: { /* see §4 — added in 1B */ },
  },
  ...
}
```

- The loadout UI (`spells`/`SpellRegistry`, `DEFAULT_LOADOUT`) derives `name`/`manaCost`/`cooldown`/`castFn` from `ABILITIES[id].ui` + `.gameplay` instead of holding its own copy.
- `AbilityRegistry`'s genuinely-used bits (if any survive an audit) move into `behavior`; the dead fields (`damageScaling`, `canParry`, `canBlock`, `effects`) are **deleted** (no code reads them; they are aspirational). If the Director wants any of them to become *real*, that is a separate feature, not part of this consolidation.

### Values reconciliation (Director to ratify)

The live (`ABILITY_REGISTRY`-derived) values are the proposed canon, because they are what actually runs today:

| Ability | Field | Live value (canon) | Stale/contradptory source | Note |
|---|---|---|---|---|
| fireball | cooldown / castTime / manaCost | 4s / 1.0s / 1 | — | volley damage `min(2+volley,6)` stays hardcoded for now |
| frostbolt | cooldown | **7s** | `spells`/`AbilityRegistry` say 14 | keep 7 (live) — or raise to 14 if intended |
| frostbolt | castTime / manaCost / freeze | instant / 2 / 1.0s | — | |
| chain_lightning | manaCost | **2** | loadout UI says "0 / doesn't cost mana" | keep 2 (code spends 2) — or make it free if intended |
| chain_lightning | cooldown / maxZaps | 30s / 3 | `AbilityRegistry` says 20 | keep 30 (live) |
| chain_lightning | "+1 mana per zap" | **not implemented** | descriptions claim it | decide: implement, or drop the claim from text |

Ratifying these is the only place Phase 1 might *intentionally* change behavior (and thus the golden hash). Everything else in 1A is a pure data move with the golden unchanged.

## 4. The behavior interface (1B)

Generalize the `UpgradeRegistry` callback pattern into a per-ability interface, **ported to be deterministic** (pure functions over sim state + injected deps — the same contract the sim already follows). All callbacks operate on `proj.x/y/z` (never `proj.mesh`), pull effects from `ctx.deps.*`, and gate presentation with `ctx.isResimulating`.

```js
behavior: {
  castType: 'channel' | 'instant' | 'targeted',   // 'targeted' = acts on existing projectiles (chain lightning)
  onCast(ctx, combatant, side),            // cast completes: spawn projectile / zap / (later) place entity
  onSpawn(proj, ctx),                      // initialize a freshly spawned projectile (pure)
  onUpdate(proj, dt, ctx),                 // per-tick motion (most abilities: omit). Pure x/y/z.
  onPaddleHit(proj, side, ctx) -> bool,    // volley response (fireball bounce vs frostbolt freeze). returns "consumed"
  onGateHit(proj, side, ctx),              // tower damage (fireball) or fizzle (frostbolt)
}
```

The PvP sim loop replaces its `if (proj.type === 'frostbolt') … else …` branches with `getAbility(proj.type).behavior.onPaddleHit(proj, side, ctx)` etc. Abilities own their own logic; the loop just dispatches.

**Determinism rule (hard):** no `Math.random`/`Date.now`/`performance.now` in any behavior callback; variety comes from interaction, never dice (per the game-design-philosophy). Porting `UpgradeRegistry`'s magma-lob (the one rich existing behavior) to pure x/y/z is the proof-of-concept that the interface is expressive enough.

## 5. Migration plan (safe, incremental, oracle-verified)

Each step is its own commit; the `dbg.determinism` oracle runs after every step. The golden stays `b1df6797` **except** where a step intentionally changes behavior (ratified values, or adding chain-lightning to PvP) — those re-baseline explicitly and are called out.

**1A — data consolidation (oracle-neutral):**
1. Promote `ABILITY_REGISTRY` → canonical `ABILITIES`; add empty `behavior: {}` per ability. Verify golden unchanged.
2. Repoint `spells`/loadout/`DEFAULT_LOADOUT` and any consumers to derive from `ABILITIES`. Delete the dead `AbilityRegistry` fields. Verify golden unchanged + loadout UI still works (visual).
3. Apply the ratified value reconciliation (§3). If any value changes, re-baseline golden and note it.

**1B — behavior interface, PvP, one ability at a time:**
4. Define the interface + a `getAbility(id)` accessor. Migrate **frostbolt** (simplest): `onCast`, `onPaddleHit` (freeze+destroy), `onGateHit` (fizzle). Route the sim's frostbolt branches through it. Verify golden unchanged; spy to confirm the callback runs.
5. Migrate **fireball**: `onCast` (channel), `onPaddleHit` (pong deflection + volley), `onGateHit` (damage). Verify golden unchanged.
6. **Wire chain lightning into PvP** via `castType: 'targeted'` + `onCast` (zap incoming). This *adds* an ability to MP. Keep the determinism harness inputs to fireball/frostbolt/parry so the golden stays comparable; verify a separate scripted chain-lightning scenario is deterministic.
7. **Cleanup:** delete the now-empty hardcoded per-ability branches in `js/sim.js`; delete remaining dead registry data. Verify golden + play.

After Phase 1: the PvP sim is fully declarative and there is **one** canonical ability registry. Single-player/doubles still branch (Phase 2 territory), but they read the same canonical stats.

## 6. Components & data flow

- **`ABILITIES`** (index.html) — the one registry: stats + ui + behavior. Single source of truth.
- **`getAbility(id)`** — accessor used by the sim and (later) all consumers.
- **`js/sim.js`** — the PvP loop dispatches collision/cast to `behavior.*`. Behavior callbacks receive the same `ctx` (`{projectiles, combatants, abilities, pvpParryState, isResimulating, consts, deps}`) the sim functions already use.
- **`SIM_DEPS`** — behavior callbacks reach all presentation/spawn effects through here (no direct Babylon).
- **Consumers** (loadout screen, tooltips, key bindings) — derive from `ABILITIES.ui`.

## 7. Determinism & testing

- The `dbg.determinism` oracle is the gate for every step (reproducible + golden comparison + spy that the new code path actually runs).
- Behavior callbacks are pure over (state, deps); no RNG, no wall-clock, no mesh reads — verified the same way the sim port was (golden-identical + dead-mesh test where relevant).
- Visual single-player check after each step (loadout UI + a real match) since single-player shares the registry.

## 8. Risks & mitigations

- **Temporary behavior duplication** (PvP declarative, single-player hardcoded) until Phase 2. *Mitigation:* both read the same canonical stats; Phase 2 deletes the single-player copy. Accepted as the safest sequencing.
- **Porting `UpgradeRegistry` behavior to pure form** is real work (it's Babylon-coupled today). *Mitigation:* upgrades/talents don't run in the PvP sim today, so Phase 1B can ship core abilities (fireball/frostbolt/chain) declaratively first and port upgrades when Phase 2 brings them into the deterministic engine. Flagged, not blocking.
- **A ratified value change alters MP feel.** *Mitigation:* surfaced explicitly in §3 for Director sign-off; re-baseline the golden when it happens.
- **Hidden consumer of a "dead" field.** *Mitigation:* grep each field before deleting; keep deletions in their own commit so they're trivially revertable.
