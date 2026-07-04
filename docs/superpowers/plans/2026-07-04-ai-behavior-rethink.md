# Singles AI Behavior Rethink Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the perfect-prediction-plus-noise singles AI with a track-&-chase AI whose difficulty is one honest competence scalar (`skill ∈ [0,1]`), so an average player gets a fair, winnable fight and the difficulty knobs stop fighting each other.

**Architecture:** `getAISkill()` returns a scalar (constant "average" today, a dynamic seam for later). A pure `skillToProfile(skill)` maps it to concrete behavior values. A rewritten, still-pure `decideAI(view, frame, rng, profile)` implements track-&-chase movement, sight-based frostbolt dodging, cadence-gated offense, a skill-gated thunderstorm, and sight-gated parry. `runSinglePlayerFrame` owns a per-projectile "sight" counter so `decideAI` stays pure. Everything routes through the existing unified `simulateNetworkFrame`, so the AI stays a symmetric player.

**Tech Stack:** Vanilla JS in a single `index.html` (~18.7k lines), Babylon.js for rendering, a deterministic sim (`window.VolleyboltSim.simulateNetworkFrame`). No unit-test framework — the test harness is (a) browser-console assertions, (b) the `dbg.aiDeterminism` / `dbg.determinism` oracles, and (c) a `grep` purity check. "Run the test" means paste the snippet into the game's dev console (game served at `http://127.0.0.1:8000/index.html`).

## Global Constraints

- **Symmetry invariant (project memory):** `skillToProfile` may return ONLY competence values (perception lag, tracking tightness, sight windows, decision cadence). It must NEVER return a multiplier on speed, mana, cooldown, cast time, or damage. The AI's paddle speed, mana, and cooldowns are identical to the player's at every `skill`.
- **`decideAI` purity:** no `performance.now`, `Date.now`, `Math.random`, or `.mesh` anywhere in `decideAI`, `skillToProfile`, or any pure AI helper. Variety comes only from the integer-seeded `rng` (unused this pass) and plain-data view fields.
- **Do not touch:** the doubles AI, `simulateNetworkFrame`, `js/sim.js` semantics, or the MP input path (`captureLocalInput`). This is singles-only.
- **Sim oracle must not move:** `dbg.determinism(180, 12345)` must return `954ea557` before and after every task.
- **`AI_SKILL_AVERAGE` seeds at `0.45`** (deliberately eased; "too good" was the complaint). Tuned from playtests in Task 3.
- All AI code lives in the game-setup closure around `index.html:12320–12590`; the `dbg.aiDeterminism` oracle lives in the outer scope around `index.html:15541–15588`.

---

## Task 1: Competence seam — `getAISkill()`, `skillToProfile()`, `lerp`

Adds the difficulty seam and tuning curve as pure, window-exposed functions. Purely additive — `decideAI` is NOT rewired yet, so the game behaves exactly as before and stays runnable. Deliverable: the seam exists and passes shape/symmetry/monotonicity assertions.

**Files:**
- Modify: `index.html` — insert immediately ABOVE the `const DEFAULT_AI_PARAMS = {` block (currently `index.html:12322`). Leave `DEFAULT_AI_PARAMS` in place for now (removed in Task 2).

**Interfaces:**
- Produces:
  - `getAISkill() → number` in `[0,1]` (today: constant `AI_SKILL_AVERAGE = 0.45`).
  - `skillToProfile(skill) → { reactionFrames:int, trackDeadzone:number, dodgeSightFrames:int, parrySight:int, castCadence:int, thunderstormSkill:number }` (pure).
  - `window.getAISkill`, `window.skillToProfile` (for console tests + the oracle in Task 2).

- [ ] **Step 1: Write the failing test**

Paste into the game console (with the game loaded):

