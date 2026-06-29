# Agent · Combat  ·  Gameplay pillar

**Owns.** The combatant system (the spine of the game), the match loop, win/lose states.

**Reports into** → [Gameplay pillar](../pillars/gameplay.md) · also reads [Shared Core](../SHARED_CORE.md)

## Grounded in (external canon)
- [Babylon.js docs home](https://doc.babylonjs.com/)

## Internal docs
- `docs/COMBAT.md` _(author + maintain)_

## Invariants
- Combatant state is fully serializable and deterministic.

## Working log
_Append-only. Newest at top. Each entry: date · decision/change · open issues._

- 2026-06-29 · Phase 2.1 spec + plan authored — deterministic singles AI design (decideAI pure function, buildAISingleView mesh boundary, applyCombatantInput shared input applier, 6-task oracle-gated implementation plan). Removed performance.now think-gate, float-seeded tryAIParry, and AI_PREDICTION_ERROR from scope. Two deliberate behavior deviations documented (movement speed, parry probability). dbg.aiDeterminism oracle specified. Sim oracle b1df6797 preserved. · Open: doubles AI Math.random (predictZAtX) deferred to 2.3; applyCombatantInput parry arm will still read mesh in 2.1 (deferred to 2.3); difficulty params designed but not wired.

---
_[Gameplay pillar](../pillars/gameplay.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
