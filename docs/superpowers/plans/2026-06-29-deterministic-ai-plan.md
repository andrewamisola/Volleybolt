# Deterministic Singles AI — Implementation Plan (Phase 2, Step 2.1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the non-deterministic singles AI (inline block ~lines 12124–12250, `tryAIParry` ~11332–11349) with a pure deterministic virtual-player AI that emits the canonical `{moveDir, parry, fireball, frostbolt, thunderstorm}` input struct and has it applied by `applyCombatantInput` under the same rules a human player uses. No behavior change to `js/sim.js`; no change to the multiplayer flow; no difficulty UI.

**Architecture:** Three new functions — `buildAISingleView()` (mesh boundary), `decideAI(view, frame, rng, params)` (pure strategy), and `applyCombatantInput(c, input, dt)` (shared input applier) — plus a `spFrameCounter` in the SP loop and a `dbg.aiDeterminism` oracle. The adapter in `updateGameLogic` replaces ~130 lines of inline AI with three lines.

**Tech stack:** Vanilla JS single-page game; no build step. `index.html` inline `<script>` is authoritative.

---

## Global constraints

- **Determinism law:** no `Math.random`/`Date.now`/`performance.now`/`.mesh` inside `decideAI` or any helper it calls. `buildAISingleView` is the sole permitted mesh-reading boundary.
- **The oracle is the gate.** Existing golden: `dbg.determinism(180, 12345)` → `b1df6797`. This step does not touch `js/sim.js`; the golden must be `b1df6797` after every task. If it is not, STOP.
- **New AI oracle** `dbg.aiDeterminism(steps, seed)` is pinned in Task 2 and verified in every subsequent task.
- **Do not touch `js/sim.js`** at any point in this plan.
- **Singles only:** doubles AI and `predictZAtX` are out of scope.
- **Inline is authoritative:** only edit `index.html`.
- **Append-only working log:** after the final task, append a dated entry to `docs/agents/gameplay-combat.md`.

---

## Standard verification recipe (referenced as "VERIFY")

Run these in the browser. "VERIFY(golden=X)" means assert `a.fold === X`.

1. Navigate to `http://localhost:8000/index.html?cb=<unique>` (fresh document).
2. Click the page once (dismiss "Click to Start"), then `window.startSinglesMatch()`, wait ~2 s.
3. `const a = window.dbg.determinism(180,12345), b = window.dbg.determinism(180,12345), c = window.dbg.determinism(180,999);`
   - Assert `a.fold === b.fold` (reproducible).
   - Assert `a.fold === 'b1df6797'` (golden unchanged).
   - Assert `a.fold !== c.fold` (seed-sensitive).
4. Screenshot — confirm the match renders (scoreboard, towers, paddles) and the console shows only the favicon 404.

---

## Task 1: Add the SP fixed-step frame counter (`spFrameCounter`)

**Files:**
- Modify: `index.html` — declare `spFrameCounter` near the other SP loop state variables; increment it inside `updateGameLogic` at the top of the sim-tick block.

**What changes:** one integer variable, one increment, zero behavior change. No AI logic added yet.

**Why it's safe:** a read-only counter that nothing reads yet. The existing AI path is untouched.

- [ ] **Step 1:** Locate the cluster of SP state variables near the top of the inline script (near `aiMoveDir`, `AI_THINK_INTERVAL`, `aiLastThinkTime`). Add:

```js
let spFrameCounter = 0;    // fixed-step frame counter for deterministic SP AI cadence
```

- [ ] **Step 2:** Inside `updateGameLogic(dt)`, at the top of the block that runs sim logic (just before or after `dt`-based time accumulation, not inside the render path), add:

```js
spFrameCounter++;
```

  Confirm via console that `spFrameCounter` increments during a running match: `window.spFrameCounter` should read a large integer after a few seconds.

- [ ] **Step 3:** Grep to confirm `performance.now` is NOT called in relation to `spFrameCounter`:

```bash
grep -n "spFrameCounter" /Users/andrewamisola/Projects/Volleybolt/index.html
```

Expected: the declaration and one increment — nothing else yet.

- [ ] **Step 4:** VERIFY(golden=`b1df6797`). The counter does not affect any game state that `hashGameState` measures.

- [ ] **Step 5:** Commit.

