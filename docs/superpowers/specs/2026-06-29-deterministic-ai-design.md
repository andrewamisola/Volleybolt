# Deterministic Singles AI — Design Spec (Phase 2, Step 2.1)

**Date:** 2026-06-29
**Status:** Draft for Director review
**Author:** Claude (with Andrew)
**Depends on:** Phase 1 ability registry (`ABILITY_REGISTRY` / `getAbilityDef`), the extracted deterministic sim (`js/sim.js`), the `dbg.determinism` oracle (golden seed 12345 → `b1df6797`), and the project **game-design-philosophy** memory (no randomness; depth from deterministic interaction).

---

## 1. Problem

The single-player AI is non-deterministic and structurally separate from the deterministic engine:

- Think-gating uses `performance.now()/1000` with a wall-clock `AI_THINK_INTERVAL=0.22` — two runs of the same match sequence can gate differently depending on real elapsed time.
- All AI decisions read live Babylon mesh positions (`proj.mesh.position`, `aiPaddle.position`, `playerPaddle.position`) directly. Mesh state is presentation state, not sim state. This means the AI cannot be tested without a rendering context.
- `tryAIParry` seeds its `deterministicValue` from a raw float mesh-Z (~line 11335), making it effectively non-reproducible for any scripted oracle.
- The AI fires the private helpers `startCasting('ai',...)`, `castFrostbolt('ai')`, `executeThunderstorm('ai')`, and `parryProjectile(...)` directly — it bypasses the input vocabulary that a human player uses and that the multiplayer sim understands.
- Dead constant `AI_PREDICTION_ERROR` (~line 11363) exists but is never read.

The result: single-player and multiplayer are two separate game-play engines that diverge whenever an ability changes. Phase 2 aims to unify them. Step 2.1 is the required precondition: make the AI deterministic and input-emitting before the engine unification (Step 2.3) folds everything together.

## 2. Goal

Rewrite the singles AI as a **pure deterministic function** that models a **virtual player** — it observes a pure-data view of the game, emits the same `{moveDir, parry, fireball, frostbolt, thunderstorm}` input struct that a human player uses, and has that input applied through the same path a human player's input follows. The AI is literally a player controlled by code, not a special subsystem with private mutation rights.

**Behavioral goal:** parity with today's AI strategy (threat detection, cast conditions, juice timing, parry reflex) with two deliberate, documented deviations described in §5. No difficulty system in 2.1 — but `params` is designed so difficulty is a later call-site change, not a code rewrite.

**Scope:** singles (`updateGameLogic`). Does not touch the doubles AI, does not route single-player through `simulateNetworkFrame`, does not touch `js/sim.js`.

## 3. The virtual-player model

A human player's input cycle is:

```
observe game state  →  decide what to do  →  emit {moveDir, parry, fireball, frostbolt, thunderstorm}  →  game applies it
```

The virtual-player AI follows the same cycle:

```
buildAISingleView()  →  decideAI(view, frame, rng, params)  →  applyCombatantInput(combatant, input, dt)
```

Every component has a single responsibility and a hard contract:

| Component | Responsibility | Side-effects allowed |
|---|---|---|
| `buildAISingleView()` | Translate mesh/SP-authority state into a pure plain object | Yes — the ONLY place meshes are read |
| `decideAI(view, frame, rng, params)` | Pure strategy: view + frame → input | None — no I/O, no mutation |
| `applyCombatantInput(c, input, dt)` | Apply an input struct to a combatant under player rules | Yes — mutates combatant, calls cast helpers |

This separation means `decideAI` can be tested without a browser, and swapping `buildAISingleView` for a sim-state reader in Step 2.3 leaves `decideAI` completely unchanged.

## 4. Component specifications

### 4.1 `decideAI(view, frame, rng, params)` → input

**Signature:**
```js
function decideAI(view, frame, rng, params)
// Returns: { moveDir: -1|0|1, parry: bool, fireball: bool, frostbolt: bool, thunderstorm: bool }
```

**Purity contract:** no `performance.now`, `Date.now`, `Math.random`, or `.mesh` access anywhere in the function body or any helper it calls. Variety (if any) comes from `rng`, which is integer-seeded.

**`view` shape** (produced by `buildAISingleView`):
```js
{
  projectiles: [
    { id: int, x: number, z: number, velX: number, velZ: number,
      owner: 'player'|'ai', volleyCount: int, type: string }
  ],
  self: {
    paddleX: number, paddleZ: number,
    mana: number,
    cooldowns: { fireball: number, frostbolt: number, thunderstorm: number },
    freezeTime: number,        // >0 means frozen
    casting: string|null,      // 'fireball'|'frostbolt'|'thunderstorm'|null
    juice: number,
    juiceActive: bool,
    shieldCharges: int
  },
  opp: { paddleZ: number },
  geom: { tableWidth: number, halfDepth: number, paddleBoundary: number },
  roundActive: bool
}
```

