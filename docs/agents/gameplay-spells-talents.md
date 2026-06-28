# Agent · Spells & talents  ·  Gameplay pillar

**Owns.** The spell registry (fire/ice/lightning), loadouts, the HotS-style talent tree, ultimates.

**Reports into** → [Gameplay pillar](../pillars/gameplay.md) · also reads [Shared Core](../SHARED_CORE.md)

## Grounded in (external canon)
- [Babylon.js docs home](https://doc.babylonjs.com/)

## Internal docs
- `docs/SPELL_REGISTRY.md` _(author + maintain)_
- `docs/TALENTS.md` _(author + maintain)_

## Invariants
- Spells are defined as data; upgrades link by ability id.
- No un-synced randomness in spell effects.

## Working log
_Append-only. Newest at top. Each entry: date · decision/change · open issues._

- _(start here)_

---
_[Gameplay pillar](../pillars/gameplay.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
