# Volleybolt — Project Master

Single front door to the project. **A new AI reads this file first**, then drills down:
master → pillar → agent. Each level links down to its children and up to its parent, so the
hierarchy is walkable from any node.

## What it is
A 3D wizard volleyball / spell-dueling game. Single-page build (`index.html`) on Babylon.js,
with P2P rollback multiplayer.

## Stack
- **Engine/render:** Babylon.js + Havok physics (WASM)
- **Netcode:** PeerJS (WebRTC) + custom rollback
- **Audio:** Tone.js (synthesized)
- **UI:** Babylon GUI + DOM + NES.css

## The law
Read **[Shared Core](docs/SHARED_CORE.md)** before anything. Short version: the sim is
deterministic and fixed-timestep because of rollback — no un-synced randomness, ever.

## Hierarchy
**Director (Andrew)** owns vision, cross-pillar calls, and anything touching the determinism law.
Below sit four pillars, each with its own agents:

### [Engine — _How it runs_](docs/pillars/engine.md)
The load-bearing plumbing: architecture, deterministic netcode, and physics. A bug here breaks every other pillar.
- [Architecture](docs/agents/engine-architecture.md)
- [Netcode](docs/agents/engine-netcode.md)
- [Physics](docs/agents/engine-physics.md)
### [Gameplay — _What you do_](docs/pillars/gameplay.md)
The rules of play — combatants, spells, talents, and balance. Mostly grounded in internal design docs, not libraries.
- [Combat](docs/agents/gameplay-combat.md)
- [Spells & talents](docs/agents/gameplay-spells-talents.md)
- [Balance](docs/agents/gameplay-balance.md)
### [Presentation — _See & hear_](docs/pillars/presentation.md)
Everything the player sees and hears. One creative voice across graphics, UI, and audio — protect the PS1/FF9/WKW feel.
- [Graphics & VFX](docs/agents/presentation-graphics-vfx.md)
- [UI / UX](docs/agents/presentation-ui-ux.md)
- [Audio](docs/agents/presentation-audio.md)
### [Production & Live — _Ship & maintain_](docs/pillars/production.md)
Build, release, QA, and post-launch operation. The pillar that runs the game once it stops being built.
- [Build & release](docs/agents/production-build-release.md)
- [QA](docs/agents/production-qa.md)
- [Live ops](docs/agents/production-live-ops.md)

## How the docs work
- **Agent doc** — one per sub-agent. Holds its grounding (external canon + internal docs) and an
  append-only **Working Log**. The agent reads its canon, does the work, logs decisions here.
- **Pillar doc** — one per pillar. Aggregates its agents' status into a **Pillar State** table so
  agents share context within the pillar. The pillar lead keeps it current.
- **Master (this file)** — the map. Director-maintained. Links every pillar; never holds detail
  that belongs in a pillar or agent doc.

## Onboarding a new AI
1. Read this master + [Shared Core](docs/SHARED_CORE.md).
2. Identify the pillar your task lives in; read its pillar doc (incl. Pillar State).
3. Open the specific agent doc; read its canon and Working Log before writing code.
4. Log your decisions back into that agent's Working Log; surface status to the Pillar State.