**`frame`**: integer fixed-step frame counter maintained by the SP loop. Incremented once per sim tick. Think cadence: `frame % K === 0` where `K = Math.round(AI_THINK_INTERVAL / FIXED_DT)` (≈ 13 at 60 Hz, 0.22 s interval). On non-think frames, `decideAI` returns the cached last output — it does not re-compute.

**`rng` helper** (integer-seeded, passed in):
```js
// Constructed before calling decideAI; call-site owns the seed.
// seed is derived deterministically, e.g. fold of (projId XOR actionIndex XOR AI_SEED_CONST).
function makeAIRng(seed) {
  let s = seed | 0;
  return function aiRng() {
    s = (Math.imul(1664525, s) + 1013904223) | 0;
    return (s >>> 0) / 0xFFFFFFFF;  // [0,1)
  };
}
```

`rng` is only used inside `decideAI` if a truly stochastic-feeling decision is required and cannot be eliminated by design. In 2.1 the parry dice-roll is removed (§5), so `rng` is threaded through but may go unused — it is present for the difficulty system in a future step.

**`params` shape** (explicit skill factors, defaulted to skilled/parity values):
```js
// Default: high-skill, parity with today's AI strategy.
const DEFAULT_AI_PARAMS = {
  reactionFrames:     0,    // extra frames of lag before a decision takes effect (difficulty knob)
  aimError:           0,    // max Z-offset error on cast targeting (difficulty knob, in world units)
  parryTimingError:   0,    // extra frames before parry fires (difficulty knob)
  castAggression:     1.0,  // multiplier on cast-readiness threshold (1.0 = normal, <1 = more conservative)
  thinkIntervalK:    13,    // think cadence in frames (K = round(AI_THINK_INTERVAL / FIXED_DT))
};
```

All values default to skilled/parity in 2.1. Difficulty levels are introduced later by passing a different `params` object — `decideAI` does not branch on a difficulty enum, it reads numeric factors.