```bash
git add index.html
git commit -m "SP loop: add spFrameCounter integer fixed-step counter (prerequisite for deterministic AI cadence)"
```

---

## Task 2: Write pure `decideAI`, `makeAIRng`, `DEFAULT_AI_PARAMS`, and `dbg.aiDeterminism` (no wiring)

**Files:**
- Modify: `index.html` — add the new block as a self-contained named section, after the existing AI constants and before `updateGameLogic`. No existing code is deleted or modified.

**What changes:** new code only. The old AI inline block is untouched. Nothing calls `decideAI` yet.

**Why it's safe:** dead code until the adapter in Task 5 wires it in. Fully isolated; cannot break anything.

**Interfaces produced:**
- `makeAIRng(seed)` → a `() => number` function returning values in `[0,1)` via LCG. Integer-only internal state.
- `DEFAULT_AI_PARAMS` — the default params object (see spec §4.1).
- `decideAI(view, frame, rng, params)` → `{moveDir, parry, fireball, frostbolt, thunderstorm, juice}`. Pure. No mesh access, no wall-clock, no `Math.random`.
- `window.dbg.aiDeterminism(steps, seed)` — folds `decideAI` over a scripted synthetic view sequence into a 32-bit hex hash. No mesh reads, no game loop.

- [ ] **Step 1:** Add the `makeAIRng` LCG helper:

```js
// ---- Deterministic AI RNG (integer-seeded LCG) ----
function makeAIRng(seed) {
  let s = seed | 0;
  return function aiRng() {
    s = (Math.imul(1664525, s) + 1013904223) | 0;
    return (s >>> 0) / 0xFFFFFFFF;
  };
}
```

Verify in console: `makeAIRng(42)()` returns the same number twice when called with a fresh seed. Calling twice with the same seed:
```js
const r1 = makeAIRng(42); r1();
const r2 = makeAIRng(42); r2();
// r1's first call must equal r2's first call.
```

- [ ] **Step 2:** Add `DEFAULT_AI_PARAMS`:

```js
const DEFAULT_AI_PARAMS = {
  reactionFrames:   0,     // extra lag frames before decision takes effect (difficulty knob)
  aimError:         0,     // max Z-offset error on cast targeting, world units (difficulty knob)
  parryTimingError: 0,     // extra frames before parry fires (difficulty knob)
  castAggression:   1.0,   // multiplier on cast-readiness threshold
  thinkIntervalK:   13,    // think cadence: decide every K frames (~0.22s at 60Hz)
};
const AI_RNG_SEED = 0xA1DE; // fixed constant; not a secret, just a stable seed offset
```

- [ ] **Step 3:** Add the pure AI helper functions. Each must be pure (no mesh, no globals mutated, no wall-clock):

```js
// Pure AI helpers — no mesh reads, no Math.random, no wall-clock.

function _aiIncomingProjectiles(view) {
  // Projectiles heading toward the AI (right) side: velX < 0 means moving right-to-left,
  // but the AI is on the right, so incoming = velX < 0 (heading negative X, toward right gate).
  // NOTE: confirm sign convention against the live SP loop before wiring.
  return view.projectiles.filter(p => p.velX < 0 && p.owner !== 'ai');
}

function _aiFindUrgentThreat(view) {
  const incoming = _aiIncomingProjectiles(view);
  if (!incoming.length) return null;
  // Closest to AI paddle by X distance (smallest absolute X difference).
  return incoming.reduce((a, b) => Math.abs(a.x - view.self.paddleX) < Math.abs(b.x - view.self.paddleX) ? a : b);
}

function _aiFindOpenTarget(view) {
  // Target a Z away from the opponent paddle.
  const oppZ = view.opp.paddleZ;
  const halfDepth = view.geom.halfDepth;
  return oppZ > 0 ? -halfDepth * 0.6 : halfDepth * 0.6;
}

function _aiIsOppBlocking(view) {
  return Math.abs(view.self.paddleZ - view.opp.paddleZ) < 1.5;
}

function _aiSafeToStartCast(view) {
  // Safe if no projectile is heading toward the AI side.
  return _aiIncomingProjectiles(view).length === 0;
}
```

- [ ] **Step 4:** Add `decideAI`:

```js
function decideAI(view, frame, rng, params) {
  // PURE: no performance.now / Date.now / Math.random / .mesh.
  if (!view.roundActive) return { moveDir: 0, parry: false, fireball: false, frostbolt: false, thunderstorm: false, juice: false };

  const K = params.thinkIntervalK;
  // On non-think frames return a neutral input (movement handled below regardless).
  const isThinkFrame = (frame % K === 0);

  // --- Movement (every frame: smooth, not gated) ---
  const threat = _aiFindUrgentThreat(view);
  const targetZ = threat ? threat.z : _aiFindOpenTarget(view);
  const diff = targetZ - view.self.paddleZ;
  const moveDir = Math.abs(diff) > 0.25 ? Math.sign(diff) : 0;

  if (!isThinkFrame) {
    return { moveDir, parry: false, fireball: false, frostbolt: false, thunderstorm: false, juice: false };
  }

  // --- Cast decisions (think frames only) ---
  const safe = _aiSafeToStartCast(view);
  const s    = view.self;
  const cd   = s.cooldowns;

  const canFireball    = safe && cd.fireball    <= 0 && s.mana >= 1 && view.projectiles.length < 10 && !_aiIsOppBlocking(view) && !s.casting;
  const canFrostbolt   = safe && cd.frostbolt   <= 0 && s.mana >= 2 && view.projectiles.length < 10 && !_aiIsOppBlocking(view) && !s.casting;
  const canThunderstorm = cd.thunderstorm <= 0 && s.mana >= 2 && _aiIncomingProjectiles(view).length >= 2;

  // Frostbolt preferred when available (freezes opponent); otherwise fireball.
  const castFrostbolt   = canFrostbolt;
  const castFireball    = canFireball && !castFrostbolt;
  const castThunderstorm = canThunderstorm;

  // --- Parry (deterministic: press when incoming is in parry range) ---
  const parryRange  = 2.5; // world-unit Z-distance threshold; confirm against SP parry window
  const parryTarget = threat && Math.abs(threat.z - s.paddleZ) < parryRange;
  const parry       = !!parryTarget;

  // --- Juice ---
  const MAX_JUICE = 100; // confirm against SP constant before wiring
  const juice = s.juice >= MAX_JUICE && !s.juiceActive;

  return { moveDir, parry, fireball: castFireball, frostbolt: castFrostbolt, thunderstorm: castThunderstorm, juice };
}
```

**Note:** the constants `1` (fireball mana), `2` (frostbolt mana, thunderstorm mana), `100` (MAX_JUICE), and `2.5` (parryRange) are stand-ins. During Task 5 (wiring) confirm each against the live SP constants (`abilities.fireball.manaCost`, etc.) before the adapter goes live.

- [ ] **Step 5:** Add `dbg.aiDeterminism`. This helper must NOT read any mesh or game state — it operates entirely on a synthetic scripted view:

