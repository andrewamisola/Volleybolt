# Overdrive Beam Visual ("Kamehameha pass") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the v1 placeholder beam (single box + tiny flash) with the full Kamehameha effect: 0.6s charge-orb windup, three-row beam body (white core / team mid / deep glow = the blockable band), muzzle crackle, ramp-scaled impact blob + FF8 pillars when connecting, deflection flare when blocked, screen shake, phase-locked audio.

**Architecture:** ONE small sim change (windup phase, derived from `juiceTimer` — no new state fields, no hash change) in `js/sim.js`; everything else is presentation in `index.html` (`updateMatchPresentation` + the existing `_overdriveBeam_*` lazy-mesh pattern + Tone.js). Spec: `docs/superpowers/specs/2026-07-06-overdrive-beam-visual-design.md` — read it first; its §2–§6 carry the anatomy, colors, and tunables.

**Tech Stack:** Babylon.js meshes/materials (emissive+additive), Tone.js, the deterministic sim.

## Global Constraints

- Touch ONLY `index.html` and `js/sim.js`; bump the sim.js `?v=` cache-bust whenever js/sim.js changes.
- Presentation reads sim state (`juiceActive`/`juiceTimer`/`juiceRamp`/paddle positions), NEVER writes it.
- Windup derivation (the only sim logic): `windingUp = (OD.DURATION - c.juiceTimer) < OD.WINDUP`. No new combatant fields.
- GLOW row height stays LOCKED to `2 × OVERDRIVE.BLOCK_TOL` (compute from the constant, don't hardcode 1.8).
- Symmetric both sides; right side colors read `window.TEAM_RIGHT` (colorblind-aware); Reduce Motion (`window._reduceMotion`) skips crackle/jitter/shake/pulse.
- All meshes lazy-created once + reused; no per-frame allocations steady-state; particles/sparks throttled.
- Goldens after the sim task: re-pin `dbg.determinism(180,12345)` (from `19595947`) + record seed-99999; `dbg.aiDeterminism(50,42)` must stay `5afbc1a6`. Controller runs browser checks.
- Audio loops are edge-triggered + state-driven per side (the casting-loop-bug discipline): start/stop from observed sim state in presentation, never inside resim.

---

### Task 1: Sim windup phase + windup-only interrupt

**Files:** Modify: `js/sim.js` (`tickOverdrive`, vaporize block in `updateNetworkProjectiles`), `index.html` (OVERDRIVE const, frostbolt `onPaddleHit` interrupt block, cache-bust, oracle golden comment).

**Interfaces:** Produces `OVERDRIVE.WINDUP = 0.6` (window + `ctx.consts.overdrive`), and the derived-phase convention `windingUp = (DUR - juiceTimer) < WINDUP` that Tasks 2–5 read presentation-side.

- [ ] Add `WINDUP: 0.6,` to the `OVERDRIVE` const in index.html (comment: seconds of charge-up before the beam exists — no damage/ramp/disintegration, and the ONLY window in which frostbolt can interrupt; TUNABLE).
- [ ] In `tickOverdrive` (js/sim.js): after the timer drain, derive `const windingUp = (OD.DURATION - c.juiceTimer) < (OD.WINDUP || 0);` and wrap the ENTIRE connect/ramp/damage section in `if (!windingUp) { ... } else { c.juiceRamp = 0; }` (defensive fallback `WINDUP: 0.6` added to the OD fallback object).
- [ ] In the vaporize block (js/sim.js `updateNetworkProjectiles`): extend the channeler test to `ch.juiceActive && ((OD.DURATION - ch.juiceTimer) >= (OD.WINDUP || 0))`.
- [ ] **Windup-only interrupt (index.html, frostbolt `behavior.onPaddleHit`):** the existing interrupt block (`if (c.juiceActive) { clear channel... }`) gains the windup gate: only end the channel when `(OVERDRIVE.DURATION - c.juiceTimer) < OVERDRIVE.WINDUP`. The FREEZE APPLIES UNCONDITIONALLY either way (the line above the block is untouched) — a frostbolt landing after eruption freezes the caster (aim pinned: the frozen paddle can't move, tickOverdrive keeps firing at the frozen Z) but does NOT end the channel. Update the block's comment to say exactly that.
- [ ] Bump sim.js cache-bust (v=36-overdrive-windup). `node --check js/sim.js`.
- [ ] Controller: browser unit asserts — (a) tickOverdrive juiceTimer=6 → no damage/ramp; juiceTimer=5 → damages; (b) frostbolt onPaddleHit with juiceTimer=5.8 (windup) → freeze + channel ENDED; (c) with juiceTimer=4 (beaming) → freeze applied + channel STILL ACTIVE; then re-pin goldens ×3 both seeds + AI golden unchanged; update golden history comments (js/sim.js header) + ledger.
- [ ] Commit: `Overdrive: 0.6s windup; frostbolt interrupts ONLY during windup (post-eruption it pins, not ends); re-pin golden`.

### Task 2: Beam body — the three rows

**Files:** Modify: `index.html` — replace the v1 beam block in `updateMatchPresentation` (anchor: `window._overdriveBeam_left`) and its lazy-create.

**Interfaces:** Consumes windup convention (Task 1). Produces per-side `window._overdriveBeam_{left,right}` = `{ core, mid, glow }` meshes (or a root TransformNode) that Tasks 3–4 position against.

- [ ] Rebuild lazy-create: per side, three flattened boxes (heights: core 0.5, mid 1.2, glow `2*OVERDRIVE.BLOCK_TOL`; depth/Y-thickness ~0.35/0.5/0.65), y≈0.5, additive emissive materials — CORE white, MID bright team color, GLOW deep team color; right side derives MID/GLOW from `window.TEAM_RIGHT`. Cache all Color3s.
- [ ] Per-frame update (only while `juiceActive && !windingUp`): position at caster Z; X spans muzzle → endpoint. Endpoint: recompute the sim's own block test read-only (`Math.abs(casterZ - oppZ) <= BLOCK_TOL`) → blocked: opponent paddle X; connecting: opponent gate X (find the gate/tower X the sim uses for scoring — grep the gate constants). Set box scaling/position from length; no allocations.
- [ ] Eruption wipe: first 0.15s after windup ends, length lerps 0→full (derive from `(DUR - juiceTimer) - WINDUP`). End thin: last 0.3s of the channel, core/mid heights scale down. Ramp feedback: CORE height ×(1 + 0.5·juiceRamp/RAMP_TIME); ±2% length jitter on CORE only (skip jitter under `_reduceMotion`).
- [ ] Hide all three on channel end/interrupt (existing setEnabled path). Windup phase: beam hidden (orb only — Task 3).
- [ ] Controller browser check: rows visible/stacked, glow height == 2×BLOCK_TOL, blocked vs connecting endpoint lengths differ, 0 errors. Commit: `Overdrive visual: three-row Kamehameha beam body (core/mid/glow = blockable band)`.

### Task 3: Charge orb, muzzle, crackle

**Files:** Modify: `index.html` (same presentation block).

**Interfaces:** Consumes windup convention + beam meshes. Produces `window._overdriveOrb_{left,right}`.

- [ ] Lazy-create per side: two concentric spheres (white inner d≈0.5, team-color outer d≈0.8, additive, outer alpha 0.7) at the caster's forward hand position (paddle X + dir·0.8, y 0.6, caster Z; track per frame).
- [ ] Windup anim: scale 0.3→1.6 with accelerating pulse over WINDUP (derive progress from `(DUR - juiceTimer)/WINDUP`); at eruption snap to 1.1 and persist as the muzzle core while the beam is live; hide on end/interrupt.
- [ ] Crackle: 4 thin jagged planes (or line meshes) parented near the orb, re-randomized rotation/scale every ~4 frames (`Math.random` is FINE here — presentation only), visible during windup + beam; skipped entirely under `_reduceMotion` (orb still swells, no pulse/crackle).
- [ ] Controller browser check: orb swells during windup with no beam, beam erupts after, crackle animates, reduce-motion static. Commit: `Overdrive visual: charge orb + muzzle + crackle arcs (windup telegraph)`.

### Task 4: Endpoint FX + shake + interrupt collapse + ATMOSPHERE (lights + fog carving)

**Files:** Modify: `index.html` — rework `showOverdriveHitFX` + add blocked-flare + shake + collapse + beam lighting/fog-reaction in the presentation block.

- [ ] **Beam PointLights (spec §2.4):** 2–3 lazy-created team-colored PointLights per side, repositioned per frame along the live beam (muzzle/mid/endpoint), radius+intensity well above the fireball `fireLight_*` pattern (grep `proj.light = new BABYLON.PointLight` for the template); one smaller light on the charge orb during windup (grows with the orb); all disabled with the channel.
- [ ] **Fog carving (spec §2.4):** while the beam is live, on a ~0.15s throttle push `fogCuts` sampled every ~1.5 units along the beam with ±Z lane offsets (grep `window.fogCuts` and the projectile push pattern with FOG_CUT_LIFETIME; use a SHORT maxAge so the lane re-fogs after); feed 2–3 beam entries into the shader `projLights` build (grep `setFloats("projLights")` — append beam lights to the same array, type 1/ice for left-blue, 0/fire for right-red, respecting the 12-light cap and leaving room for real projectiles). No cuts during windup.

- [ ] CONNECTING end: impact blob (two spheres, white in team shell) at the gate endpoint, scale pulsing with juiceRamp; spark bursts (existing spark/zap particle pattern) throttled ~5Hz — fold the current `showOverdriveHitFX` throttle into this; 2–3 vertical light pillars (thin additive planes, 0.4s life, spawn ≤1 per 0.5s) — the FF8 flourish.
- [ ] BLOCKED end: deflection flare at the blocker's paddle face (flattened bright burst mesh, reused) + perpendicular spark spray (throttled); no blob/pillars while blocked.
- [ ] Screen shake: one eruption kick + low sustained rumble while CONNECTING only, amplitude scaled by ramp; use the existing shake helper (grep screen shake / `_reduceMotion` gates around it) and skip under reduce-motion.
- [ ] Interrupt/end collapse: on juiceActive flipping false (track prev state presentation-side per side), scale-collapse beam+orb over ~0.1s + one fizzle burst at the caster; ensure no orphaned meshes/intervals (materials: `mat.dispose()` directly — Materials lack isDisposed() in this Babylon build).
- [ ] Controller browser check: blob grows with ramp when connecting; flare at blocker when blocked; interrupt collapses everything; 0 errors through repeated channels. Commit: `Overdrive visual: impact blob + pillars, deflection flare, shake, interrupt collapse`.

### Task 5: Audio (phase-locked, leak-proof)

**Files:** Modify: `index.html` (Tone.js SFX area — follow the casting-loop state machine pattern, anchor: `_castingDesired`).

- [ ] Windup riser (0.6s pitch/filter sweep, one-shot on channel start), eruption boom (one-shot at windup→beam), beam roar LOOP per side (edge-triggered from observed state in presentation: start when `juiceActive && !windingUp`, stop on end/interrupt — mirror the `_castingDesired` desired-state pattern exactly, including the async-init race guard), quiet deflection crackle while blocked, power-down on interrupt.
- [ ] All through the SFX bus/volume settings; never started during resim (presentation layer never runs in resim anyway — keep the guard consistent with neighbors).
- [ ] Controller browser check: sounds start/stop with phases across channel/interrupt/rematch ×3, no stuck loops. Commit: `Overdrive audio: windup riser, eruption, beam roar loop, deflection, power-down`.

### Task 6: Playtest + tune (user-driven)

- [ ] User plays: telegraph readable? rows == blockable band trustworthy? impact feel? shake too much/little? audio mix?
- [ ] Tune spec §6 knobs; re-pin golden only if WINDUP (sim) changes.
- [ ] Fold results into the Overdrive as-built note (with the mechanic tuning from the prior plan's Task 8).
- [ ] Commit: `Overdrive visual: tuning pass`.

## Self-Review

**Spec coverage:** §1 windup→Task 1; §2.1 orb/crackle→Task 3; §2.2 rows/ramp/eruption→Task 2; §2.3 endpoints→Task 4; §2.4 shake/interrupt→Task 4; §3 audio→Task 5; §5 acceptance→controller checks + Task 6. ✓
**Placeholders:** visual tasks reference the existing v1 code as the integration anchor by name and give dimensions/colors/timings from the spec; no TBDs. ✓
**Type consistency:** windup derivation formula identical in Tasks 1–3; `_overdriveBeam_*`/`_overdriveOrb_*` names consistent; GLOW height always computed from BLOCK_TOL. ✓
