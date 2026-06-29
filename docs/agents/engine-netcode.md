# Agent · Netcode  ·  Engine pillar

**Owns.** Rollback, PeerJS transport, input prediction, snapshots, seeded-RNG sync, disconnect handling, ping indicator. Highest-risk agent — a determinism bug is silent until it desyncs a match.

**Reports into** → [Engine pillar](../pillars/engine.md) · also reads [Shared Core](../SHARED_CORE.md)

## Grounded in (external canon)
- [GGPO (canonical rollback model)](https://www.ggpo.net/)
- [Rollback architecture (SnapNet)](https://www.snapnet.dev/blog/netcode-architectures-part-2-rollback/)
- [Deterministic lockstep (Gaffer on Games)](https://gafferongames.com/post/deterministic_lockstep/)
- [Preparing a game for deterministic netcode](https://yal.cc/preparing-your-game-for-deterministic-netcode/)
- [PeerJS docs](https://peerjs.com/docs/)
- [PeerJS repo](https://github.com/peers/peerjs)
- [WebRTC data channels (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Using_data_channels)

## Internal docs
- `docs/NETCODE.md` _(author + maintain)_

## Invariants
- Sticky-input prediction by default; correct on real input arrival.
- Keep per-frame sim cost low — N rollback frames re-simulate N times inside one 16.6ms frame (the 'spiral of death').
- Seed the RNG as a synced input. Never branch sim logic on un-synced data.

## Working log
_Append-only. Newest at top. Each entry: date · decision/change · open issues._

- 2026-06-29 · Step 2.2 Task C code edits (C.1–C.9, CODE only — lead owns browser validation / G3 pin / version bump / commit). js/sim.js: added pure `simActivateJuice(combatant, ctx)` (guard juiceActive/juice<MAX → false; set juice=MAX, juiceActive, juiceTimer=DURATION, reset ALL cooldowns once, FX via deps.onJuiceActivate gated by !isResimulating); juice drain loop at top of `simulateNetworkFrame` (drains unconditionally even while frozen, clears + deps.onJuiceEnd at ≤0); juice activation from input after parry processing; auto-parry burst in BOTH paddle blocks (after Lightning-Shield, before onPaddleHit) — REFLECT only (`D.parryProjectile(proj, side, 0); continue;`), no toDestroy/no extra sound. index.html: frostbolt+thunderstorm cast-charge via `window.addJuice(combatant, JUICE.CHARGE.cast)` in their registry onCast; SIM_DEPS onJuiceActivate/onJuiceEnd → window.onJuiceStart/onJuiceEnd + logJuice/logCombat. node-check (sim.js + extracted inline) pass; purity grep clean (only comment hits). · Open / plan deviations flagged to lead: (1) C.4 — did NOT add the blanket charge hook in tryNetworkCast: fireball already charges once via the shared completeCasting→fireFireball (line 17771, already in G2), so a tryNetworkCast charge would DOUBLE fireball. Matched SP per-ability instead (fireball=unchanged, frostbolt/thunderstorm charge in onCast). Oracle casts frostbolt (f%71) so G2→G3 still changes legitimately via frostbolt charge, not via a double-charge bug. (2) C.6 — fireball burst NOT added to behavior.onCast: fireball is castType 'channel' (onCast only starts the channel, no proj exists there); the 6-tier burst already lives in the shared `spawnFireball` (index.html ~10490-10502, reached by the sim via completeCasting→fireFireball→spawnFireball), so no edit needed/possible. (3) C.5/C.7 — SP code does NOT push parried projectiles to toDestroy nor add an extra playSound (parryProjectile reflects + sounds itself), and onJuiceStart already does tint+'juiceUp'+drone, so the plan's toDestroy/playSound/_juiceTint/playSample('juiceUp') extras were dropped to match SP exactly. (4) auto-parry aimDir forced to 0 (neutral) for determinism — SP reads keys[]/AI findOpenTarget there, which is not sim-safe. (5) sim drain loop does state only; SP's per-frame aura wobble/tint-reassert (updateJuice ~1739-1771) is cosmetic and still driven by SP's untouched updateJuice — MP lacks the wobble until a future onJuiceTick dep (no determinism/behavior impact).
- 2026-06-29 · Step 2.2 Task B code edits (B.1–B.7): added pure `simAddJuice` + `resolveNetworkProjVsProj(ctx, toDestroy)` to js/sim.js (frostbolt cancel + fireball overpower/mutual-cancel, proj.x/z only, FX via deps gated by !isResimulating); called it once after the per-projectile loop in updateNetworkProjectiles; added 3 FX deps (onFrostboltCancel/onOverpower/onProjCancel) to SIM_DEPS; added juice/juiceActive/juiceTimer to hashGameState (deliberate golden change → lead re-baselines G2). node-check (sim.js + extracted inline) pass; purity grep clean (only comment hits). · Open: gate-collision is INSIDE the per-proj loop, so resolve runs after gate hits this frame, not before (plan/handoff assumed gate was a separate later pass) — flagged to lead, no observed correctness impact (collisions are mid-court, gate at x=14). FX wrappers wrap into BABYLON.Vector3 because createImpactFlash(copyFrom)/showCombatTextAt(clone) require it; plan's plain {x,y,z} would have thrown. Browser validation / golden pin / commit owned by lead (B.8–B.16).
- _(start here)_

---
_[Engine pillar](../pillars/engine.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