```js
// Extend dbg after it is defined in the existing code.
(function() {
  const _syntheticView = (seed) => ({
    projectiles: [
      { id: 1, x: 3.0, z: (seed % 5) * 0.4 - 1.0, velX: -8, velZ: 0.5, owner: 'player', volleyCount: 1, type: 'fireball' },
      { id: 2, x: 5.0, z: (seed % 3) * 0.3,        velX: -6, velZ: -0.3, owner: 'player', volleyCount: 0, type: 'frostbolt' },
    ],
    self: {
      paddleX: 7, paddleZ: (seed % 7) * 0.2 - 0.6,
      mana: 3,
      cooldowns: { fireball: 0, frostbolt: 0, thunderstorm: 0 },
      freezeTime: 0, casting: null, juice: 0, juiceActive: false, shieldCharges: 0,
    },
    opp: { paddleZ: (seed % 11) * 0.15 - 0.8 },
    geom: { tableWidth: 16, halfDepth: 4, paddleBoundary: 3.8 },
    roundActive: true,
  });

  function aiDeterminism(steps, seed) {
    let hash = 0;
    const rng = makeAIRng(seed ^ AI_RNG_SEED);
    for (let i = 0; i < steps; i++) {
      const view   = _syntheticView(seed + i);
      const result = decideAI(view, i, makeAIRng((seed + i) ^ AI_RNG_SEED), DEFAULT_AI_PARAMS);
      // Fold result into hash.
      hash = ((hash << 5) - hash + result.moveDir + 1)  | 0;
      hash = ((hash << 5) - hash + (result.parry         ? 7  : 0)) | 0;
      hash = ((hash << 5) - hash + (result.fireball      ? 13 : 0)) | 0;
      hash = ((hash << 5) - hash + (result.frostbolt     ? 17 : 0)) | 0;
      hash = ((hash << 5) - hash + (result.thunderstorm  ? 19 : 0)) | 0;
      hash = ((hash << 5) - hash + (result.juice         ? 23 : 0)) | 0;
    }
    const fold = ((hash >>> 0).toString(16)).padStart(8, '0');
    const fold2 = aiDeterminism_inner(steps, seed); // call twice, assert equal
    return { fold, reproducible: fold === fold2 };
  }

  // Inner call for reproducibility check (avoids infinite recursion by duplicating the loop inline).
  function aiDeterminism_inner(steps, seed) {
    let hash = 0;
    for (let i = 0; i < steps; i++) {
      const view   = _syntheticView(seed + i);
      const result = decideAI(view, i, makeAIRng((seed + i) ^ AI_RNG_SEED), DEFAULT_AI_PARAMS);
      hash = ((hash << 5) - hash + result.moveDir + 1)  | 0;
      hash = ((hash << 5) - hash + (result.parry         ? 7  : 0)) | 0;
      hash = ((hash << 5) - hash + (result.fireball      ? 13 : 0)) | 0;
      hash = ((hash << 5) - hash + (result.frostbolt     ? 17 : 0)) | 0;
      hash = ((hash << 5) - hash + (result.thunderstorm  ? 19 : 0)) | 0;
      hash = ((hash << 5) - hash + (result.juice         ? 23 : 0)) | 0;
    }
    return ((hash >>> 0).toString(16)).padStart(8, '0');
  }

  if (window.dbg) window.dbg.aiDeterminism = aiDeterminism;
})();
```

- [ ] **Step 6:** Pin the AI oracle golden. In the browser console after loading the page:

```js
const result = window.dbg.aiDeterminism(50, 42);
console.log(result.fold, result.reproducible); // reproducible must be true
```

Record the `fold` value. This is the `AI_GOLDEN`. Write it as a comment in the `dbg.aiDeterminism` block and record it in the commit message. Every subsequent task asserts this value.

- [ ] **Step 7:** Purity check:

```bash
grep -n "performance\.now\|Date\.now\|Math\.random\|\.mesh\b" /Users/andrewamisola/Projects/Volleybolt/index.html \
  | grep -E "decideAI|makeAIRng|_aiFindUrgentThreat|_aiFindOpenTarget|_aiIsOppBlocking|_aiSafeToStartCast|_aiIncomingProjectiles"
```

Expected: zero hits.

- [ ] **Step 8:** VERIFY(golden=`b1df6797`). The new block is dead code; the sim oracle must be unaffected.

- [ ] **Step 9:** Commit.

```bash
git add index.html
git commit -m "Deterministic AI: add pure decideAI + makeAIRng + DEFAULT_AI_PARAMS + dbg.aiDeterminism (no wiring; AI oracle golden = <AI_GOLDEN>)"
```

---

## Task 3: Write `buildAISingleView()`

**Files:**
- Modify: `index.html` — add `buildAISingleView` in the same new block, after the pure helpers.

**What changes:** one new function. Still no wiring; the old AI inline block is untouched.

**Why it's safe:** the function only reads; it does not mutate anything. Dead until Task 5.

**Interfaces produced:**
- `buildAISingleView()` → view object matching the spec §4.2 shape exactly.

- [ ] **Step 1:** Locate the live SP state variables to read. Note exact variable names used in the inline AI block (~12124–12250) for:
  - Projectile position: `proj.mesh.position.x`, `proj.mesh.position.z`
  - Projectile physics: `proj.velX`, `proj.velZ`, `proj.owner`, `proj.volleyCount`, `proj.id`, `proj.type`
  - AI paddle: `aiPaddle.position.x`, `aiPaddle.position.z`
  - Player paddle: `playerPaddle.position.z`
  - Combatant state: `combatants.right.mana`, `combatants.right.cooldowns`, `combatants.right.freezeTime`, `combatants.right.casting`, `combatants.right.juice`, `combatants.right.juiceActive`, `combatants.right.shieldCharges`
  - Constants: `TABLE_WIDTH` (or equivalent), `HALF_DEPTH`, `PADDLE_BOUNDARY`
  - Loop flag: `roundActive`

  Do a targeted grep to confirm each variable name before writing the function:

