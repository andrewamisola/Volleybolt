# Pillar · Engine  ·  _How it runs_

**Mission.** The load-bearing plumbing: architecture, deterministic netcode, and physics. A bug here breaks every other pillar.

**Reads** [Shared Core](../SHARED_CORE.md) · **part of** [the master](../../PROJECT.md)

## Agents in this pillar
- [Architecture](../agents/engine-architecture.md) — Decomposition of the ~20k-line index.
- [Netcode](../agents/engine-netcode.md) — Rollback, PeerJS transport, input prediction, snapshots, seeded-RNG sync, disconnect handling, ping indicator.
- [Physics](../agents/engine-physics.md) — Havok — the ball, paddle, parry/block collisions, restitution tuning.

## Shared pillar context
_Context every agent in this pillar needs. The pillar lead keeps this current._

- _(add cross-agent decisions, shared types, naming, gotchas here)_

## Pillar state (rollup)
_Each agent's Working Log rolls up here as a one-line status, so any agent — or a new AI —
gets the whole pillar at a glance without opening every file._

| Agent | Status | Current focus |
|---|---|---|
| [Architecture](../agents/engine-architecture.md) | — | — |
| [Netcode](../agents/engine-netcode.md) | — | — |
| [Physics](../agents/engine-physics.md) | — | — |

---
_[Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
