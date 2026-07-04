# Singles AI Behavior Rethink — Design Spec

**Date:** 2026-07-04
**Status:** Draft for Director review
**Author:** Claude (with Andrew)
**Depends on:** the deterministic singles AI (`decideAI` / `buildAISingleView`, Phase 2 Step 2.1), the unified SP engine (`runSinglePlayerFrame` → `simulateNetworkFrame`, Step 2.3), and the project **symmetry principle** memory (player & AI fully symmetric; difficulty = AI *competence*, never stat crutches).

---

## 1. Problem

The singles AI is **too good for an average player**, and the fix so far has made it worse to reason about.

The root cause is architectural, not a mistuning: `decideAI` computes the **mathematically perfect** defensive answer and then degrades it with additive error.

- It leads the ball to its exact impact point through wall bounces (`_reflectZ` + `timeToImpact` + `BLOCK_ARC` projection).
- It instantly classifies frostbolt-vs-fireball to dodge.
- It auto-panic-casts thunderstorm the instant `incomingCount ≥ 2`.
- Difficulty is then applied as noise on top of that perfect player: `aimError` (per-ball positional noise), `reactionFrames` (view lag), `parryTimingError` (whiff dice), `castAggression` (skip-cast dice).

Two consequences:

1. **Its mistakes feel random, not human.** A perfect player throwing on a dice roll reads as cheap, not beatable.
2. **The knobs have drifted into sediment.** `DEFAULT_AI_PARAMS` is five hand-tuned values, each compensating for a side-effect of the last (`aimError 0.85→1.4`, `parryTimingError 0.25→0.4`, `castAggression 0.65→0.55`, `thinkIntervalK 13→22`, `reactionFrames 9→5`). Every retune fights the others.

## 2. Goal

Rebuild the singles AI so its imperfection is **emergent from how it plays**, not sprinkled on a perfect player. The AI should behave like a human: it *watches and chases the ball* rather than solving for its future, and it makes recognizably human mistakes (wrong-footed by fast/bounced shots, occasionally freezing itself on a frostbolt it read too late).

Difficulty collapses to a **single competence scalar** `skill ∈ [0,1]`, read fresh every frame, that modulates *everything* through one tuning curve. Today it is a constant ("average"); it is authored as a seam so it can later be driven dynamically (e.g. a clutch/comeback ramp) without a rewrite.

**Hard invariant (symmetry principle):** competence may change *how well* the AI perceives and decides. It may **never** grant extra speed, mana, cooldown reduction, faster cast time, or more damage. A clutching AI plays *better*, never *stronger*.

**Scope:** singles only (`decideAI`, `runSinglePlayerFrame`, `skillToProfile`, `getAISkill`, and the `dbg.aiDeterminism` oracle). Does **not** touch the doubles AI, `simulateNetworkFrame`, `buildAISingleView`'s contract, or `js/sim.js` semantics.

## 3. Architecture

### 3.1 The one seam

At the top of `runSinglePlayerFrame`, difficulty resolves through a single chain:

```
skill   = getAISkill()            // scalar in [0,1], read fresh every frame
profile = skillToProfile(skill)   // pure: scalar → concrete behavior values
rightInput = decideAI(view, spFrameCounter, rng, profile)
```

| Component | Responsibility | Purity |
|---|---|---|
| `getAISkill()` | Return the current competence scalar. Today: constant `AI_SKILL_AVERAGE`. The ONLY difficulty input. | Impure by design (future: reads match state). The single dynamic seam. |
| `skillToProfile(skill)` | Map the scalar to concrete behavior values `decideAI` consumes. The single tuning curve. | Pure. |
| `decideAI(view, frame, rng, profile)` | Track-&-chase strategy: view + profile → input struct. | Pure — no wall-clock, no `.mesh`, no `Math.random`. |

`decideAI` never sees `skill`, only the derived `profile`. Tuning lives in exactly one inspectable place (`skillToProfile`), replacing the five drifting knobs.

### 3.2 `getAISkill()`

```js
// getAISkill() — the ONLY difficulty input. Returns skill ∈ [0,1].
// Today: constant AI_SKILL_AVERAGE (0.45 — deliberately eased; "too good" was the complaint).
// Future (documented, NOT built this pass): dynamic competence, e.g.
//   skill = clamp(AI_SKILL_AVERAGE + clutchBonus(scoreDeficit), 0, 1)
// INVARIANT: clutch may only raise COMPETENCE (this scalar). It must never grant
// speed/mana/cooldown/cast-time/damage — see skillToProfile's symmetry banner.
const AI_SKILL_AVERAGE = 0.45;
function getAISkill() { return AI_SKILL_AVERAGE; }
```

### 3.3 `skillToProfile(skill)` — the single tuning curve

Pure function. Returns ONLY competence values. Higher skill → sharper perception and decisions. Exact curves are tuned from playtests; the table gives the shape and direction (values illustrative, `skill=0` easiest → `skill=1` hardest):