```bash
grep -n "aiPaddle\|playerPaddle\|HALF_DEPTH\|TABLE_WIDTH\|PADDLE_BOUNDARY\|roundActive\b" \
  /Users/andrewamisola/Projects/Volleybolt/index.html | head -60
```

- [ ] **Step 2:** Write `buildAISingleView`:

```js
// Mesh-reading boundary — the ONLY place AI path touches .mesh.
// Everything downstream (decideAI) is pure.
function buildAISingleView() {
  const projSnaps = (window.projectiles || []).map(p => ({
    id:          p.id,
    x:           p.mesh.position.x,
    z:           p.mesh.position.z,
    velX:        p.velX,
    velZ:        p.velZ,
    owner:       p.owner,
    volleyCount: p.volleyCount,
    type:        p.type,
  }));
  const cr = combatants.right;
  return {
    projectiles: projSnaps,
    self: {
      paddleX:       aiPaddle.position.x,
      paddleZ:       aiPaddle.position.z,
      mana:          cr.mana,
      cooldowns: {
        fireball:    cr.cooldowns.fireball    || 0,
        frostbolt:   cr.cooldowns.frostbolt   || 0,
        thunderstorm: cr.cooldowns.thunderstorm || 0,
      },
      freezeTime:    cr.freezeTime    || 0,
      casting:       cr.casting       || null,
      juice:         cr.juice         || 0,
      juiceActive:   cr.juiceActive   || false,
      shieldCharges: cr.shieldCharges || 0,
    },
    opp: {
      paddleZ: playerPaddle.position.z,
    },
    geom: {
      tableWidth:     TABLE_WIDTH,
      halfDepth:      HALF_DEPTH,
      paddleBoundary: PADDLE_BOUNDARY,
    },
    roundActive: !!roundActive,
  };
}
```

**IMPORTANT:** Before submitting this step, verify each variable name (`combatants.right`, `aiPaddle`, `playerPaddle`, `TABLE_WIDTH`, `HALF_DEPTH`, `PADDLE_BOUNDARY`, `window.projectiles`) against the actual names in the live code. They may differ. Use the grep from Step 1 to confirm.

- [ ] **Step 3:** Smoke-test in browser console during a running match:

```js
const v = buildAISingleView();
console.assert(typeof v.self.mana === 'number', 'mana is a number');
console.assert(Array.isArray(v.projectiles), 'projectiles is array');
console.assert(typeof v.opp.paddleZ === 'number', 'opp.paddleZ is a number');
console.assert(typeof v.roundActive === 'boolean', 'roundActive is boolean');
```

- [ ] **Step 4:** Verify `decideAI` still produces consistent output using the live view:

```js
const v = buildAISingleView();
const i1 = decideAI(v, 100, makeAIRng(100 ^ AI_RNG_SEED), DEFAULT_AI_PARAMS);
const i2 = decideAI(v, 100, makeAIRng(100 ^ AI_RNG_SEED), DEFAULT_AI_PARAMS);
console.assert(JSON.stringify(i1) === JSON.stringify(i2), 'decideAI reproducible from live view');
```

- [ ] **Step 5:** AI oracle unchanged:

```js
const r = window.dbg.aiDeterminism(50, 42);
console.assert(r.fold === '<AI_GOLDEN>', 'AI oracle unchanged');
console.assert(r.reproducible === true);
```

- [ ] **Step 6:** VERIFY(golden=`b1df6797`).

- [ ] **Step 7:** Commit.

```bash
git add index.html
git commit -m "Deterministic AI: add buildAISingleView (mesh boundary; decideAI stays pure)"
```

---

## Task 4: Write `applyCombatantInput(c, input, dt)`

**Files:**
- Modify: `index.html` — add `applyCombatantInput` in the same new block.

**What changes:** one new function. Still no wiring.

**Why it's safe:** dead until Task 5. Does not change any existing cast helpers.

**Interfaces produced:**
- `applyCombatantInput(c, input, dt)` — applies a canonical input struct to combatant `c` under player rules.

