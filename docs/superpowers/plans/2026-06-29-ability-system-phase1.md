# Ability System Phase 1 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate Volleybolt's four contradictory ability registries into one canonical `ABILITY_REGISTRY`, rename the `chain_lightning` ability to `thunderstorm` everywhere, and make the PvP sim's per-ability logic declarative (each ability declares its own behavior) — without ever changing the determinism golden except where intended.

**Architecture:** `ABILITY_REGISTRY` (index.html) is already the de-facto source of truth (the live `abilities` object derives from it). We extend it with a `behavior` block of pure deterministic callbacks, add a `getAbilityDef(id)` accessor, route the PvP sim (`js/sim.js`) per-ability branches through `behavior.*`, and delete the dead duplicate registries/branches. Behavior callbacks follow the same contract the sim already uses: pure math on `proj.x/y/z`, all effects through `ctx.deps`, presentation gated by `ctx.isResimulating`.

**Tech Stack:** Vanilla JS single-page game; Babylon.js render; PeerJS rollback netcode; `js/sim.js` ES module bridged via `window.VolleyboltSim`. No build step, no unit-test framework.

## Global Constraints

- **Determinism law:** no `Math.random`/`Date.now`/`performance.now`/`new Date()` in any sim or behavior code. Variety comes from interaction, never dice.
- **The oracle is the gate.** Golden baseline: `dbg.determinism(180, 12345)` → `b1df6797` (seed 999 → `d769a77`). After every task the golden must be unchanged, UNLESS the task is explicitly marked **RE-BASELINE** (intentional behavior change) — then record the new value and update `js/sim.js`'s header comment + the determinism memory.
- **Browser dev-cache caveat:** the browser caches BOTH `index.html` and `js/sim.js` per session. To test edits, navigate to `http://localhost:8000/index.html?cb=<unique>` AND `await import('/js/sim.js?v=' + Date.now())` before running checks. The server runs via `python3 -m http.server 8000` from the repo root (already running).
- **Ratified values (do not "fix"):** frostbolt cooldown 7s, thunderstorm 2 mana, thunderstorm cooldown 30s / 3 zaps, fireball 4s/1.0s/1 mana. The "+1 mana per zap" text is dropped (it was never implemented).
- **Scope:** PvP sim (`js/sim.js`) only. Do NOT modify single-player `updateGameLogic` behavior branches or the doubles-AI loop — they keep working off the same canonical stats and are migrated in Phase 2.
- **Inline-is-authoritative:** the game runs from the inline `<script>` in index.html; `js/*` modules only run if explicitly loaded. Never rely on a module to shadow inline.

---

## The standard verification recipe (referenced by every task as "VERIFY")

Run these in the browser via the playwright MCP tools. "VERIFY(golden=X)" means the expected fold is X.

1. Navigate to `http://localhost:8000/index.html?cb=<unique>` (fresh document).
2. `await import('/js/sim.js?v=' + Date.now())` (fresh module).
3. Click the page once (dismiss "Click to Start"), then `window.startSinglesMatch()`, wait ~2s.
4. `const a = window.dbg.determinism(180,12345), b = window.dbg.determinism(180,12345), c = window.dbg.determinism(180,999);`
   - Assert `a.fold === b.fold` (reproducible).
   - Assert `a.fold === '<golden>'` (or record the new value if RE-BASELINE).
   - Assert `a.fold !== c.fold` (seed-sensitive).
5. Screenshot — confirm the match renders (scoreboard, towers, paddles, projectiles) and the console shows only the favicon 404.

---

## Task 1: Drop the dead "+1 mana per zap" text + add `getAbility` accessor

**Files:**
- Modify: `index.html` — `ABILITY_REGISTRY` (~line 2133–2158), and add `getAbility` just after the `abilities` derivation (~line 2165).

**Interfaces:**
- Produces: `getAbilityDef(id)` → the `ABILITY_REGISTRY[id]` entry (or `undefined`); `window.getAbility` exposed. Used by later tasks and the sim.