```js
// ┌──────────────────────────────────────────────────────────────────┐
// │ SYMMETRY BANNER: this function may return ONLY competence values —  │
// │ perception lag, tracking tightness, sight windows, decision cadence.│
// │ It must NEVER return a multiplier on speed, mana, cooldown, cast    │
// │ time, or damage. Difficulty = how well the AI plays, never how      │
// │ strong it is. (See project symmetry-principle memory.)              │
// └──────────────────────────────────────────────────────────────────┘
function skillToProfile(skill) {
  const s = Math.max(0, Math.min(1, skill));
  return {
    reactionFrames:   Math.round(lerp(12, 2, s)),  // view-history depth: acts on an older world at low skill
    trackDeadzone:    lerp(1.1, 0.34, s),           // looser tracking (parks roughly) at low skill
    dodgeSightFrames: Math.round(lerp(18, 3, s)),   // must "see" a frostbolt this long before committing to dodge
    parrySight:       Math.round(lerp(14, 2, s)),   // frames a threat must be visible before parry fires
    castCadence:      Math.round(lerp(10, 2, s)),   // safe/idle think-cycles required before committing a cast
    thunderstormSkill: s,                            // gate: recognizes the multi-projectile panic-clear at high s
  };
}
```

> `lerp(a, b, t) = a + (b - a) * t`. Endpoints are starting guesses; the shape (monotonic, easier at `s=0`) is the contract, the exact numbers are tuned.

## 4. Behavior specification (`decideAI`)

### 4.1 Movement — track & chase

**Removed:** `_reflectZ`, the `timeToImpact` lead computation, the `BLOCK_ARC` impact-point projection, and the per-ball `aimError` noise.

**New:**
- Find the most urgent incoming threat: closest projectile with `velX > 0` and `owner !== 'ai'` (unchanged from `_aiFindUrgentThreat`).
- Non-frostbolt threat → steer toward the ball's **current** `z`:
  `moveDir = (|threat.z − self.paddleZ| > profile.trackDeadzone) ? sign(threat.z − self.paddleZ) : 0`.
- No threat → idle reposition toward the open lane only when meaningfully out of place (keep `_aiFindOpenTarget` with its existing `>1.5` guard).

Because movement runs at **player speed** (via `moveDir` through the shared sim) and chases *where the ball is*, fast/steep/bounced shots physically outrun the paddle. Imperfection is emergent.