- [ ] **Step 1:** Identify the exact call signatures of each cast helper used by the inline AI block:
  - `startCasting('ai', 'fireball')` — check ~line 12160 area
  - `castFrostbolt('ai')` — check ~line 12190 area
  - `executeThunderstorm('ai')` — check ~line 12230 area
  - `parryProjectile(...)` — check what arguments `tryAIParry` passes (~line 11332)

```bash
grep -n "startCasting\|castFrostbolt\|executeThunderstorm\|parryProjectile\|tryAIParry\|activateJuice\b" \
  /Users/andrewamisola/Projects/Volleybolt/index.html | head -40
```

- [ ] **Step 2:** Identify how the inline AI block moves the paddle (the `aiMoveDir`-based position update at ~line 12163) to understand the exact move formula `applyCombatantInput` should replicate:

```bash
grep -n "aiMoveDir\|aiSpeed\|aiPaddle\.position\.z\b" \
  /Users/andrewamisola/Projects/Volleybolt/index.html | head -20
```

- [ ] **Step 3:** Write `applyCombatantInput`. Fill in the exact signatures confirmed in Steps 1–2:

```js
// Interprets the canonical input struct against combatant c under player rules.
// The AI routes through this in 2.1; the human player will join it in 2.3.
function applyCombatantInput(c, input, dt) {
  // Movement — player speed, no urgency multiplier (see spec §5, Deviation 1).
  if (!c.freezeTime || c.freezeTime <= 0) {
    if (input.moveDir !== 0) {
      aiPaddle.position.z += input.moveDir * aiSpeed * dt;
      aiPaddle.position.z = Math.max(-PADDLE_BOUNDARY, Math.min(PADDLE_BOUNDARY, aiPaddle.position.z));
    }
  }

  // Parry — deterministic (see spec §5, Deviation 2).
  if (input.parry) {
    // Find the nearest incoming projectile in parry range and parry it.
    // Reuse the same projectile-selection logic from the old tryAIParry, minus the probability roll.
    const parryRange = 2.5; // confirm against live SP parry window
    const incoming = (window.projectiles || []).filter(p =>
      p.velX < 0 && p.owner !== 'ai' &&
      Math.abs(p.mesh.position.z - aiPaddle.position.z) < parryRange
    );
    if (incoming.length > 0) {
      // Closest by Z distance.
      const target = incoming.reduce((a, b) =>
        Math.abs(a.mesh.position.z - aiPaddle.position.z) < Math.abs(b.mesh.position.z - aiPaddle.position.z) ? a : b
      );
      parryProjectile(target, 'ai'); // confirm exact call signature
    }
  }

  // Casts — same guards as the player keydown path (each helper enforces its own mana/cooldown check).
  if (input.fireball    && !c.casting) startCasting('ai', 'fireball');
  if (input.frostbolt)                 castFrostbolt('ai');
  if (input.thunderstorm)              executeThunderstorm('ai');
  if (input.juice)                     activateJuice('ai'); // confirm function name
}
```

**IMPORTANT:** The parry path in `applyCombatantInput` still reads `p.mesh.position.z` because in 2.1 the SP engine is not yet on the sim path. This is the only mesh read permitted inside `applyCombatantInput` and it is explicitly temporary — it moves to `view.projectiles` when Step 2.3 runs. Add a `// TODO 2.3: replace with view.projectiles` comment.

- [ ] **Step 4:** Smoke-test: call it manually in the console during a match with a neutral input and confirm no errors:

```js
applyCombatantInput(combatants.right, { moveDir: 0, parry: false, fireball: false, frostbolt: false, thunderstorm: false, juice: false }, 1/60);
// Should produce no errors and no visible change.
```

- [ ] **Step 5:** AI oracle unchanged:

```js
const r = window.dbg.aiDeterminism(50, 42);
console.assert(r.fold === '<AI_GOLDEN>');
```

- [ ] **Step 6:** VERIFY(golden=`b1df6797`).

- [ ] **Step 7:** Commit.

```bash
git add index.html
git commit -m "Deterministic AI: add applyCombatantInput (shared virtual-player input applier; no wiring yet)"
```

---

## Task 5: Swap the adapter — wire `decideAI` into `updateGameLogic`, delete the old inline AI block