- [ ] **Step 1:** In `ABILITY_REGISTRY.chain_lightning.ui.description`, remove the sentence "Gain 1 Mana for each projectile destroyed." (the `<span ...>1</span> Mana for each...` clause). Leave the rest of the description intact.

- [ ] **Step 2:** Immediately after the `abilities` derivation loop (the line `window.abilities = abilities;`), add:

```js
// Canonical ability accessor — single lookup point for stats + behavior.
function getAbilityDef(id) { return ABILITY_REGISTRY[id]; }
window.getAbility = getAbility;
```

- [ ] **Step 3:** VERIFY(golden=`b1df6797`). Also in the browser console assert `typeof window.getAbilityDef('fireball') === 'object'` and `window.getAbilityDef('fireball').gameplay.cooldown === 4`.

- [ ] **Step 4:** Commit.

```bash
git add index.html
git commit -m "Ability registry: add getAbility accessor; drop unimplemented per-zap mana text"
```

---

## Task 2: Add an empty `behavior` block to each ability (scaffolding, oracle-neutral)

**Files:**
- Modify: `index.html` — each entry of `ABILITY_REGISTRY` (~2134–2157).

**Interfaces:**
- Produces: every `ABILITY_REGISTRY[id]` now has a `behavior` object (empty for now). Later tasks fill it.

- [ ] **Step 1:** Add `behavior: {}` as a third key (alongside `gameplay` and `ui`) to `fireball`, `frostbolt`, and `chain_lightning` in `ABILITY_REGISTRY`. Example for fireball:

```js
fireball: {
    gameplay: { cooldown: 4, castTime: 1.0, baseSpeed: 12, maxSpeed: 20, damage: 1, manaCost: 1 },
    ui: { /* unchanged */ },
    behavior: {},
},
```

- [ ] **Step 2:** VERIFY(golden=`b1df6797`). Assert `window.getAbilityDef('frostbolt').behavior && typeof window.getAbilityDef('frostbolt').behavior === 'object'`.

- [ ] **Step 3:** Commit.

```bash
git add index.html
git commit -m "Ability registry: add empty behavior block per ability (scaffolding)"
```

---

## Task 3: Rename `chain_lightning` → `thunderstorm` everywhere (hash-neutral)

**Files:**
- Modify: `index.html` (registry id/key, `cooldowns.chain_lightning` field everywhere it's init/read/written, `castChainLightning`/`executeChainLightning`/`updateChainLightningChannel`/`startChainLightningChannel`/`endChainLightningChannel` function names + all call sites, `spellCastMap`, keybinding for Digit3, `CHAIN_LIGHTNING_MAX_ZAPS`/`CHAIN_LIGHTNING_COOLDOWN` consts, `SIM_DEPS.updateChainLightningChannel`, capture/restore/hash references to the cooldown key, the determinism harness's `cooldowns = {...}` reset).
- Modify: `js/sim.js` (`cooldowns.chain_lightning` decrement, `c.casting === 'chain_lightning'`, `D.updateChainLightningChannel`).

**Interfaces:**
- Produces: the ability id is `thunderstorm`; functions are `castThunderstorm`/`executeThunderstorm`/`updateThunderstormChannel`/`startThunderstormChannel`/`endThunderstormChannel`; cooldown key is `cooldowns.thunderstorm`; consts `THUNDERSTORM_MAX_ZAPS`/`THUNDERSTORM_COOLDOWN`; dep `SIM_DEPS.updateThunderstormChannel`.

- [ ] **Step 1:** Enumerate every reference first (do not edit yet):

```bash
grep -nE "chain_lightning|chainLightning|ChainLightning|CHAIN_LIGHTNING" index.html js/sim.js
```

Read the surrounding lines of each hit so the rename is mechanical, not guessed.

