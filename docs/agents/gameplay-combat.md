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

- 2026-06-29 · Phase 2.3 spec + plan authored — engine unification: SP routes through simulateNetworkFrame (SP feel wins principle). Seven paddle-return divergences resolved to SP's values (prevPaddleZ momentum, hitbox 2.0, hitOffset 1.25, speed-floor player-side only, unconditional block-mana, cast pushback, parry-state reset). Parry unified onto pvpParryState for both player and AI. runSinglePlayerFrame + buildPlayerInput architecture specified. ~700-line singles duplicate enumerated for deletion in step D. One deliberate golden re-baseline: G3 → G_2.3 after step A. Two acceptance gates: numeric paddle-return tests + SP-feel playtest by lead (required before pinning G_2.3 and before committing the driver swap). Doubles stays on old loop (isDoublesMode), out of scope. prevPaddleZ added to hash/capture/restore. · Open: doubles AI Math.random (predictZAtX, deferred); exact G_2.3 value unknown until lead runs browser oracle after step A.

- 2026-06-29 · Phase 2.2 spec + plan authored — proj-vs-proj (frostbolt cancel, fireball overpower/mutual cancel) and juice/ultimate (drain timers, activation from input, charge hooks at cast/parry/proj-vs-proj/gate-damage, burst effects: auto-parry + 6-tier fireball) designed for port into the deterministic sim. Rollback contract additions specified (juice/juiceActive/juiceTimer in hash/capture/restore). Input shape extended with `juice` boolean. Two deliberate golden re-baselines planned: b1df6797 → G2 (proj-vs-proj fires in oracle + juice in hash) → G3 (cast charge hook fires in oracle run). Correctness gate before each pin. SP duplicates in updateGameLogic remain until 2.3. · Open: SP proj-vs-proj + juice loops removal (2.3); doubles AI Math.random (predictZAtX, 2.3); exact G2/G3 values unknown until the lead runs the browser oracle.

- 2026-06-29 · Phase 2.1 implemented — decideAI (pure, no .mesh/.random/wall-clock), buildAISingleView (sole mesh boundary), applyCombatantInput (shared virtual-player applier), aiCheckParryHits + updateAIParryTimer (dt-ticked, no setTimeout). Deleted tryAIParry, AI_PREDICTION_ERROR, AI_THINK_INTERVAL, aiLastThinkTime, predictZ, findUrgentThreat, isPlayerBlocking. Adapter in updateGameLogic replaces ~130-line inline AI block with 4 lines. AI oracle pinned: dbg.aiDeterminism(50,42) = c542c4ab (reproducible, seed-sensitive). Sim oracle b1df6797 unchanged (js/sim.js not touched). Commit: d3c4790. · Open: doubles AI Math.random (predictZAtX, deferred to 2.3); aiCheckParryHits reads mesh (deferred to 2.3 when SP routes through sim state); thunderstorm in applyCombatantInput calls executeThunderstorm (mana not auto-spent via helper — decideAI guards on mana before emitting thunderstorm:true).

- 2026-06-29 · Phase 2.1 spec + plan authored — deterministic singles AI design (decideAI pure function, buildAISingleView mesh boundary, applyCombatantInput shared input applier, 6-task oracle-gated implementation plan). Removed performance.now think-gate, float-seeded tryAIParry, and AI_PREDICTION_ERROR from scope. Two deliberate behavior deviations documented (movement speed, parry probability). dbg.aiDeterminism oracle specified. Sim oracle b1df6797 preserved. · Open: doubles AI Math.random (predictZAtX) deferred to 2.3; applyCombatantInput parry arm will still read mesh in 2.1 (deferred to 2.3); difficulty params designed but not wired.

---
_[Gameplay pillar](../pillars/gameplay.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