**Strategy logic** (behavior-parity with today's AI, except as noted in §5):

- **Movement:** compute target Z from `findUrgentThreat(view)` or `findOpenTarget(view)`. If `|targetZ - self.paddleZ| > 0.25`, set `moveDir = Math.sign(targetZ - self.paddleZ)`. Otherwise `moveDir = 0`. No variable speed — that is applied by `applyCombatantInput` at player speed only.
- **Cast readiness gate** `safeToStartCast`: `true` iff no projectile with `velX > 0` (i.e. heading toward the AI's side) is currently in flight.
- **Fireball:** emit `fireball: true` if `safeToStartCast && self.cooldowns.fireball <= 0 && self.mana >= fireballCost && projectiles.length < 10 && !isOppBlocking(view) && self.casting === null`.
- **Frostbolt:** same gates as fireball, substituting frostbolt cost/cooldown.
- **Thunderstorm:** emit `thunderstorm: true` if `self.cooldowns.thunderstorm <= 0 && self.mana >= thunderstormCost && incomingProjectileCount(view) >= 2`.
- **Juice:** emit the juice input flag when `self.juice >= MAX_JUICE && !self.juiceActive`.
- **Parry:** emit `parry: true` deterministically when a projectile is within parry range on the think frame. No probability roll (§5).

Internal helpers (pure, no mesh):
- `findUrgentThreat(view)` — closest projectile where `velX > 0` (heading toward AI); returns its `z`, or `null`.
- `findOpenTarget(view)` — Z-position away from `opp.paddleZ` (open lane targeting); returns a number.
- `isOppBlocking(view)` — `|self.paddleZ - opp.paddleZ| < 1.5`.
- `incomingProjectileCount(view)` — count of projectiles heading toward AI side.

### 4.2 `buildAISingleView()` → view

**Signature:**
```js
function buildAISingleView()
// Returns: the view object (shape above). Reads live SP authority.
```

**Contract:** the ONLY function in the AI path that touches meshes. It translates the present Babylon mesh positions and SP combatant state into a pure plain object. Nothing downstream reads `.mesh`.

**What it reads:**
- `aiPaddle.position.x/z`, `playerPaddle.position.z` (mesh positions — accepted here only)
- `projectiles` array: each `proj.mesh.position.x/z`, `proj.velX`, `proj.velZ`, `proj.owner`, `proj.volleyCount`, `proj.id`, `proj.type`
- `combatants.right`: `mana`, `cooldowns`, `freezeTime`, `casting`, `juice`, `juiceActive`, `shieldCharges`
- Game constants: `TABLE_WIDTH`, `HALF_DEPTH`, `PADDLE_BOUNDARY`, `roundActive`

**Why this boundary matters:** in Step 2.3, when SP routes through `simulateNetworkFrame`, this function is replaced with one that reads `simState.projectiles[i].x/z` instead of `proj.mesh.position.x/z`. `decideAI` never changes.

### 4.3 `applyCombatantInput(c, input, dt)`

**Signature:**
```js
function applyCombatantInput(c, input, dt)
// c: combatant object (combatants.right for AI in 2.1)
// input: { moveDir, parry, fireball, frostbolt, thunderstorm, juice }
// dt: fixed timestep in seconds
// Returns: void. Mutates c and invokes cast/parry helpers under player rules.
```

**Contract:** interprets the canonical input struct against combatant `c` using player rules. The AI routes through this in 2.1. The human player routes through this in 2.3. There is no branching on "is this the AI or the player" — the rules are the same.

**What it does:**
- **Movement:** if `freezeTime <= 0`, move along Z by `moveDir * AI_SPEED * dt`, clamped to `[-PADDLE_BOUNDARY, +PADDLE_BOUNDARY]`. Uses `AI_SPEED` (the existing `aiSpeed = 20`) at full 1.0x — no urgency multiplier (§5).
- **Parry:** if `input.parry` is true and a projectile is within parry range, call `parryProjectile(...)`.
- **Fireball:** if `input.fireball` is true, call `startCasting('ai', 'fireball')` (subject to the game's existing cast-start guards, which enforce the same mana/cooldown checks as the decision logic).
- **Frostbolt:** if `input.frostbolt` is true, call `castFrostbolt('ai')`.
- **Thunderstorm:** if `input.thunderstorm` is true, call `executeThunderstorm('ai')`.
- **Juice:** if `input.juice` is true, activate juice.

The cast helpers (`startCasting`, `castFrostbolt`, `executeThunderstorm`) already contain their own guards. `applyCombatantInput` does not duplicate them — it calls them the same way the player keydown handlers do.

### 4.4 Adapter (wiring)

Replace the inline AI block at `updateGameLogic` ~lines 12124–12250 and the `tryAIParry` call at ~12628 with:

```js
// SP frame counter must be in scope (see Step (a) of the plan).
const aiView  = buildAISingleView();
const aiInput = decideAI(aiView, spFrameCounter, getAIRng(), aiParams);
applyCombatantInput(combatants.right, aiInput, dt);
```

`getAIRng()` constructs a fresh `makeAIRng` seeded from a deterministic fold of the current frame and a fixed `AI_RNG_SEED` constant.

## 5. Two deliberate deviations from strict behavior parity

These are honest deviations: the old behaviors were **AI-only mechanics** that a human player could never replicate. They are removed in favor of the real difficulty controls that will replace them.

### Deviation 1 — Movement speed

**Old behavior:** variable speed multiplier of 0.6–1.0x depending on urgency, applied only to the AI.

**New behavior:** AI moves at full player speed (1.0x) via `moveDir`. No urgency multiplier.

**Rationale:** a human player cannot slow themselves down by urgency. The urgency-speed coupling was fake "imperfection" that did not model a real skill axis. Real reaction-time imperfection returns as the `reactionFrames` param (future difficulty step), which delays the action taken, not the speed it is executed at.

### Deviation 2 — Parry probability

**Old behavior:** `tryAIParry` rolled a probability dice (85%/75%/50%/35%) seeded from a float mesh-Z — effectively non-reproducible and not a modeled skill axis.

**New behavior:** AI presses parry deterministically whenever a projectile is in parry range on a think frame. No dice roll.

**Rationale:** a human player either presses parry or does not — there is no hidden probability weight on their input. The dice roll was fake randomness masquerading as skill variance. Real parry imperfection returns as the `parryTimingError` param (future difficulty step), which shifts the frame window the AI "sees" the parry opportunity.

### What is kept

All strategic thresholds are kept at parity: `safeToStartCast`, `findUrgentThreat`, `findOpenTarget`, `isOppBlocking`, `incomingProjectileCount >= 2` for thunderstorm, juice activation threshold, projectile count cap. The AI makes the same reads and the same strategic calls — just through a clean, testable, deterministic interface.

## 6. What is removed

| Item | Location | Reason |
|---|---|---|
| `performance.now()/1000` think-gate | ~line 12125 | Replaced by `frame % K === 0` |
| `AI_THINK_INTERVAL = 0.22` constant | ~line 11362 | Absorbed into `params.thinkIntervalK` |
| `tryAIParry` (float-seeded) | ~lines 11332–11349 | Replaced by deterministic parry in `decideAI` |
| `AI_PREDICTION_ERROR` constant | ~line 11363 | Never read; deleted |
| Inline AI block | ~lines 12124–12250 | Replaced by adapter (§4.4) |

## 7. Determinism strategy

`decideAI` is pure: same `(view, frame, rng, params)` → identical output every time. It has no side-effects, accesses no globals, reads no wall-clock.

The `frame` argument is an integer fixed-step counter (`spFrameCounter`), incremented once per sim tick in `updateGameLogic`. It is never tied to `performance.now`. This replaces the wall-clock think-gate with a reproducible frame-parity gate.

The `rng` helper is integer-seeded (LCG). The seed is derived from `(spFrameCounter ^ AI_RNG_SEED)` using bitwise ops only — no floats, no wall-clock. The same frame + seed always produces the same RNG stream.

`buildAISingleView` is the mesh-reading boundary. It is NOT pure (it reads live Babylon state), but it is the ONLY non-pure component. Everything downstream of it is pure. In Step 2.3 this function is swapped; `decideAI` stays untouched.

`applyCombatantInput` is effectful (it mutates combatants and calls cast helpers) but it is deterministic — the same input + combatant state + dt always produces the same mutation sequence. It contains no wall-clock reads, no `Math.random`.

The existing sim oracle `dbg.determinism(180, 12345)` → `b1df6797` is unaffected: this step does not touch `js/sim.js`.

## 8. Scope boundaries

**In scope (2.1):**
- Singles AI only (`updateGameLogic`, right-side combatant).
- The three new functions: `decideAI`, `buildAISingleView`, `applyCombatantInput`.
- Deleting the old inline AI block, `tryAIParry`, and the dead constants listed in §6.
- Adding `spFrameCounter` to the SP loop.
- Adding `dbg.aiDeterminism` as a testable AI oracle.

**Out of scope (later steps):**
- Difficulty UI / difficulty levels — `params` is designed for it, but the UI is not built here.
- Doubles AI and its `Math.random` in `predictZAtX` — that is a separate subsystem, explicitly out of scope.
- Routing human player input through `applyCombatantInput` — that is Step 2.3 (engine unification).
- Routing SP through `simulateNetworkFrame` — that is Step 2.3.
- Touching `js/sim.js` in any way — the sim oracle golden must not be disturbed.

## 9. Verification and acceptance criteria

### 9.1 Purity check (grep, no browser needed)
```bash
grep -n "performance\.now\|Date\.now\|Math\.random\|\.mesh\b" index.html \
  | grep -A0 "decideAI\|buildAIRng\|makeAIRng\|findUrgentThreat\|findOpenTarget\|isOppBlocking"
```
Expected: zero hits inside `decideAI` and the pure AI helpers. `buildAISingleView` is explicitly excluded from this check (it is the mesh boundary).

### 9.2 decideAI reproducibility (browser console)
```js
const v = buildAISingleView();
const r1 = decideAI(v, 100, makeAIRng(100 ^ AI_RNG_SEED), DEFAULT_AI_PARAMS);
const r2 = decideAI(v, 100, makeAIRng(100 ^ AI_RNG_SEED), DEFAULT_AI_PARAMS);
console.assert(JSON.stringify(r1) === JSON.stringify(r2), 'decideAI must be reproducible');
```

### 9.3 AI determinism oracle (`dbg.aiDeterminism`)
A new `dbg.aiDeterminism(steps, seed)` helper folds `decideAI` outputs over a fixed scripted sequence of synthetic views (no meshes, no browser state) into a 32-bit hash. It is runnable headlessly (no game loop needed). After pinning, the same call must always return the same value. The golden value is determined on first run and recorded in the commit and the working log.

```js
// Example call:
window.dbg.aiDeterminism(50, 42) // → pin this value in the commit
```

### 9.4 Sim oracle unchanged
`dbg.determinism(180, 12345)` must still return `b1df6797`. Run before and after the adapter swap. If it changes, STOP — something touched sim state.

### 9.5 Parity smoke (headless/visual)
- AI intercepts incoming projectiles (movement reaches threat Z).
- AI casts fireball and frostbolt under the same conditions as before (console log the cast events).
- AI parries (deterministically, no console dice-roll).
- AI does not freeze after the inline block is deleted (no broken references).
- Match completes to a win/loss state normally.