- [ ] **Step 2:** Apply the rename consistently. Mapping:
  - `chain_lightning` → `thunderstorm` (id + `cooldowns.*` key + `spellCastMap` key)
  - `castChainLightning` → `castThunderstorm`; `executeChainLightning` → `executeThunderstorm`; `updateChainLightningChannel` → `updateThunderstormChannel`; `startChainLightningChannel` → `startThunderstormChannel`; `endChainLightningChannel` → `endThunderstormChannel`
  - `CHAIN_LIGHTNING_MAX_ZAPS` → `THUNDERSTORM_MAX_ZAPS`; `CHAIN_LIGHTNING_COOLDOWN` → `THUNDERSTORM_COOLDOWN`
  - Leave the `ui.name: 'Thunderstorm'` as-is (already correct). Keep `iconClass: 'chainlightning-icon'` if it maps to a CSS class / asset name — rename the CSS class only if it has no external asset dependency (check; if a texture/sprite file is named chainlightning, leave the class name and add a code comment).

- [ ] **Step 3:** Confirm nothing was missed:

```bash
grep -nE "chain_lightning|chainLightning|ChainLightning|CHAIN_LIGHTNING" index.html js/sim.js
```
Expected: zero hits except any intentionally-left CSS/asset class noted in Step 2.

- [ ] **Step 4:** `node --check js/sim.js` → expect no output (valid syntax).

- [ ] **Step 5:** VERIFY(golden=`b1df6797`). The rename is hash-neutral: `hashGameState` mixes the cooldown *value*, not the key name. Also assert in console: `'thunderstorm' in window.getAbilityDef('thunderstorm').gameplay === false` is irrelevant; instead assert `window.getAbilityDef('thunderstorm') !== undefined` and `window.getAbilityDef('chain_lightning') === undefined`. Confirm a single-player match: cast Thunderstorm (key 3) and confirm it still zaps incoming projectiles (visual).

- [ ] **Step 6:** Commit.

```bash
git add index.html js/sim.js
git commit -m "Rename chain_lightning -> thunderstorm everywhere (hash-neutral); code now matches in-game name"
```

---

## Task 4: Behavior interface + migrate FROSTBOLT in the PvP sim

**Files:**
- Modify: `index.html` — `ABILITY_REGISTRY.frostbolt.behavior` (fill it in).
- Modify: `js/sim.js` — `tryNetworkCast` (frostbolt branch ~285–299) and `updateNetworkProjectiles` (frostbolt collision branches ~124–131 left, ~176–183 right; gate fizzle guard ~215/223).

**Interfaces:**
- Consumes: `getAbilityDef(id)` (Task 1); `ctx` = `{projectiles, combatants, abilities, pvpParryState, isResimulating, consts, deps}`.
- Produces: the behavior-callback contract, used by Tasks 5–6. **`side` is always `'left'/'right'` (the combatant side); callbacks derive the `'player'/'ai'` owner internally when needed.**
  - `behavior.castType: 'instant' | 'channel' | 'targeted'`
  - `behavior.onCast(ctx, combatant)` — cast resolves (spawn / zap). Reads `combatant.side`; no separate side param.
  - `behavior.onPaddleHit(proj, side, ctx) -> boolean` — `side` = the hit paddle's combatant side (`'left'/'right'`). Returns `true` if the projectile is consumed/destroyed (caller pushes to destroy), `false` if it bounced and continues.
  - `behavior.onGateHit(proj, side, ctx) -> {damage:number}|null` — `side` = `'left'/'right'`. `null` = no damage (fizzle).

- [ ] **Step 1:** Fill `frostbolt.behavior` in `ABILITY_REGISTRY`. `side` is `'player'|'ai'`; `combatant.side` is `'left'|'right'`. Spawn uses pure paddle position (`combatant.paddleX/paddleZ`). Effects via `ctx.deps`.

