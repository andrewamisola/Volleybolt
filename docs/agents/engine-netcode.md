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

- 2026-06-29 · Step 2.2 Task B code edits (B.1–B.7): added pure `simAddJuice` + `resolveNetworkProjVsProj(ctx, toDestroy)` to js/sim.js (frostbolt cancel + fireball overpower/mutual-cancel, proj.x/z only, FX via deps gated by !isResimulating); called it once after the per-projectile loop in updateNetworkProjectiles; added 3 FX deps (onFrostboltCancel/onOverpower/onProjCancel) to SIM_DEPS; added juice/juiceActive/juiceTimer to hashGameState (deliberate golden change → lead re-baselines G2). node-check (sim.js + extracted inline) pass; purity grep clean (only comment hits). · Open: gate-collision is INSIDE the per-proj loop, so resolve runs after gate hits this frame, not before (plan/handoff assumed gate was a separate later pass) — flagged to lead, no observed correctness impact (collisions are mid-court, gate at x=14). FX wrappers wrap into BABYLON.Vector3 because createImpactFlash(copyFrom)/showCombatTextAt(clone) require it; plan's plain {x,y,z} would have thrown. Browser validation / golden pin / commit owned by lead (B.8–B.16).
- _(start here)_

---
_[Engine pillar](../pillars/engine.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
