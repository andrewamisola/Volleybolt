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

- _(start here)_

---
_[Engine pillar](../pillars/engine.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