**Files:**
- Modify: `index.html` — replace the inline AI block (~12124–12250), remove the `tryAIParry` call (~12628), delete `tryAIParry` function definition (~11332–11349), delete `AI_PREDICTION_ERROR` constant (~11363), delete `aiLastThinkTime` if it is only used for the `performance.now` gate.

**What changes:** the old ~130-line inline AI block is removed and replaced with the three-line adapter. This is the largest, most visible change; all prior tasks make it safe.

**Why it's safe:** `decideAI`, `buildAISingleView`, and `applyCombatantInput` have been smoke-tested in isolation in Tasks 2–4. The old constants (`AI_THINK_INTERVAL`, `aiLastThinkTime`) are removed only after the replacement is confirmed working.

- [ ] **Step 1:** Confirm the exact line range of the inline AI block before touching anything:

```bash
grep -n "AI_THINK_INTERVAL\|aiLastThinkTime\|safeToStartCast\|tryAIParry\|AI_PREDICTION_ERROR" \
  /Users/andrewamisola/Projects/Volleybolt/index.html
```

- [ ] **Step 2:** Confirm `decideAI` constants match live SP values. In the browser console:

```js
// Confirm mana costs match what decideAI hardcoded as stand-ins.
console.log('fireball mana:', abilities.fireball.manaCost);   // expect 1
console.log('frostbolt mana:', abilities.frostbolt.manaCost); // expect 2
console.log('thunderstorm mana:', abilities.thunderstorm.manaCost); // expect 2
console.log('MAX_JUICE:', window.MAX_JUICE); // confirm constant name
```

Update the stand-in constants in `decideAI` to match live values if any differ.

- [ ] **Step 3:** Replace the inline AI block (~12124–12250) with the adapter:

```js
// --- Deterministic singles AI (Phase 2.1) ---
const _aiView  = buildAISingleView();
const _aiInput = decideAI(_aiView, spFrameCounter, makeAIRng(spFrameCounter ^ AI_RNG_SEED), DEFAULT_AI_PARAMS);
applyCombatantInput(combatants.right, _aiInput, dt);
```

Leave the old lines commented out until Step 4 confirms the match runs correctly.

- [ ] **Step 4:** Remove the `tryAIParry` call from the projectile-paddle collision handler (~12628). This is where the AI would previously trigger a probabilistic parry. `applyCombatantInput` now emits the parry decision via the `input.parry` flag, so the old call-site is dead.