```js
behavior: {
    castType: 'instant',
    onCast(ctx, combatant) {
        const a = ctx.abilities.frostbolt;
        const owner = combatant.side === 'left' ? 'player' : 'ai';
        combatant.mana -= a.manaCost;
        combatant.cooldowns.frostbolt = a.cooldown;
        const velX = combatant.side === 'left' ? a.baseSpeed : -a.baseSpeed;
        const startX = combatant.side === 'left' ? combatant.paddleX + 1 : combatant.paddleX - 1;
        if (!ctx.isResimulating) ctx.deps.playSound('frostboltCast', startX, 0.7);
        ctx.deps.spawnFrostbolt(owner, startX, combatant.paddleZ, velX, 0); // factory assigns id
    },
    onPaddleHit(proj, side, ctx) {
        // side is the paddle being hit: 'left' or 'right'
        const c = ctx.combatants[side];
        c.freezeTime = ctx.abilities.frostbolt.freezeDuration;
        if (!ctx.isResimulating) {
            const px = c.paddleX;
            ctx.deps.playSound('frozen', px, 0.7);
            ctx.deps.showFrozenText(!!(c && c.isLocalPlayer));
        }
        return true; // consumed (destroy)
    },
    onGateHit(proj, side, ctx) { return null; }, // fizzle, no tower damage
},
```

- [ ] **Step 2:** In `js/sim.js` `tryNetworkCast`, replace the hardcoded `if (abilityId === 'frostbolt') { …instant spawn… }` block body with a dispatch through behavior for instant casts:

```js
const ability = abilities[abilityId];
if (!ability) return;
if (combatant.mana < ability.manaCost) return;
if (combatant.cooldowns[abilityId] > 0) return;
const beh = (ctx.deps.getAbilityDef ? ctx.deps.getAbilityDef(abilityId) : null)?.behavior;
if (beh && beh.castType === 'instant') {
    beh.onCast(ctx, combatant);
    return;
}
// (fireball channel path stays as-is for now — migrated in Task 5)
```

Add `getAbility: (id) => getAbilityDef(id)` to `SIM_DEPS` in index.html so the module can reach the registry.

- [ ] **Step 3:** In `js/sim.js` `updateNetworkProjectiles`, replace the left+right `if (proj.type === 'frostbolt') { freeze… } else { bounce… }` so the frostbolt arm calls the behavior. For the left paddle:

```js
const hitAbility = ctx.deps.getAbilityDef(proj.type);
if (hitAbility && hitAbility.behavior.onPaddleHit && proj.type === 'frostbolt') {
    if (hitAbility.behavior.onPaddleHit(proj, 'left', ctx)) { toDestroy.push(proj); }
} else {
    // existing fireball bounce branch unchanged (migrated in Task 5)
}
```
Mirror for the right paddle with `'right'`. Keep the Lightning-Shield auto-block check ABOVE this (unchanged). Note: `ctx` is not currently destructured in `updateNetworkProjectiles` — it receives `ctx`; add `const ctx = arguments`-free by changing the signature call to pass `ctx` (the function already gets `ctx`; reference `ctx.deps`/`ctx.combatants` etc. or destructure what you need at the top). Verify the function still reads `combatants`/`abilities`/`isResimulating` from its existing destructure and add `ctx` passthrough as needed.

- [ ] **Step 4:** For gate fizzle, the existing guard `if (proj.type !== 'frostbolt')` already encodes frostbolt's `onGateHit → null`. Leave it for now (fully generalized in Task 7); do not regress it.

- [ ] **Step 5:** `node --check js/sim.js`. Then VERIFY(golden=`b1df6797`) — frostbolt behaves identically, so the golden must NOT move. Additionally spy: wrap `getAbilityDef('frostbolt').behavior.onPaddleHit` and confirm it is invoked during a scripted frostbolt-into-paddle scenario, with the fold still `b1df6797`.

- [ ] **Step 6:** Commit.

```bash
git add index.html js/sim.js
git commit -m "Ability behavior interface: migrate frostbolt (cast + paddle freeze) to declarative behavior in the PvP sim"
```

---

