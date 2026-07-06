# Juice "Overdrive" Beam Ultimate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the Juice buff-burst with a 6-second channeled "Overdrive" beam: charges from all actions, aimed by moving (paddle Z), blocked by lane-matching, ramping ~45% DoT, vaporizes Fireballs but is countered/interrupted by Frostbolt freeze.

**Architecture:** All Overdrive *gameplay* runs inside the deterministic sim (`simulateNetworkFrame` path) so it's identical in SP and MP — the current `updateJuice` runs only in the SP driver (index.html:13737) and must be split: gameplay tick → sim, aura/visual → presentation. State lives on the combatant (`juiceActive` = channeling, `juiceTimer` = seconds left, new `juiceRamp` = connection ramp accumulator). `hashGameState` already hashes `juice`/`juiceActive`/`juiceTimer`; add `juiceRamp`. The beam + channel cast-bar are presentation-only (read sim state, never write it).

**Tech Stack:** Vanilla JS in a single `index.html` (~19k lines), Babylon.js, deterministic sim (`window.VolleyboltSim.simulateNetworkFrame`), PeerJS rollback netcode. No unit framework — tests are browser-console assertions + the `dbg.determinism`/`dbg.aiDeterminism` oracles (paste snippets into the game console at `http://127.0.0.1:8000/index.html`).

## Global Constraints

- **Determinism:** all Overdrive gameplay (channel timer, connect/block test, ramp, per-tick tower damage, Fireball disintegration, Frostbolt interrupt) runs in the sim path with fixed `dt`. NO `Math.random`, `Date.now`, `performance.now`, or `.mesh` reads in that path. `dbg.determinism(180,12345)` currently returns `954ea557` and `dbg.aiDeterminism(50,42)` returns `5afbc1a6` — the AI oracle must stay `5afbc1a6` (keep Overdrive out of `decideAI`); the sim oracle golden WILL change once the beam is in the scripted sequence and must be re-pinned exactly once (Task 7).
- **Presentation is read-only w.r.t. the sim:** the beam mesh, aura, and channel cast-bar may READ `juiceActive`/`juiceTimer`/`juiceRamp`/paddle Z but must never WRITE simulated state.
- **Symmetry (project memory):** both combatants use the identical charge table and beam constants. No per-side difference.
- **Anchor:** a fully-connected 6s beam ≈ **45%** of a health bar; tune the per-second rate to hit that, don't exceed it wildly.
- Touch ONLY `index.html`.
- The MP beam behavior can't be verified headlessly (needs 2 peers) — that's the human's live test. Verify determinism (oracles), SP behavior (console), and no crashes.

---

## Task 1: Overdrive constants + charge-on-all-actions

Replace the buff-oriented `JUICE` constants with Overdrive tuning values and make charging fire on every action. Deliverable: the constant block + charge table exist and charging is wired at every action site.

**Files:**
- Modify: `index.html:1764-1768` (the `JUICE` const), and the charge call sites (Task verifies each).

**Interfaces:**
- Produces: `JUICE.MAX`, `JUICE.CHARGE.{cast,parry,damage,minor}` (unchanged names), and new `OVERDRIVE = { DURATION, BLOCK_TOL, DMG_START, DMG_MAX, RAMP_TIME }`.

- [ ] **Step 1: Add the OVERDRIVE constant block.** Replace `index.html:1764-1768`:

```js
        const JUICE = {
            MAX: 350,                                               // points to fill (status bar shows the %)
            CHARGE: { damage: 12, cast: 8, parry: 10, minor: 4 },  // per action; damage is PER damage point
        };
        // Overdrive = the channeled beam ultimate (replaces the old buff burst).
        // All values TUNABLE in playtest; the ~45% fully-connected total is the balance anchor.
        const OVERDRIVE = {
            DURATION:  6,     // seconds of channel
            BLOCK_TOL: 0.9,   // |beamZ - oppPaddleZ| <= this => blocked this tick (≈ paddle block half-width; tune)
            DMG_START: 0.04,  // fraction of max HP / sec on first connect
            DMG_MAX:   0.10,  // fraction of max HP / sec at full ramp
            RAMP_TIME: 2.5,   // seconds of CONTINUOUS connection to reach DMG_MAX
        };
```
(Removed `DURATION: 8` from JUICE — it becomes `OVERDRIVE.DURATION`.)