**Perception degradation (skill, not output noise):**
- `reactionFrames` — the view fed to `decideAI` is `reactionFrames` old (mechanism already exists in `runSinglePlayerFrame`'s `aiViewHistory`; its depth now comes from `profile.reactionFrames`). Low skill acts on a stale world → late starts, wrong-footed by re-angled balls.
- `trackDeadzone` — low skill tracks loosely; high skill tightly.

### 4.2 Frostbolt dodge — sight-based read

**Removed:** instant classify-and-dodge.

**New:** the AI must observe an incoming frostbolt (a threat with `type === 'frostbolt'` and `velX > 0`) for `profile.dodgeSightFrames` consecutive think-cycles before it commits to dodging to the opposite half (`targetZ = threat.z >= 0 ? −halfD*0.5 : halfD*0.5`). Below that threshold it treats the frostbolt like any incoming ball and tries to block it — and gets frozen. Low skill's long sight window → frequently frozen (punishable human mistake); high skill → reliable dodge.

The consecutive-sight counter is tracked per-projectile-id in `decideAI`-local state (see §6 determinism note) or reconstructed from the threat's travelled distance — implementation detail resolved in the plan; both are pure and deterministic.

### 4.3 Offense — skill-driven cadence

**Removed:** the `castAggression` per-cycle `rng` dice.

**New:** the AI commits to an offensive cast only after it has held a safe + idle + in-position state for `profile.castCadence` think-cycles (a "settle" window). Cast *choice* is unchanged and stays (sound reasoning any player uses):
- Frostbolt preferred when the opponent is blocking / directly in front (freezes them).
- Otherwise fireball, subject to existing guards (`safe`, cooldown, mana, `projectiles.length < 10`, not already casting, opponent not blocking for fireball).

Low skill needs a long uninterrupted settle window → sparse offense, misses openings. High/clutch skill → short window → presses advantage.

### 4.4 Thunderstorm — competence, not reflex

**Removed:** auto-fire on `incomingCount ≥ 2`.

**New:** thunderstorm fires on a genuine multi-projectile crunch (`incomingCount ≥ 2`, cooldown ready, `mana ≥ 2`) **only when `profile.thunderstormSkill` clears a threshold** (e.g. `≥ 0.6`). Low skill under-uses/mistimes it; high/clutch skill uses it as a real panic-clear.

### 4.5 Parry — perception-gated press

**Removed:** the `parryTimingError` whiff dice.

**New:** press parry when a threat is within parry range (`|threat.z − self.paddleZ| < parryRange`, `parryRange = 2.5`) **and** it has been visible for `profile.parrySight` frames (via the same reaction-lagged view). Whiffs on fast parries emerge from late perception, not a probability roll. High skill catches tight windows; low skill sees them late.

### 4.6 Juice

Unchanged: emit `juice` when `self.juice >= JUICE.MAX && !self.juiceActive`.

## 5. De-bloat ledger

| Removed | Location (approx.) | Replaced by |
|---|---|---|
| `DEFAULT_AI_PARAMS` (5 knobs + comment sediment) | ~12322 | `getAISkill()` + `skillToProfile()` |
| `_reflectZ` | ~12375 | (nothing — track & chase needs no bounce math) |
| lead / `timeToImpact` / `BLOCK_ARC` block | ~12405–12423 | current-position tracking (§4.1) |
| per-ball `aimError` noise | ~12420 | emergent miss from player-speed chase |
| `castAggression` roll | ~12466 | `castCadence` settle window (§4.3) |
| `parryTimingError` roll | ~12482 | `parrySight` perception gate (§4.5) |
| thunderstorm auto-fire on `≥2` | ~12472 | `thunderstormSkill` gate (§4.4) |

**Added:** `getAISkill()`, `skillToProfile(skill)`, track-&-chase movement, sight-based dodge, cadence offense, sight-gated parry.

## 6. Determinism

- `decideAI` stays pure: no `performance.now` / `Date.now` / `Math.random` / `.mesh`. `skill` and `profile` are plain-data inputs.
- `rng` is **kept threaded** through the signature (integer-seeded LCG) even though all dice are removed — harmless, ready for a future human-plausible tiebreak. It goes unused in this pass.
- Per-projectile sight counters (§4.2/§4.5): if `decideAI` needs to remember "how long have I seen projectile X," that state must be reconstructable purely (e.g. keyed off projectile id + its travelled distance / velocity, not a mutable closure that breaks replay). The plan will pick the pure formulation; no wall-clock, no `Math.random`.
- `buildAISingleView` (mesh boundary) and `simulateNetworkFrame` (symmetric application) are untouched.
- `dbg.aiDeterminism(steps, seed)` is updated to pass a **fixed** profile (`skillToProfile(0.45)`) so the oracle is difficulty-stable; its golden hash is re-pinned on first run and recorded in the commit + working log.
- The sim oracle `dbg.determinism(180, 12345)` must be unchanged (this pass does not touch `js/sim.js`). Run before/after; if it moves, STOP.

## 7. Scope boundaries

**In scope:** singles `decideAI` rewrite; `getAISkill` + `skillToProfile`; wiring in `runSinglePlayerFrame`; removals in §5; `dbg.aiDeterminism` re-pin.

**Out of scope (later):**
- Dynamic/clutch `getAISkill()` — only the seam + documented shape ship now.
- A difficulty-picker UI / named levels — the scalar makes it trivial later, but no menu work here.
- Doubles AI and its `predictZAtX` `Math.random`.
- `simulateNetworkFrame` / `js/sim.js` semantics.

## 8. Verification & acceptance criteria

### 8.1 Purity (grep, no browser)
Zero hits for `performance.now` / `Date.now` / `Math.random` / `.mesh` inside `decideAI`, `skillToProfile`, and the pure AI helpers. `buildAISingleView` and `getAISkill` are excluded (mesh boundary / dynamic seam).

### 8.2 `decideAI` reproducibility (console)
```js
const v = buildAISingleView(), p = skillToProfile(0.45);
const a = decideAI(v, 100, makeAIRng(100 ^ AI_RNG_SEED), p);
const b = decideAI(v, 100, makeAIRng(100 ^ AI_RNG_SEED), p);
console.assert(JSON.stringify(a) === JSON.stringify(b), 'decideAI must be reproducible');
```

### 8.3 AI determinism oracle
`dbg.aiDeterminism(50, 42)` returns a stable pinned hash across runs (re-pinned this pass since behavior changed).

### 8.4 Sim oracle unchanged
`dbg.determinism(180, 12345)` still returns `b1df6797`.

### 8.5 Behavior smoke (playtest)
- AI blocks slow straight shots (fair) but is beaten by fast / steep / wall-bounced shots (track-&-chase lag is visible).
- AI sometimes blocks a frostbolt and freezes itself at `skill = 0.45` (sight-based dodge failing) — a readable human mistake, not a crash.
- AI casts noticeably less relentlessly than before; offense is punishable.
- Thunderstorm no longer auto-fires the instant 2 balls are incoming at average skill.
- Lowering `AI_SKILL_AVERAGE` toward 0 makes it visibly, coherently worse across ALL axes (movement, dodge, parry, offense) — proving the single-scalar coupling.
- `AI_SKILL_AVERAGE = 0.45` feels fair/winnable for an average player (the acceptance bar; tune from here).

### 8.6 Symmetry audit
Confirm `skillToProfile` returns no speed/mana/cooldown/cast-time/damage value at any `skill`. The AI's paddle speed, mana regen, and cooldowns are identical to the player's at every difficulty.