```js
// TEST 1a: profile shape + symmetry (no forbidden keys) + range clamp
(() => {
  const FORBIDDEN = ['speed','mana','cooldown','castTime','damage','manaRegen'];
  const p = window.skillToProfile(0.5);
  const keys = Object.keys(p);
  const expected = ['reactionFrames','trackDeadzone','dodgeSightFrames','parrySight','castCadence','thunderstormSkill'];
  console.assert(expected.every(k => k in p), '1a: missing profile keys', keys);
  console.assert(!keys.some(k => FORBIDDEN.some(f => k.toLowerCase().includes(f))), '1a: FORBIDDEN stat-crutch key present', keys);
  // clamp
  console.assert(JSON.stringify(window.skillToProfile(-1)) === JSON.stringify(window.skillToProfile(0)), '1a: skill<0 must clamp to 0');
  console.assert(JSON.stringify(window.skillToProfile(2))  === JSON.stringify(window.skillToProfile(1)), '1a: skill>1 must clamp to 1');
  console.log('TEST 1a done (check for assertion errors above)');
})();

// TEST 1b: monotonicity — higher skill = sharper perception (smaller lag/windows, tighter deadzone)
(() => {
  const lo = window.skillToProfile(0), hi = window.skillToProfile(1);
  console.assert(hi.reactionFrames   < lo.reactionFrames,   '1b: reactionFrames must fall with skill');
  console.assert(hi.trackDeadzone    < lo.trackDeadzone,    '1b: trackDeadzone must fall with skill');
  console.assert(hi.dodgeSightFrames < lo.dodgeSightFrames, '1b: dodgeSightFrames must fall with skill');
  console.assert(hi.parrySight       < lo.parrySight,       '1b: parrySight must fall with skill');
  console.assert(hi.castCadence      < lo.castCadence,      '1b: castCadence must fall with skill');
  console.assert(hi.thunderstormSkill > lo.thunderstormSkill, '1b: thunderstormSkill must rise with skill');
  console.log('TEST 1b done');
})();

// TEST 1c: seam default
console.assert(window.getAISkill() === 0.45, '1c: getAISkill default must be 0.45');
```

- [ ] **Step 2: Run test to verify it fails**