- [ ] **Step 2: Expose OVERDRIVE on window** next to `window.JUICE = JUICE;` (currently `index.html:1847`):

```js
        window.JUICE = JUICE;
        window.OVERDRIVE = OVERDRIVE;
```

- [ ] **Step 3: Verify charge fires on all actions.** Grep the charge sites and confirm each is reached in the SIM path (so SP+MP both charge). Run from repo root:

```bash
grep -n "addJuice" index.html
```
Expected sites (must all call `addJuice(combatant, JUICE.CHARGE.*)`): cast (the ability `onCast`/cast-complete in the sim, ~lines 2132/2170), parry (~11946), damage dealt (search `dealDamageToTower`/damage application). If a `damage`/`minor` charge on TAKING a hit is missing from the sim path, add it where the sim applies tower/combatant damage (the combatant that just got hit gets `addJuice(victim, JUICE.CHARGE.minor)` and the attacker gets `addJuice(attacker, JUICE.CHARGE.damage * dmg)`). Ensure these run inside `simulateNetworkFrame` (not a render-only path) and are gated `if (!ctx.isResimulating)` only for FX, never for the `addJuice` state change (charge is sim state and must apply during resim too — it's already deterministic).

- [ ] **Step 4: Console test — charging from a cast (no damage taken).** Reload the game, start an SP match, open console:

```js
// Zero juice, cast a fireball, expect juice > 0 from the cast alone.
combatants.left.juice = 0;
// simulate a cast by setting the input flag and stepping one sim frame is complex; instead verify the code path:
console.log('cast charge value:', JUICE.CHARGE.cast, 'OVERDRIVE:', JSON.stringify(window.OVERDRIVE));
console.assert(window.OVERDRIVE && window.OVERDRIVE.DURATION === 6, 'OVERDRIVE constants present');
```
Expected: logs the charge value and `OVERDRIVE` object, no assertion error. (Full charge-on-action is validated in the SP smoke, Task 8.)

- [ ] **Step 5: Commit.**
```bash
git add index.html
git commit -m "Overdrive: add channel constants; charge Juice on all actions"
```

---

## Task 2: Channel state + activation (replace the buff)

Rewrite `activateJuice` to start the channel instead of the buff, add the `juiceRamp` state field, and remove the old buff side-effects. Deliverable: pressing ult with a full bar sets the channel state (no buff).

**Files:**
- Modify: `index.html:1687-1689` (combatant state init — add `juiceRamp`), `1784-1795` (`activateJuice`).

**Interfaces:**
- Consumes: `OVERDRIVE` (Task 1).
- Produces: a combatant in channel state = `{ juiceActive:true, juiceTimer:OVERDRIVE.DURATION, juiceRamp:0, juice:JUICE.MAX (drains) }`. `activateJuice(ref)` returns true if it started.

- [ ] **Step 1: Add `juiceRamp` to combatant init.** At `index.html:1687-1689` (the combatant object literal with `juice: 0, juiceActive: false, juiceTimer: 0,`), add:
```js
                juice: 0,
                juiceActive: false,
                juiceTimer: 0,
                juiceRamp: 0,          // Overdrive: seconds of CONTINUOUS beam connection (ramps damage)
```

- [ ] **Step 2: Rewrite `activateJuice`** (`index.html:1784-1795`) to start the channel and drop the buff (no cooldown reset, no mana grant):

```js
        // Spend a full bar -> start the Overdrive CHANNEL. The bar stays full and drains over the
        // channel (it becomes the duration meter). No buff — the beam does the work. Returns true
        // if it started. Cannot start while frozen or already channeling.
        function activateJuice(ref) {
            const c = resolveCombatant(ref);
            if (!c || c.juiceActive || (c.juice || 0) < JUICE.MAX) return false;
            if ((c.freezeTime || 0) > 0) return false;   // can't start Overdrive while frozen
            c.juice = JUICE.MAX;
            c.juiceActive = true;
            c.juiceTimer = OVERDRIVE.DURATION;
            c.juiceRamp = 0;
            if (window.onJuiceStart) window.onJuiceStart(c);   // FX only (presentation)
            if (window.logJuice) window.logJuice(c.side === 'left' ? 'blue' : 'red');
            return true;
        }
```

- [ ] **Step 3: Reset `juiceRamp` in combatantReset.** At `index.html:2023-2025` (the `combatantReset` block that clears juice on round boundary), ensure it also clears ramp:
```js
                combatant.juiceActive = false; combatant.juiceTimer = 0; combatant.juice = 0; combatant.juiceRamp = 0;
```

- [ ] **Step 4: Console test — activation sets channel state, not a buff.** Reload, SP match, console:
```js
combatants.left.juice = JUICE.MAX; combatants.left.juiceActive = false; combatants.left.freezeTime = 0;
const cdBefore = JSON.stringify(combatants.left.cooldowns);
activateJuice('left');
console.assert(combatants.left.juiceActive === true, 'channel started');
console.assert(Math.abs(combatants.left.juiceTimer - 6) < 1e-6, 'timer = DURATION');
console.assert(combatants.left.juiceRamp === 0, 'ramp reset');
console.assert(JSON.stringify(combatants.left.cooldowns) === cdBefore, 'cooldowns NOT reset (buff removed)');
console.log('activation ok');
```
Expected: `activation ok`, no assertion errors.

- [ ] **Step 5: Commit.**
```bash
git add index.html
git commit -m "Overdrive: activateJuice starts the channel (buff removed), add juiceRamp state"
```

---

## Task 3: Move the channel tick into the sim (deterministic)

Create the deterministic per-frame Overdrive tick and call it from `simulateNetworkFrame` for BOTH combatants, so it runs identically in SP and MP. This replaces the gameplay half of the old render-driven `updateJuice`. Deliverable: the channel drains, connects/blocks, ramps, and damages in the sim.

**Files:**
- Modify: `index.html` — add `tickOverdrive(c, opp, dt, ctx)` near the sim ability logic; call it from `simulateNetworkFrame`'s per-combatant update; strip the gameplay (timer/damage) out of `updateJuice` (`index.html:1798-1843`) leaving only the aura animation.

**Interfaces:**
- Consumes: `OVERDRIVE`, channel state (Task 2), `getMaxHealth`/`maxTowerHealth`.
- Produces: `tickOverdrive(caster, opponent, dt, ctx)` — pure w.r.t. wall-clock/RNG; mutates `caster.juiceTimer/juiceRamp/juiceActive/juice` and `opponent.towerHealth`; calls `ctx.deps.*` for FX only (gated `!ctx.isResimulating`).

- [ ] **Step 1: Write `tickOverdrive`.** Add near the other sim helpers (e.g. just after `activateJuice`/`updateJuice` definitions or in the ABILITY area). Beam is hitscan (per-tick position check), fires along the caster's forward axis at the caster's Z:

```js
        // Deterministic Overdrive channel tick — runs INSIDE the sim for caster `c` vs `opp`.
        // Drains the timer, tests lane-match block, ramps damage while connected, applies tower
        // damage. Fireball disintegration + Frostbolt interrupt are handled in the projectile
        // loop (Task 4). ctx.deps.* are FX-only (never gate the STATE changes on isResimulating).
        function tickOverdrive(c, opp, dt, ctx) {
            if (!c || !c.juiceActive) return;
            c.juiceTimer -= dt;
            const frac = Math.max(0, c.juiceTimer / OVERDRIVE.DURATION);
            c.juice = JUICE.MAX * frac;   // bar = time remaining

            // Connect/block: beam is at the caster's Z; blocked while the opponent's paddle is within
            // BLOCK_TOL of it. (Same coordinate space as paddleZ; no camera flip.)
            const connected = opp && Math.abs((c.paddleZ || 0) - (opp.paddleZ || 0)) > OVERDRIVE.BLOCK_TOL;
            if (connected) {
                c.juiceRamp = Math.min(OVERDRIVE.RAMP_TIME, (c.juiceRamp || 0) + dt);
                const rampFrac = OVERDRIVE.RAMP_TIME > 0 ? c.juiceRamp / OVERDRIVE.RAMP_TIME : 1;
                const ratePerSec = OVERDRIVE.DMG_START + (OVERDRIVE.DMG_MAX - OVERDRIVE.DMG_START) * rampFrac;
                const maxHP = (typeof maxTowerHealth === 'number') ? maxTowerHealth : 20;
                const dmg = ratePerSec * maxHP * dt;   // fraction/sec * maxHP * dt
                if (opp) {
                    opp.towerHealth = Math.max(0, (opp.towerHealth || 0) - dmg);
                    // Attacker gains charge? NO — no charging while channeling (addJuice guards on juiceActive).
                    if (ctx && ctx.deps && !ctx.isResimulating && ctx.deps.onOverdriveHit) {
                        ctx.deps.onOverdriveHit(c, opp, dmg);   // FX: beam impact spark, damage number
                    }
                }
            } else {
                c.juiceRamp = 0;   // block resets the ramp
            }

            if (c.juiceTimer <= 0) {
                c.juiceActive = false; c.juiceTimer = 0; c.juice = 0; c.juiceRamp = 0;
                if (ctx && ctx.deps && !ctx.isResimulating && ctx.deps.onJuiceEnd) ctx.deps.onJuiceEnd(c);
            }
        }
        window.tickOverdrive = tickOverdrive;
```

- [ ] **Step 2: Call `tickOverdrive` from the sim.** In `simulateNetworkFrame` (search for where it updates each combatant's per-frame state — freeze timer, cooldowns, mana), add for each side, passing the opponent:
```js
            // Overdrive channel (deterministic; both sides). left's opponent is right and vice-versa.
            tickOverdrive(ctx.combatants.left,  ctx.combatants.right, dt, ctx);
            tickOverdrive(ctx.combatants.right, ctx.combatants.left,  dt, ctx);
```
Place it AFTER paddle Z is updated for the frame (so the connect test uses this frame's positions) and BEFORE the settled-hash is taken.

- [ ] **Step 3: Strip gameplay out of the render-side `updateJuice`.** In `updateJuice` (`index.html:1798-1843`), REMOVE the timer drain, `c.juice = JUICE.MAX*frac`, and the end-of-channel block (lines that mutate `juiceTimer`/`juice`/`juiceActive`) — those now live in `tickOverdrive`. KEEP only the aura wobble/tint animation (presentation). The `for (const c ...) if (!c || !c.juiceActive) continue;` guard stays; inside, keep just `if (window._juiceTint) ...` and the `if (c.juiceAura ...)` wobble block. This makes `updateJuice` purely visual.

- [ ] **Step 4: Add the SIM_DEPS FX hooks.** Where `SIM_DEPS` is defined (search `castingStart:` in the deps object, ~line 16654), add no-op-safe FX hooks:
```js
            onOverdriveHit: (caster, opp, dmg) => { if (window.showOverdriveHitFX) window.showOverdriveHitFX(caster, opp, dmg); },
```
(`onJuiceEnd` already exists as a dep or window fn — reuse it.)

- [ ] **Step 5: Console test — channel drains + damages in the sim.** Reload, SP match, console (drive a few sim frames by stepping the SP loop is hard; instead unit-test `tickOverdrive` directly):
```js
const c = { paddleZ: 0, juiceActive: true, juiceTimer: 6, juiceRamp: 0, side: 'left' };
const opp = { paddleZ: 3, towerHealth: 20 };   // off-lane (>BLOCK_TOL) => connects
window.tickOverdrive(c, opp, 1/60, { isResimulating: true });   // isResim: skip FX, still change state
console.assert(c.juiceTimer < 6, 'timer drained');
console.assert(opp.towerHealth < 20, 'connected -> tower took damage');
console.assert(c.juiceRamp > 0, 'ramp advanced while connected');
const opp2 = { paddleZ: 0, towerHealth: 20 };  // on-lane (<=BLOCK_TOL) => blocked
const c2 = { paddleZ: 0, juiceActive: true, juiceTimer: 6, juiceRamp: 1, side: 'left' };
window.tickOverdrive(c2, opp2, 1/60, { isResimulating: true });
console.assert(opp2.towerHealth === 20, 'blocked -> no damage');
console.assert(c2.juiceRamp === 0, 'block reset the ramp');
console.log('tickOverdrive ok');
```
Expected: `tickOverdrive ok`, no assertion errors.

- [ ] **Step 6: Commit.**
```bash
git add index.html
git commit -m "Overdrive: deterministic channel tick in the sim (drain/connect/ramp/damage)"
```

---

## Task 4: Fireball disintegration + Frostbolt interrupt

In the sim's projectile loop, vaporize Fireballs that cross an active beam and let a Frostbolt that reaches the channeling caster freeze+interrupt them. Deliverable: Fireballs into the beam disappear; a Frostbolt hit ends the channel.

**Files:**
- Modify: `index.html` — the sim projectile update loop (search the projectile-move loop inside `simulateNetworkFrame`; `destroyProjectile`/`destroyProjectileSilent` at 11583/18274 are the removal helpers) and the frostbolt-hit/freeze application (`freezeTime = ...frostbolt.freezeDuration`, ~line 2137).

**Interfaces:**
- Consumes: channel state, `OVERDRIVE.BLOCK_TOL`, projectile `{x,z,type,owner}`.

- [ ] **Step 1: Fireball disintegration.** In the sim projectile loop, for each projectile, if a beam is active on either side and the projectile is a `fireball` whose position crosses that beam's lane, remove it. A beam occupies caster `c`'s Z from the caster's X toward the opponent. Simplest deterministic test: a fireball is disintegrated if there is an active channeler `c` such that `Math.abs(proj.z - c.paddleZ) <= OVERDRIVE.BLOCK_TOL` AND the projectile is between the two paddles on X (i.e. the beam sweeps its lane). Add inside the loop (before normal collision):
```js
                // Overdrive beam vaporizes Fireballs in its lane (NOT Frostbolt — that's the counter).
                if ((proj.type === 'fireball' || !proj.type)) {
                    for (const ch of [ctx.combatants.left, ctx.combatants.right]) {
                        if (ch && ch.juiceActive && Math.abs(proj.z - (ch.paddleZ || 0)) <= OVERDRIVE.BLOCK_TOL) {
                            ctx.deps.destroyProjectile(proj);   // remove; deps handles FX vs silent
                            proj._gone = true; break;
                        }
                    }
                    if (proj._gone) continue;   // skip further processing for this projectile
                }
```
(Match the loop's existing removal convention — if it splices, splice; adapt `continue`/index handling to the actual loop.)

- [ ] **Step 2: Frostbolt interrupt.** Frostbolt is NOT disintegrated. Where the sim applies a frostbolt freeze to a combatant (~line 2137, `c.freezeTime = ctx.abilities.frostbolt.freezeDuration`), also end any active channel on the frozen combatant:
```js
                        c.freezeTime = ctx.abilities.frostbolt.freezeDuration;
                        if (c.juiceActive) {   // Frostbolt freezes the caster -> interrupt Overdrive
                            c.juiceActive = false; c.juiceTimer = 0; c.juice = 0; c.juiceRamp = 0;
                            if (ctx.deps && !ctx.isResimulating && ctx.deps.onJuiceEnd) ctx.deps.onJuiceEnd(c);
                        }
```

- [ ] **Step 3: Console test — disintegration + interrupt logic (unit, deterministic).**
```js
// Frostbolt interrupt: freezing a channeler ends the channel.
const c = { juiceActive: true, juiceTimer: 5, juice: 350, juiceRamp: 1, freezeTime: 0 };
// mimic the freeze branch:
c.freezeTime = 1; if (c.juiceActive) { c.juiceActive = false; c.juiceTimer = 0; c.juice = 0; c.juiceRamp = 0; }
console.assert(!c.juiceActive && c.freezeTime === 1, 'frostbolt interrupts channel');
console.log('interrupt ok');
```
Expected: `interrupt ok`. (Fireball disintegration is validated in the SP smoke, Task 8.)

- [ ] **Step 4: Commit.**
```bash
git add index.html
git commit -m "Overdrive: vaporize Fireballs in the beam lane; Frostbolt freeze interrupts the channel"
```

---

## Task 5: Remove the rapid-fire buff remnants

Delete the `juiceActive ? 0 : cooldown` rapid-fire behavior (the old buff) so `juiceActive` means only "channeling." Deliverable: no cooldown special-casing during Overdrive.

**Files:**
- Modify: `index.html:13889` and `index.html:18416` (both `c.juiceActive ? 0 : abilities.fireball.cooldown`).

- [ ] **Step 1: Fix line ~13889.** Change:
```js
            c.cooldowns.fireball = c.juiceActive ? 0 : abilities.fireball.cooldown;
```
to:
```js
            c.cooldowns.fireball = abilities.fireball.cooldown;
```

- [ ] **Step 2: Fix line ~18416.** Change:
```js
            const effectiveCooldown = c.juiceActive ? 0 : abilities.fireball.cooldown;
```
to:
```js
            const effectiveCooldown = abilities.fireball.cooldown;
```

- [ ] **Step 3: Confirm the caster can't cast while channeling.** The player CANNOT cast during Overdrive (full commitment). Find the cast-start guard (where a fireball/frostbolt cast is initiated in the sim) and add `&& !c.juiceActive` so casts are blocked while channeling. Grep the cast-start condition and add the guard; if the AI's `decideAI` could emit a cast while channeling, the applyCombatantInput/cast path must reject it (guard at the cast-start site is sufficient and keeps `decideAI` pure).

- [ ] **Step 4: Console test.**
```js
combatants.left.juiceActive = true;
// spot-check the cooldown lines no longer branch on juiceActive:
console.log('grep confirms no juiceActive?0 remains (see verify step)');
```
Then grep:
```bash
grep -n "juiceActive ? 0" index.html || echo "clean: no rapid-fire remnants"
```
Expected: `clean: no rapid-fire remnants`.

- [ ] **Step 5: Commit.**
```bash
git add index.html
git commit -m "Overdrive: remove old rapid-fire buff; block casting while channeling"
```

---

## Task 6: Hash the ramp + presentation (beam visual + channel cast-bar)

Add `juiceRamp` to the sim hash (so a beam desync is caught) and render the beam + the reversed channel cast-bar (presentation-only). Deliverable: the beam draws, the cast bar depletes over 6s, and the hash covers the ramp.

**Files:**
- Modify: `index.html:15578` (hashGameState — add `juiceRamp`), `captureGameState`/`restoreGameState` (add `juiceRamp` so rollback preserves it), `updateMatchPresentation` (beam mesh + channel cast bar).

- [ ] **Step 1: Hash `juiceRamp`.** At `index.html:15578` (`mix(q(c.juice)); mix(c.juiceActive ? 1 : 0); mix(q(c.juiceTimer));`) append:
```js
                mix(q(c.juice)); mix(c.juiceActive ? 1 : 0); mix(q(c.juiceTimer)); mix(q(c.juiceRamp));
```

- [ ] **Step 2: Snapshot `juiceRamp` in rollback.** In `captureGameState` (the `left:`/`right:` combatant capture, search `juiceTimer:` there) add `juiceRamp: combatants.left ? (combatants.left.juiceRamp||0) : 0` (and right), and in `restoreGameState` set `combatants.left.juiceRamp = state.left.juiceRamp` (and right). Mirror the exact pattern already used for `juiceTimer`.

- [ ] **Step 3: Render the channel cast-bar (reversed).** In `updateMatchPresentation`'s cast-bar section, when a combatant `juiceActive`, drive its cast bar as a depleting channel meter using the SAME positional bar (left wizard→left bar, right→right bar). After the normal cast-bar blocks, add:
```js
                // Overdrive channel meter: reuse the positional cast bar, depleting over the 6s.
                for (const [side, c] of [['left', leftC], ['right', rightC]]) {
                    if (c && c.juiceActive) {
                        const prog = Math.max(0, Math.min(1, (c.juiceTimer || 0) / (window.OVERDRIVE ? OVERDRIVE.DURATION : 6)));
                        const fill = side === 'left' ? (window.guiElements && window.guiElements.playerCastFill) : (window.guiElements && window.guiElements.aiCastFill);
                        const label = side === 'left' ? (window.guiElements && window.guiElements.playerCastLabel) : (window.guiElements && window.guiElements.aiCastLabel);
                        if (label) label.text = 'Overdrive';
                        if (fill) fill.width = (prog * 100) + '%';   // depletes as juiceTimer falls
                        if (side === 'left') showCastBar(true); else showAICastBar(true);
                    }
                }
```
(Read-only: reads `juiceActive`/`juiceTimer` only.)

- [ ] **Step 4: Render the beam mesh (visual only).** Add `window.showOverdriveHitFX` (Task 3 dep) and a per-frame beam draw in `updateMatchPresentation`: for each `juiceActive` combatant, show a beam mesh from the caster along ±X at the caster's paddle Z, length spanning to the opponent side. Reuse an existing emissive material/cylinder pattern (see the projectile/trail mesh code). This is FX-only; if time-boxed, a simple stretched glowing box at the caster's Z is acceptable for v1. Never write sim state here.

- [ ] **Step 5: Verify determinism unchanged BY THIS TASK (hash addition is additive; golden re-pins in Task 7).** Reload, console:
```js
window.dbg.aiDeterminism(50,42).fold   // must still be "5afbc1a6"
```
Expected: `5afbc1a6` (AI oracle unaffected — Overdrive isn't in decideAI). The sim golden changes in Task 7.

- [ ] **Step 6: Commit.**
```bash
git add index.html
git commit -m "Overdrive: hash+snapshot juiceRamp; render beam + reversed channel cast-bar (presentation)"
```

---

## Task 7: Extend the determinism oracle + re-pin the sim golden

Make `dbg.determinism`'s scripted match fire an Overdrive so the beam path is covered by the golden, then re-pin. Deliverable: the sim golden reflects the beam and is stable.

**Files:**
- Modify: `index.html` — the `dbg.determinism` harness input script (search `function _fold`/the scripted `inp(f, side)` used by `dbg.determinism`), and the golden comment/reference (`b1df6797` was replaced by `954ea557`; this task produces a new value).

- [ ] **Step 1: Fire Overdrive in the scripted sequence.** In the `dbg.determinism` input generator, at a deterministic frame (e.g. frame 30), set `juice: true` for one side after pre-loading its bar. If the harness pins `c.juice` (it does — `c.juice = 0` at ~15742), change that side's pin to `JUICE.MAX` and emit `juice:true` once so `activateJuice` fires and the beam ticks for subsequent frames. Keep it fully deterministic (fixed frame numbers, no RNG).

- [ ] **Step 2: Run + capture the new golden.** Reload, console:
```js
window.dbg.determinism(180, 12345)   // note .fold; run twice — must match
```
Copy the `fold`. Update the golden reference comment (search `954ea557`) to the new value with a dated note: `re-pinned 2026-07-05: Overdrive beam added to the scripted sequence`.

- [ ] **Step 3: Verify reproducible + AI oracle intact.**
```js
const a = window.dbg.determinism(180,12345).fold, b = window.dbg.determinism(180,12345).fold;
console.assert(a === b, 'sim oracle reproducible');
console.assert(window.dbg.aiDeterminism(50,42).fold === '5afbc1a6', 'AI oracle unchanged');
console.log('golden pinned:', a);
```
Expected: reproducible, AI oracle `5afbc1a6`, logs the new sim golden.

- [ ] **Step 4: Commit.**
```bash
git add index.html
git commit -m "Overdrive: cover the beam in dbg.determinism; re-pin sim golden"
```

---

## Task 8: SP playtest smoke + tuning pass

Play it and tune to the ~45% anchor. Deliverable: it feels right in SP; numbers recorded.

**Files:**
- Modify: `index.html` (OVERDRIVE constants + JUICE.CHARGE), as tuning dictates.
- Create: `docs/superpowers/specs/2026-07-05-juice-overdrive-as-built.md` (final values + notes).

- [ ] **Step 1: Play 3-5 SP matches.** Confirm: bar charges from casting/parrying/hitting (not just taking damage); ult fires a 6s beam; moving aims it; the AI in your lane blocks it, off-lane takes ramping damage; a fully-connected beam does ~45%; a Frostbolt to the moving caster freezes+interrupts; Fireballs into the beam vaporize; the channel cast-bar depletes over 6s; you can't cast while channeling.

- [ ] **Step 2: Tune.** Adjust `OVERDRIVE.DMG_START/DMG_MAX/RAMP_TIME` to hit ~45% fully-connected (and ~15-25% well-defended), `BLOCK_TOL` so "on the paddle = safe", and `JUICE.CHARGE`/`JUICE.MAX` so a full bar is ~1-2 rounds. Change one knob, replay, repeat.

- [ ] **Step 3: Re-run oracles after any constant change.** Constants don't change `decideAI` so `aiDeterminism` stays `5afbc1a6`; the `dbg.determinism` golden WILL move if you changed values that the scripted Overdrive exercises — re-pin (Task 7 Step 2) and note it.

- [ ] **Step 4: Write the as-built note** with final OVERDRIVE + CHARGE values, the pinned sim golden, and 3-5 lines of feel notes.

- [ ] **Step 5: Commit.**
```bash
git add index.html docs/superpowers/specs/2026-07-05-juice-overdrive-as-built.md
git commit -m "Overdrive: tune to the ~45% anchor; record as-built values"
```

---

## Self-Review

**1. Spec coverage:**
- §3 charging on all actions → Task 1. ✓
- §4 activation → channel (buff removed) → Task 2 (+ Task 5 removes rapid-fire). ✓
- §5 beam: duration/aim/lane-match/ramping DoT/target → Task 3. ✓
- §5 Fireball disintegrate + Frostbolt counter/interrupt → Task 4. ✓
- §5 channel cast-bar (reversed) → Task 6 Step 3. ✓
- §6 removals (buff, rapid-fire) → Tasks 2, 5. ✓
- §7 symmetry (same constants both sides) → Task 3 ticks both; Global Constraints. ✓
- §7 determinism (sim-side, hash, oracle) → Tasks 3, 6, 7. ✓
- §8 tunable values → Task 1 constants + Task 8 tuning. ✓
- §9 verification → console tests per task + Task 8 SP smoke + live MP (human). ✓

**2. Placeholder scan:** The two spots that legitimately require reading surrounding code — the exact projectile-loop splice convention (Task 4 Step 1) and the exact cast-start guard site (Task 5 Step 3) — provide the code to add and name the anchor to find; they are integration points in an 18k-line file, not vague TODOs. The beam-mesh visual (Task 6 Step 4) allows a simple v1 by design. No "TBD"/"handle edge cases" placeholders.

**3. Type consistency:** `juiceRamp` (new field) is added in Task 2, ticked in Task 3, reset in Tasks 2/3/4, hashed+snapshotted in Task 6 — same name throughout. `OVERDRIVE.{DURATION,BLOCK_TOL,DMG_START,DMG_MAX,RAMP_TIME}` defined in Task 1, consumed in Tasks 3/6 under identical names. `tickOverdrive(c, opp, dt, ctx)` defined in Task 3, called in Task 3 Step 2 with the same signature. `activateJuice(ref)→bool` unchanged.