## Task 5: Migrate FIREBALL in the PvP sim

**Files:**
- Modify: `index.html` — `ABILITY_REGISTRY.fireball.behavior`.
- Modify: `js/sim.js` — `tryNetworkCast` fireball channel branch (~300–309), `updateNetworkProjectiles` fireball bounce branches (left ~132–155, right ~184–207), gate damage (~211–227).

**Interfaces:**
- Consumes: the behavior contract from Task 4.
- Produces: `fireball.behavior` with `castType:'channel'`, `onPaddleHit` (pong deflection + volley), `onGateHit` (damage). `onCast` for a channel sets `casting` state; the actual spawn stays in `completeCasting`/`fireFireball` (render-side) for now.

- [ ] **Step 1:** Fill `fireball.behavior`. The pong-deflection math is copied verbatim from the current `js/sim.js` fireball arm (keep identical to preserve the golden):

```js
behavior: {
    castType: 'channel',
    onCast(ctx, combatant) {
        const a = ctx.abilities.fireball;
        combatant.casting = 'fireball';
        combatant.castProgress = 0;
        combatant.castTime = a.castTime;
        combatant.pendingManaCost = a.manaCost;
        if (!ctx.isResimulating) ctx.deps.castingStart();
    },
    onPaddleHit(proj, side, ctx) {
        const c = ctx.combatants[side];
        const px = c.paddleX, pz = c.paddleZ;
        const projRadius = proj.hitboxRadius || 0.25;
        const paddleHalfWidth = 0.2, paddleHalfDepth = 0.8;
        proj.x = side === 'left' ? px + paddleHalfWidth + projRadius : px - paddleHalfWidth - projRadius;
        const hitOffset = (proj.z - pz) / paddleHalfDepth;
        const currentSpeed = Math.max(Math.sqrt(proj.velX*proj.velX + proj.velZ*proj.velZ), 10);
        const angleStrength = hitOffset * 0.7;
        proj.velX = currentSpeed * Math.cos(angleStrength) * (proj.velX > 0 ? -1 : 1);
        proj.velZ = currentSpeed * Math.sin(angleStrength) * Math.sign(hitOffset || 1);
        proj.owner = side === 'left' ? 'player' : 'ai';
        proj.volleyCount++;
        ctx.deps.updateFireballScale(proj);
        if (c && !proj.isParried) c.mana = Math.min(ctx.deps.getMaxMana(side === 'left' ? 'left' : 'right'), c.mana + 0.5);
        if (!ctx.isResimulating) ctx.deps.playSound('block', px, 0.6);
        return false; // bounced, not consumed
    },
    onGateHit(proj, side, ctx) { return { damage: Math.min(2 + proj.volleyCount, 6) }; },
},
```

- [ ] **Step 2:** In `js/sim.js` `tryNetworkCast`, delete the now-dead `else if (abilityId === 'fireball')` block — the generic instant/channel dispatch must now also handle `castType: 'channel'`:

```js
if (beh && (beh.castType === 'instant' || beh.castType === 'channel' || beh.castType === 'targeted')) {
    beh.onCast(ctx, combatant);
    return;
}
```

- [ ] **Step 3:** In `js/sim.js` `updateNetworkProjectiles`, replace the fireball `else` bounce arm (both paddles) with the behavior dispatch, unifying the frostbolt/fireball handling from Task 4:

```js
const hitAbility = ctx.deps.getAbilityDef(proj.type);
if (hitAbility && hitAbility.behavior.onPaddleHit) {
    if (hitAbility.behavior.onPaddleHit(proj, 'left', ctx)) toDestroy.push(proj);
}
```
(and `'right'` for the right paddle). The Lightning-Shield block stays above it unchanged.

- [ ] **Step 4:** Replace the gate-collision damage with `onGateHit`:

```js
if (proj.x < -goalX) {
    const hitAbility = ctx.deps.getAbilityDef(proj.type);
    const res = hitAbility && hitAbility.behavior.onGateHit ? hitAbility.behavior.onGateHit(proj, 'left', ctx) : { damage: Math.min(2 + proj.volleyCount, 6) };
    if (res && res.damage) ctx.deps.dealDamageToTower(proj.owner === 'ai', res.damage, proj.z);
    toDestroy.push(proj);
} else if (proj.x > goalX) {
    const hitAbility = ctx.deps.getAbilityDef(proj.type);
    const res = hitAbility && hitAbility.behavior.onGateHit ? hitAbility.behavior.onGateHit(proj, 'right', ctx) : { damage: Math.min(2 + proj.volleyCount, 6) };
    if (res && res.damage) ctx.deps.dealDamageToTower(proj.owner === 'ai', res.damage, proj.z);
    toDestroy.push(proj);
}
```
(frostbolt's `onGateHit` returns `null` → no damage, preserving the fizzle.)

- [ ] **Step 5:** `node --check js/sim.js`. VERIFY(golden=`b1df6797`) — the math is copied verbatim, so the golden must NOT move. Spy `fireball.behavior.onPaddleHit` and `onGateHit` to confirm they run with the fold still `b1df6797`.

- [ ] **Step 6:** Commit.

```bash
git add index.html js/sim.js
git commit -m "Ability behavior: migrate fireball (cast/volley/gate) to declarative behavior; unify paddle+gate dispatch in the PvP sim"
```

---

## Task 6: Wire THUNDERSTORM into the PvP sim (RE-BASELINE expected only for thunderstorm scenarios)

**Files:**
- Modify: `index.html` — `ABILITY_REGISTRY.thunderstorm.behavior`; add `pendingNetInput.thunderstorm` handling in the PvP keydown branch; `defaultInput`/input capture/remote merge to carry a `thunderstorm` flag; `SIM_DEPS` zap effect if needed.
- Modify: `js/sim.js` — `simulateNetworkFrame` ability-input dispatch (add thunderstorm), `tryNetworkCast` targeted path.

**Interfaces:**
- Consumes: behavior contract; `executeThunderstorm` (renamed in Task 3) as the zap implementation.
- Produces: thunderstorm castable in PvP via `castType: 'targeted'`.

- [ ] **Step 1:** Fill `thunderstorm.behavior`:

```js
behavior: {
    castType: 'targeted',
    onCast(ctx, combatant) {
        const a = ctx.abilities.thunderstorm;
        if (combatant.cooldowns.thunderstorm > 0) return;
        if (combatant.mana < a.manaCost) return;
        const owner = combatant.side === 'left' ? 'player' : 'ai';
        // Deterministic zap of up to maxZaps incoming enemy projectiles, in stable id order.
        ctx.deps.thunderstormZap(owner, a.maxZaps, ctx); // dep wraps the renamed executeThunderstorm, made deterministic
        combatant.mana -= a.manaCost;
        combatant.cooldowns.thunderstorm = a.cooldown;
    },
},
```

- [ ] **Step 2:** Add `SIM_DEPS.thunderstormZap(owner, maxZaps, ctx)` in index.html (`owner` is `'player'/'ai'`, the caster) that performs the zap on the pure `projectiles` array: select incoming ENEMY projectiles (owner !== caster, heading toward the caster by velX sign) and destroy up to `maxZaps` of them in stable **id** order via `window.destroyProjectile`, gated so FX only fire when `!ctx.isResimulating`. Reuse the renamed `executeThunderstorm` internals but ensure NO `Math.random`/`Date.now` and NO mesh reads in the selection (use `proj.x`/`proj.velX`, not `proj.mesh.position.x`). Stable id order matters for determinism — do not sort by distance using floats that could tie.

- [ ] **Step 3:** In `js/sim.js` `simulateNetworkFrame`, add input dispatch:

```js
if (leftInput.thunderstorm && combatants.left) tryNetworkCast(combatants.left, 'thunderstorm', ctx);
if (rightInput.thunderstorm && combatants.right) tryNetworkCast(combatants.right, 'thunderstorm', ctx);
```
And in `tryNetworkCast`, the generic dispatch must handle `castType: 'targeted'` (same `beh.onCast(ctx, combatant, side)` path; targeted just doesn't spawn a projectile).

- [ ] **Step 4:** In index.html, set `pendingNetInput.thunderstorm = true` on the Digit3 keydown in the PvP branch (mirroring fireball/frostbolt), add `thunderstorm: false` to `defaultInput()` and the input capture/remote-merge shapes so it round-trips through the netcode.

- [ ] **Step 5:** `node --check js/sim.js`. VERIFY(golden=`b1df6797`) — the standard harness inputs (fireball/frostbolt/parry only) do NOT cast thunderstorm, so the golden must still be `b1df6797`. THEN run a **separate** scripted check: drive `simulateNetworkFrame` with a thunderstorm input present, capture the fold twice — assert it is reproducible (deterministic), and assert incoming projectiles get destroyed. (This is a NEW deterministic scenario; record its fold in the commit message, not as the global golden.)

- [ ] **Step 6:** Commit.

```bash
git add index.html js/sim.js
git commit -m "Wire Thunderstorm into the PvP sim (castType targeted, deterministic zap); MP feature gap closed"
```

---

## Task 7: Cleanup — delete dead registries and dead branches

**Files:**
- Modify: `index.html` — delete unused `AbilityRegistry` fields (`damageScaling`, `canParry`, `canBlock`, `effects`) after confirming zero readers; repoint `spells`/loadout to derive from `ABILITY_REGISTRY` if any duplicate values remain.
- Modify: `js/sim.js` — remove any now-dead `proj.type === '...'` branches superseded by behavior dispatch.

**Interfaces:**
- Produces: a single canonical `ABILITY_REGISTRY`; no dead duplicate ability data.

- [ ] **Step 1:** For each candidate-dead field, prove no readers before deleting:

```bash
grep -nE "damageScaling|\.canParry|\.canBlock|\.effects\b|calculateDamage" index.html js/sim.js
```
Only delete a field if its only references are its own definition (and a dead `calculateDamage` that nothing live calls). Keep deletions minimal and reversible.

- [ ] **Step 2:** Repoint any remaining `spells`/`SpellRegistry` duplicate stat values to read from `ABILITY_REGISTRY` (e.g. cooldown/manaCost in the loadout UI), so there is one source of truth. If `spells` carries UI-only data not in `ABILITY_REGISTRY.ui`, leave that data but remove the duplicated gameplay numbers.

- [ ] **Step 3:** In `js/sim.js`, confirm the only remaining `proj.type` checks are inside behavior dispatch fallbacks; remove leftover dead branches.

- [ ] **Step 4:** `node --check js/sim.js`. VERIFY(golden=`b1df6797`). Visual: loadout screen still shows correct names/mana/cooldowns; a single-player match plays normally (frostbolt freeze, fireball volley, thunderstorm zap).

- [ ] **Step 5:** Commit.

```bash
git add index.html js/sim.js
git commit -m "Cleanup: delete dead ability-registry fields and superseded per-ability branches; one canonical registry"
```

---

## Post-plan

After Task 7: `ABILITY_REGISTRY` is the single source of truth (stats + behavior); the PvP sim dispatches all per-ability logic through `behavior.*`; chain_lightning is gone in favor of `thunderstorm`; multiplayer can cast Thunderstorm. Single-player/doubles still branch on `proj.type` (Phase 2 unification). Update the determinism memory and `js/sim.js` header if any golden re-baseline occurred (none expected except Task 6's separate thunderstorm scenario fold).

**Phase 2 (separate spec/plan):** unify `updateGameLogic` + doubles onto the deterministic engine; convert the AI to deterministic input (fix the `Math.random` aim-error landmine at index.html ~12579); port `UpgradeRegistry` behavior to pure form behind the same interface.