- [ ] **Step 5:** Visual smoke-test — start a singles match and confirm:
  - AI paddle moves toward projectiles.
  - AI casts (watch for frostbolt / fireball projectiles fired by AI).
  - AI parries (watch for a parry event in the console; add a temporary `console.log` inside `applyCombatantInput`'s parry arm if needed).
  - Match reaches a win/loss state normally.

- [ ] **Step 6:** Once the match runs correctly, delete the commented-out old AI block, the `tryAIParry` function definition, `AI_PREDICTION_ERROR`, and `aiLastThinkTime` (if it is used only by the old `performance.now` gate):

```bash
grep -n "tryAIParry\|AI_PREDICTION_ERROR\|aiLastThinkTime\|performance\.now" \
  /Users/andrewamisola/Projects/Volleybolt/index.html
```

Expected after deletion: zero hits for these identifiers.

- [ ] **Step 7:** Purity check — confirm no `performance.now`, `Date.now`, `Math.random`, or `.mesh` in the AI path:

```bash
grep -n "performance\.now\|Date\.now\|Math\.random" \
  /Users/andrewamisola/Projects/Volleybolt/index.html \
  | grep -v "predictZAtX\|\/\/" \
  | head -20
```

The only surviving `Math.random` should be `predictZAtX` in the doubles AI path (~11457) — which is explicitly out of scope.

- [ ] **Step 8:** AI oracle unchanged:

```js
const r = window.dbg.aiDeterminism(50, 42);
console.assert(r.fold === '<AI_GOLDEN>', 'AI oracle still ' + r.fold);
console.assert(r.reproducible === true);
```

- [ ] **Step 9:** VERIFY(golden=`b1df6797`). The sim oracle must be unchanged because we never touched `js/sim.js`.

- [ ] **Step 10:** Commit.

```bash
git add index.html
git commit -m "Deterministic AI: swap adapter in updateGameLogic; delete tryAIParry, AI_PREDICTION_ERROR, perf.now think-gate"
```

---

## Task 6: Final verification pass

**Files:** no new code changes. Verification and working log only.

**What changes:** a dated working-log entry in `docs/agents/gameplay-combat.md`. If any verification step fails, return to the relevant task.

- [ ] **Step 1:** Purity audit (all AI path functions):

```bash
grep -n "performance\.now\|Date\.now\|Math\.random\|\.mesh\b" \
  /Users/andrewamisola/Projects/Volleybolt/index.html \
  | grep -Ev "predictZAtX|buildAISingleView|applyCombatantInput|\/\/"
```

Expected: zero hits for `decideAI` and all pure helpers (`_aiFindUrgentThreat`, `_aiSafeToStartCast`, etc.).

- [ ] **Step 2:** Reproducibility assertion in the browser:

```js
// Same (view, frame, seed, params) must produce identical output.
const v  = buildAISingleView();
const i1 = decideAI(v, 200, makeAIRng(200 ^ AI_RNG_SEED), DEFAULT_AI_PARAMS);
const i2 = decideAI(v, 200, makeAIRng(200 ^ AI_RNG_SEED), DEFAULT_AI_PARAMS);
console.assert(JSON.stringify(i1) === JSON.stringify(i2), 'FAIL: decideAI not reproducible');
console.log('decideAI reproducibility: PASS', i1);
```

- [ ] **Step 3:** AI oracle final check:

```js
const r = window.dbg.aiDeterminism(50, 42);
console.assert(r.fold === '<AI_GOLDEN>', 'AI oracle FAIL: ' + r.fold);
console.assert(r.reproducible === true, 'AI oracle not reproducible');
console.log('dbg.aiDeterminism: PASS', r.fold);
```

- [ ] **Step 4:** Sim oracle final check. VERIFY(golden=`b1df6797`). Assert:

```js
const a = dbg.determinism(180, 12345);
const b = dbg.determinism(180, 12345);
const c = dbg.determinism(180, 999);
console.assert(a.fold === b.fold, 'not reproducible');
console.assert(a.fold === 'b1df6797', 'sim oracle FAIL: ' + a.fold);
console.assert(a.fold !== c.fold, 'not seed-sensitive');
console.log('dbg.determinism: PASS', a.fold);
```

- [ ] **Step 5:** Parity smoke — play through a full singles match and confirm:
  - AI intercepts and returns incoming projectiles.
  - AI casts fireball, frostbolt, and thunderstorm (observe cast events).
  - AI parries (deterministic, no dice-roll; confirm via console or visual).
  - Match completes to a win or loss state without JS errors.

- [ ] **Step 6:** Confirm the only surviving `Math.random` in `index.html` is the doubles-AI `predictZAtX` (out of scope):

```bash
grep -n "Math\.random" /Users/andrewamisola/Projects/Volleybolt/index.html
```

Expected: exactly one hit, in the doubles-AI path.

- [ ] **Step 7:** Append a dated entry to `docs/agents/gameplay-combat.md` (newest at top, append-only):

```
- 2026-06-29 · Phase 2.1: deterministic singles AI — decideAI (pure), buildAISingleView (mesh boundary), applyCombatantInput (shared). Deleted tryAIParry, AI_PREDICTION_ERROR, performance.now think-gate. AI oracle pinned at <AI_GOLDEN>. Sim oracle b1df6797 unchanged. · Open: doubles AI Math.random (predictZAtX, deferred to 2.3); applyCombatantInput parry arm still reads mesh (deferred to 2.3 when SP routes through sim state).
```

---

## Post-plan state

After Task 6, the singles AI:
- Is fully deterministic and oracle-tested (`dbg.aiDeterminism`).
- Emits the same input vocabulary as a human player.
- Has its input applied through `applyCombatantInput`, which is the future shared path for both AI and human player (Step 2.3).
- Has no `Math.random`, `performance.now`, `Date.now`, or mesh reads in its decision logic.
- Leaves `js/sim.js` and the `b1df6797` sim oracle completely untouched.

**Phase 2.3 (engine unification):** route single-player through `simulateNetworkFrame`; replace `buildAISingleView`'s mesh reads with sim-state reads; route human player input through `applyCombatantInput`; remove the doubles AI `Math.random` in `predictZAtX`.