Reload `http://127.0.0.1:8000/index.html`, open the console, paste the Step 1 snippet.
Expected: `Uncaught TypeError: window.skillToProfile is not a function` (functions don't exist yet).

- [ ] **Step 3: Write minimal implementation**

Insert immediately above `const DEFAULT_AI_PARAMS = {` at `index.html:12322`:

```js
            // ── AI COMPETENCE SEAM ─────────────────────────────────────────────
            // getAISkill() is the ONLY difficulty input. Returns skill ∈ [0,1].
            // Today: constant AI_SKILL_AVERAGE. Authored as a seam so difficulty can
            // later be driven dynamically WITHOUT a rewrite, e.g. a clutch ramp:
            //   skill = clamp(AI_SKILL_AVERAGE + clutchBonus(scoreDeficit), 0, 1)
            // INVARIANT: dynamic competence may only raise this SCALAR. It must never
            // grant speed / mana / cooldown / cast-time / damage — see the symmetry
            // banner on skillToProfile. (Project symmetry-principle memory.)
            const AI_SKILL_AVERAGE = 0.45;
            function getAISkill() { return AI_SKILL_AVERAGE; }

            function _aiLerp(a, b, t) { return a + (b - a) * t; }

            // ┌────────────────────────────────────────────────────────────────┐
            // │ SYMMETRY BANNER — skillToProfile may return ONLY competence      │
            // │ values: perception lag, tracking tightness, sight windows,       │
            // │ decision cadence. NEVER speed / mana / cooldown / cast-time /    │
            // │ damage. Difficulty = how WELL the AI plays, never how STRONG.   │
            // └────────────────────────────────────────────────────────────────┘
            // Pure: skill → concrete behavior values consumed by decideAI. This is
            // the single tuning curve (endpoints are starting guesses; the shape —
            // monotonic, easiest at skill=0 — is the contract). skill=0 easiest,
            // skill=1 hardest.
            function skillToProfile(skill) {
                const s = Math.max(0, Math.min(1, skill));
                return {
                    reactionFrames:    Math.round(_aiLerp(12, 2, s)),  // acts on an older world at low skill
                    trackDeadzone:     _aiLerp(1.1, 0.34, s),          // tracks loosely at low skill
                    dodgeSightFrames:  Math.round(_aiLerp(18, 3, s)),  // frames a frostbolt must be seen before dodging
                    parrySight:        Math.round(_aiLerp(14, 2, s)),  // frames a threat must be seen before parrying
                    castCadence:       Math.round(_aiLerp(10, 2, s)),  // offensive cast phase-gate period (in think-cycles)
                    thunderstormSkill: s,                              // gate value: uses thunderstorm well only at high s
                };
            }
```

Then, next to the other `window.*` AI exports (currently `index.html:12496–12499`, after `window.decideAI = decideAI;`), add:

```js
            window.getAISkill = getAISkill;
            window.skillToProfile = skillToProfile;
```

- [ ] **Step 4: Run test to verify it passes**

Reload the page, re-paste the Step 1 snippet.
Expected: three `TEST 1x done` logs, **no** assertion errors.

- [ ] **Step 5: Verify the game still runs and the sim oracle is unmoved**

In console:
```js
window.dbg.determinism(180, 12345).fold   // expected: "954ea557"
```
Start a singles match — it must play exactly as before (this task changed nothing wired).

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "Add AI competence seam: getAISkill + skillToProfile"
```

---

## Task 2: Rewrite `decideAI` to track-&-chase, wire the profile, remove the old knobs

The core change. Rewrites `decideAI` for track-&-chase movement, sight-based dodge, cadence offense, skill-gated thunderstorm, and sight-gated parry. Adds the driver-owned sight counter in `runSinglePlayerFrame`, stamps `sightFrames` onto the view in `buildAISingleView`, deletes `DEFAULT_AI_PARAMS` and `_reflectZ`, and re-points the `dbg.aiDeterminism` oracle at `skillToProfile(0.45)` (re-pinning its golden hash). Deliverable: a deterministic, reproducible, symmetric track-&-chase AI.

**Files:**
- Modify: `index.html`
  - `decideAI` body — currently `index.html:12383–12492`.
  - `_reflectZ` helper — delete, currently `index.html:12373–12381`.
  - `DEFAULT_AI_PARAMS` — delete, currently `index.html:12322–12340` (and its `window.DEFAULT_AI_PARAMS` export at `12498`).
  - `buildAISingleView` projectile snapshot — currently `index.html:12505–12514` (add `sightFrames`).
  - `runSinglePlayerFrame` — currently `index.html:12570–12589` (add sight-counter update; drive lag from profile; pass profile).
  - `dbg.aiDeterminism` oracle — currently `index.html:15546–15588` (synthetic view gets `sightFrames`; pass `skillToProfile(0.45)`; re-pin golden comment at `15544`).

**Interfaces:**
- Consumes (from Task 1): `getAISkill()`, `skillToProfile(skill)`, `_aiLerp`.
- Consumes (existing, unchanged): `_aiIncomingProjectiles(view)`, `_aiFindOpenTarget(view)`, `_aiIsOppBlocking(view)`, `_aiSafeToStartCast(view)`, `makeAIRng`, `AI_RNG_SEED`, `JUICE.MAX`, `combatants`, `projectiles`, `spFrameCounter`, `aiViewHistory`.
- Produces: `decideAI(view, frame, rng, profile) → { moveDir:-1|0|1, parry:bool, fireball:bool, frostbolt:bool, thunderstorm:bool, juice:bool }`. `view.projectiles[i]` now carries `sightFrames:int` (frames the projectile has been continuously incoming, from the AI's lagged view).

- [ ] **Step 1: Write the failing test**

Paste into console (after Task 1 is present):

```js
// TEST 2a: decideAI reproducibility under a profile
(() => {
  const v = window.buildAISingleView ? null : null; // buildAISingleView is closure-local; use a synthetic view:
  const view = {
    projectiles: [{ id: 1, x: 3, z: 0.5, velX: 8, velZ: 0.2, owner: 'player', volleyCount: 1, type: 'fireball', sightFrames: 6 }],
    self: { paddleX: 7, paddleZ: -0.4, mana: 3, cooldowns: { fireball:0, frostbolt:0, thunderstorm:0 },
            freezeTime: 0, casting: null, castProgress: 0, castTime: 1, juice: 0, juiceActive: false, shieldCharges: 0 },
    opp: { paddleZ: 0.3 },
    geom: { tableWidth: 16, halfDepth: 4, paddleBoundary: 3.8 },
    roundActive: true,
  };
  const p = window.skillToProfile(0.45);
  const a = window.decideAI(view, 100, window.makeAIRng(100 ^ window.AI_RNG_SEED), p);
  const b = window.decideAI(view, 100, window.makeAIRng(100 ^ window.AI_RNG_SEED), p);
  console.assert(JSON.stringify(a) === JSON.stringify(b), '2a: decideAI must be reproducible', a, b);
  // track-&-chase: threat.z (0.5) is above paddleZ (-0.4), gap 0.9 > deadzone → move toward it (+1)
  console.assert(a.moveDir === 1, '2a: should chase the ball toward +z', a);
  console.log('TEST 2a done');
})();

// TEST 2b: sight-gated parry — below parrySight the AI must NOT parry, at/above it may
(() => {
  const mk = (sight) => ({
    projectiles: [{ id: 2, x: 6.6, z: -0.4, velX: 9, velZ: 0, owner: 'player', volleyCount: 0, type: 'fireball', sightFrames: sight }],
    self: { paddleX: 7, paddleZ: -0.4, mana: 3, cooldowns:{fireball:0,frostbolt:0,thunderstorm:0},
            freezeTime:0, casting:null, castProgress:0, castTime:1, juice:0, juiceActive:false, shieldCharges:0 },
    opp: { paddleZ: 0 }, geom:{ tableWidth:16, halfDepth:4, paddleBoundary:3.8 }, roundActive:true,
  });
  const p = window.skillToProfile(0.45);   // parrySight ≈ round(lerp(14,2,0.45)) = 9
  const late = window.decideAI(mk(1), 0, window.makeAIRng(1), p);  // seen 1 frame → too late
  const seen = window.decideAI(mk(20), 0, window.makeAIRng(1), p); // seen plenty
  console.assert(late.parry === false, '2b: must NOT parry a barely-seen threat', late);
  console.assert(seen.parry === true,  '2b: must parry a long-seen in-range threat', seen);
  console.log('TEST 2b done');
})();

// TEST 2c: purity — no forbidden tokens in the AI source region (manual grep in Step 2/verify)
console.log('TEST 2c: run the grep in the verify step');
```

- [ ] **Step 2: Run test to verify it fails**

Reload, paste Step 1 snippet.
Expected: `2a` reproducibility may pass, but `2a: should chase the ball toward +z` and `2b` **fail** — the current `decideAI` leads the ball (uses `_reflectZ`/`timeToImpact`) and has no `sightFrames` concept, so `moveDir`/`parry` won't match. This confirms the old behavior is still in place.

- [ ] **Step 3: Delete `_reflectZ` and `DEFAULT_AI_PARAMS`**

Delete the `_reflectZ` function block (`index.html:12373–12381`, the comment `// Reflect a Z coordinate...` through its closing `}`).

Delete the entire `const DEFAULT_AI_PARAMS = { ... };` block (`index.html:12322–12340`) and its export line `window.DEFAULT_AI_PARAMS = DEFAULT_AI_PARAMS;` (`index.html:12498`). (The `AI_SKILL_AVERAGE`/`getAISkill`/`skillToProfile` block added in Task 1 sits just below where `DEFAULT_AI_PARAMS` was.)

- [ ] **Step 4: Replace the `decideAI` body**

Replace the whole `function decideAI(view, frame, rng, params) { ... }` (`index.html:12383–12492`) with this `profile`-driven track-&-chase version:

```js
            function decideAI(view, frame, rng, profile) {
                // PURE: no performance.now / Date.now / Math.random / .mesh.
                // Track-&-chase: the AI watches the ball's CURRENT position (from a
                // reaction-lagged view) and chases it at player speed. It never solves
                // for a future impact point, so fast / steep / bounced shots outrun it.
                const idle = { moveDir: 0, parry: false, fireball: false, frostbolt: false, thunderstorm: false, juice: false };
                if (!view.roundActive) return idle;

                const s      = view.self;
                const halfD  = view.geom.halfDepth;
                const threat = _aiFindUrgentThreat(view);   // closest incoming (velX>0, owner!=='ai') or null

                // ---- Movement (every frame) ----
                let targetZ = null;   // null = no reason to move → hold
                if (threat) {
                    const dodging = threat.type === 'frostbolt'
                        && (threat.sightFrames || 0) >= profile.dodgeSightFrames;
                    if (dodging) {
                        // Recognized the frostbolt in time → commit to the opposite half
                        // (blocking it would freeze us). Fixed target so we don't chase a wall.
                        targetZ = threat.z >= 0 ? -halfD * 0.5 : halfD * 0.5;
                    } else {
                        // Chase where the ball IS (frostbolt seen too late is treated like a
                        // normal ball here → the AI tries to block it and gets frozen).
                        targetZ = threat.z;
                    }
                } else {
                    // Idle: only reposition toward the open lane if meaningfully out of place.
                    const open = _aiFindOpenTarget(view);
                    if (Math.abs(open - s.paddleZ) > 1.5) targetZ = open;
                }
                let moveDir = 0;
                if (targetZ !== null) {
                    const diff = targetZ - s.paddleZ;
                    if (Math.abs(diff) > profile.trackDeadzone) moveDir = Math.sign(diff);
                }
                // Defense over offense: if mid-cast and a threat will reach us before the
                // cast finishes (plus a little slack), bail to defend (moving cancels the
                // cast); otherwise hold to let the cast land.
                if (s.casting) {
                    let holdCast = true;
                    if (threat && threat.velX > 0) {
                        const remainingCast = Math.max(0, (s.castTime || 0) - (s.castProgress || 0));
                        const timeToImpact  = (s.paddleX - threat.x) / threat.velX;
                        if (timeToImpact < remainingCast + 0.2) holdCast = false;
                    }
                    if (holdCast) moveDir = 0;
                }

                // ---- Parry (every frame): press when an in-range threat has been SEEN
                // long enough. Late/narrow perception at low skill → natural whiffs. ----
                const PARRY_RANGE = 2.5;
                const parry = !!(threat
                    && Math.abs(threat.z - s.paddleZ) < PARRY_RANGE
                    && (threat.sightFrames || 0) >= profile.parrySight);

                // ---- Casting: gated to a fixed cast-decision cadence, with offensive
                // casts further phase-gated by castCadence (low skill = sparse). ----
                const K = 8;                                  // cast-decision base period (~0.13s @60Hz)
                const isCastFrame = (frame % K === 0);
                let fireball = false, frostbolt = false, thunderstorm = false;
                if (isCastFrame) {
                    const cycle = Math.floor(frame / K);
                    const offenseOpen = (cycle % Math.max(1, profile.castCadence)) === 0;
                    const safe = _aiSafeToStartCast(view);
                    const cd   = s.cooldowns;
                    const canFireball  = offenseOpen && safe && cd.fireball  <= 0 && s.mana >= 1
                        && view.projectiles.length < 10 && !_aiIsOppBlocking(view) && !s.casting;
                    // Frostbolt WANTS the opponent in front (it freezes them), so it does not
                    // avoid a blocking opponent like fireball does.
                    const canFrostbolt = offenseOpen && safe && cd.frostbolt <= 0 && s.mana >= 1
                        && view.projectiles.length < 10 && !s.casting;
                    // Thunderstorm is a competence read, not a reflex: only a skilled AI
                    // recognizes the multi-projectile panic-clear.
                    const canThunderstorm = cd.thunderstorm <= 0 && s.mana >= 2
                        && _aiIncomingProjectiles(view).length >= 2
                        && profile.thunderstormSkill >= 0.6;
                    frostbolt    = canFrostbolt;
                    fireball     = canFireball && !frostbolt;
                    thunderstorm = canThunderstorm;
                }

                // ---- Juice ----
                const juice = s.juice >= JUICE.MAX && !s.juiceActive;

                return { moveDir, parry, fireball, frostbolt, thunderstorm, juice };
            }
```

- [ ] **Step 5: Stamp `sightFrames` onto the view in `buildAISingleView`**

In `buildAISingleView` (`index.html:12503`), change the `projSnaps` map (`index.html:12505–12514`) to include `sightFrames`, reading the driver-owned counter added in Step 6:

```js
                const projSnaps = projectiles.map(p => ({
                    id:          p.id,
                    x:           p.x,
                    z:           p.z,
                    velX:        p.velX,
                    velZ:        p.velZ,
                    owner:       p.owner,
                    volleyCount: p.volleyCount,
                    type:        p.type,
                    sightFrames: aiThreatSight[p.id] || 0,
                }));
```

- [ ] **Step 6: Add the driver-owned sight counter + profile wiring in `runSinglePlayerFrame`**

Add a module-scope declaration next to where `aiViewHistory` is declared (search for `aiViewHistory` near the SP driver; add beside it):

```js
            const aiThreatSight = {};   // projectile id → frames continuously incoming (driver-owned; keeps decideAI pure)
```

Replace the body of `runSinglePlayerFrame` from `spFrameCounter++;` through the `decideAI(...)` call (`index.html:12577–12586`) with:

```js
                spFrameCounter++;
                // Update the driver-owned sight counter BEFORE snapshotting the view, so the
                // snapshot (and thus the AI's lagged perception) carries correct sightFrames.
                const _incoming = new Set();
                for (const p of projectiles) {
                    if (p.velX > 0 && p.owner !== 'ai') {
                        _incoming.add(p.id);
                        aiThreatSight[p.id] = (aiThreatSight[p.id] || 0) + 1;
                    }
                }
                for (const k in aiThreatSight) { if (!_incoming.has(+k)) delete aiThreatSight[k]; }

                const leftInput  = buildPlayerInput();
                const aiProfile  = skillToProfile(getAISkill());
                // Reaction delay: the AI decides on the world it saw `reactionFrames` ago.
                aiViewHistory.push(buildAISingleView());
                const lag = (aiProfile.reactionFrames | 0);
                while (aiViewHistory.length > lag + 1) aiViewHistory.shift();
                const aiView = aiViewHistory[0];   // oldest retained ≈ `lag` frames old once warmed
                const rightInput = decideAI(aiView, spFrameCounter, makeAIRng(spFrameCounter ^ AI_RNG_SEED), aiProfile);
```

(The lines after — `window.VolleyboltSim.simulateNetworkFrame(...)` and `updateSinglePlayerPresentation(dt)` — stay unchanged.)

- [ ] **Step 7: Update the `dbg.aiDeterminism` oracle for the new signature + view field**

In `attachAIDeterminism` (`index.html:15546`):

In `_syntheticView` (`index.html:15547–15563`), add `sightFrames` to each synthetic projectile so dodge/parry logic is exercised deterministically:

```js
                    projectiles: [
                        { id: 1, x: 3.0, z: (seed % 5) * 0.4 - 1.0, velX: 8, velZ: 0.5,  owner: 'player', volleyCount: 1, type: 'fireball',  sightFrames: (seed % 13) },
                        { id: 2, x: 5.0, z: (seed % 3) * 0.3,        velX: 6, velZ: -0.3, owner: 'player', volleyCount: 0, type: 'frostbolt', sightFrames: (seed % 7)  },
                    ],
```

In `_foldAI` (`index.html:15569`), replace the `window.DEFAULT_AI_PARAMS` argument with a fixed profile so the oracle is difficulty-stable:

```js
                    const result = window.decideAI(view, i, window.makeAIRng((seed + i) ^ window.AI_RNG_SEED), window.skillToProfile(0.45));
```

- [ ] **Step 8: Run tests — behavior + reproducibility**

Reload the page, paste the Step 1 snippet.
Expected: `TEST 2a done` and `TEST 2b done` with **no** assertion errors (`moveDir === 1`, sight-gated parry correct).

- [ ] **Step 9: Re-pin the AI determinism golden**

In console:
```js
window.dbg.aiDeterminism(50, 42)   // note the .fold value; run twice — reproducible must be true
```
Copy the printed `fold`. Update the golden comment at `index.html:15544–15545` to:
```js
        // AI_GOLDEN (dbg.aiDeterminism(50,42).fold) = "<PASTE_FOLD_HERE>"  (re-pinned 2026-07-04:
        // track-&-chase rewrite; difficulty via skillToProfile(skill), single competence scalar)
```

- [ ] **Step 10: Verify purity + sim oracle unchanged**

Purity grep (run from repo root):
```bash
awk 'NR>=12383 && NR<=12470' index.html | grep -nE 'performance\.now|Date\.now|Math\.random|\.mesh'
```
Expected: **no output** (empty) — `decideAI` is pure. (Line range is approximate after edits; if the grep hits, inspect — a hit inside `decideAI` is a bug.)

Sim oracle:
```js
window.dbg.determinism(180, 12345).fold   // expected: "954ea557" (unchanged)
```

- [ ] **Step 11: Smoke-play a singles match**

Start a singles match. Confirm: the AI moves and chases the ball, blocks slow straight shots, does NOT crash, casts less relentlessly than before, and completes to a win/loss. (Full tuning is Task 3.)

- [ ] **Step 12: Commit**

```bash
git add index.html
git commit -m "Rewrite singles AI to track-&-chase driven by one competence scalar

Replace perfect-prediction-plus-noise decideAI with reactive track-&-chase:
sight-based frostbolt dodge, cadence-gated offense, skill-gated thunderstorm,
sight-gated parry. Difficulty is skillToProfile(getAISkill()); driver-owned
sight counter keeps decideAI pure. Remove DEFAULT_AI_PARAMS and _reflectZ.
Re-pin dbg.aiDeterminism golden."
```

---

## Task 3: Playtest tuning + final pin

Tunes `AI_SKILL_AVERAGE` and the `skillToProfile` curve endpoints from real play until an average player gets a fair, winnable fight, then locks the values and records them in the spec's acceptance log. Deliverable: a shipped "average" difficulty that meets §8.5 of the spec, and a short as-built note.

**Files:**
- Modify: `index.html` — `AI_SKILL_AVERAGE` and/or `skillToProfile` endpoint constants (Task 1 block).
- Create: `docs/superpowers/specs/2026-07-04-ai-behavior-rethink-as-built.md` — final values + playtest notes.

**Interfaces:**
- Consumes: everything from Tasks 1–2. No new interfaces.

- [ ] **Step 1: Baseline playtest at `skill = 0.45`**

Play 3–5 singles matches. For each, note: did fast/steep/bounced shots beat the AI? Did it occasionally freeze itself on a frostbolt? Was offense punishable? Did it feel fair/winnable? Record wins/losses.

- [ ] **Step 2: Verify the scalar couples all axes**

In console, temporarily probe the extremes without shipping them:
```js
// Verify low skill degrades ALL axes coherently (read-only check of the curve)
console.table([0, 0.25, 0.45, 0.7, 1].map(s => ({ s, ...window.skillToProfile(s) })));
```
Confirm the table is monotonic and the 0.45 row's values feel right for "average." (This proves the single-scalar coupling for spec §8.5.)

- [ ] **Step 3: Adjust and re-test**

If too hard: lower `AI_SKILL_AVERAGE` (e.g. 0.45 → 0.35) OR widen the easy endpoints in `skillToProfile` (e.g. `reactionFrames` 12→16 at s=0, `trackDeadzone` 1.1→1.4). If too easy: nudge upward. Change ONE thing at a time, reload, replay 2–3 matches. Repeat until "fair/winnable for an average player" is met.

> If the average AI feeling "never uses thunderstorm" is undesirable, lower the `thunderstormSkill >= 0.6` threshold in `decideAI` (Task 2, Step 4) toward `0.45` so the average AI uses it occasionally. Change and re-test the same way.

- [ ] **Step 4: Confirm oracles still hold after tuning**

Tuning `AI_SKILL_AVERAGE` does NOT change the oracle (it pins `skillToProfile(0.45)` explicitly). If you changed `skillToProfile` endpoints, the oracle golden WILL change — re-run and re-pin:
```js
window.dbg.aiDeterminism(50, 42)   // if fold changed due to curve edits, update the golden comment
window.dbg.determinism(180, 12345).fold   // must still be "954ea557"
```

- [ ] **Step 5: Write the as-built note**

Create `docs/superpowers/specs/2026-07-04-ai-behavior-rethink-as-built.md` with: final `AI_SKILL_AVERAGE`, final `skillToProfile` endpoints, the final `thunderstormSkill` threshold, the pinned `dbg.aiDeterminism` golden, and 3–5 lines of playtest observations (what beats the AI, how it feels vs the old one).

- [ ] **Step 6: Commit**

```bash
git add index.html docs/superpowers/specs/2026-07-04-ai-behavior-rethink-as-built.md
git commit -m "Tune average AI difficulty and record as-built values"
```

---

## Self-Review

**1. Spec coverage:**
- §3.1 one seam → Task 1 (getAISkill/skillToProfile) + Task 2 Step 6 (wiring). ✓
- §3.2 getAISkill constant + documented clutch seam → Task 1 Step 3 (comment). ✓
- §3.3 skillToProfile curve + symmetry banner → Task 1 Step 3. ✓
- §4.1 track-&-chase movement (remove _reflectZ/lead/aimError) → Task 2 Steps 3–4. ✓
- §4.2 sight-based frostbolt dodge → Task 2 Step 4 (`dodgeSightFrames`) + Steps 5–6 (sight counter). ✓
- §4.3 cadence offense (remove castAggression) → Task 2 Step 4 (`castCadence` phase-gate). ✓ (Refinement: phase-gate instead of settle-streak — documented in the movement/cast comments; pure, no extra state.)
- §4.4 thunderstorm competence gate → Task 2 Step 4 (`thunderstormSkill >= 0.6`). ✓
- §4.5 sight-gated parry (remove parryTimingError) → Task 2 Step 4 (`parrySight`). ✓
- §4.6 juice unchanged → Task 2 Step 4. ✓
- §5 de-bloat ledger → Task 2 Steps 3–4 (removals). ✓
- §6 determinism (pure decideAI, rng threaded, driver-owned sight state, oracle re-pin) → Task 2 Steps 4/6/7/9/10. ✓
- §7 scope (singles only) → Global Constraints. ✓
- §8 acceptance (purity grep, reproducibility, oracle, sim oracle, playtest, symmetry) → Task 2 Steps 8–11 + Task 3. ✓

**2. Placeholder scan:** No TBD/TODO. The one golden hash is intentionally pinned at runtime (Task 2 Step 9) because it can only be known by executing the pinned function — the plan specifies exactly how to capture and where to write it. Task 3 tuning values are deliberately playtest-derived with concrete starting numbers and a one-knob-at-a-time procedure.

**3. Type consistency:** `profile` fields (`reactionFrames`, `trackDeadzone`, `dodgeSightFrames`, `parrySight`, `castCadence`, `thunderstormSkill`) are defined identically in Task 1 Step 3 and consumed under the same names in Task 2 Step 4. `sightFrames` is produced in `buildAISingleView` (Task 2 Step 5) + the synthetic oracle view (Step 7) and consumed as `threat.sightFrames` in `decideAI` (Step 4). `aiThreatSight` is declared (Step 6) and read (Step 5) under one name. `decideAI` signature `(view, frame, rng, profile)` is consistent across Task 2 Steps 4/7 and both test snippets.
