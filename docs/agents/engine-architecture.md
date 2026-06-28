# Agent · Architecture  ·  Engine pillar

**Owns.** Decomposition of the ~20k-line index.html into js/ modules, load order, perf budget. First job: finish the migration already started (config, audio, ui, rendering, systems).

**Reports into** → [Engine pillar](../pillars/engine.md) · also reads [Shared Core](../SHARED_CORE.md)

## Grounded in (external canon)
- [Scene optimization](https://doc.babylonjs.com/features/featuresDeepDive/scene/optimize_your_scene)
- [Babylon.js docs home](https://doc.babylonjs.com/)
- [Babylon API (TypeDoc)](https://doc.babylonjs.com/typedoc/)

## Internal docs
- `docs/ARCHITECTURE.md` _(author + maintain)_
- `docs/MODULE_BOUNDARIES.md` _(author + maintain)_

## Invariants
- No new global without registering it in ARCHITECTURE.md.
- Module boundaries are contracts — other pillars import, never reach in.

## Working log
_Append-only. Newest at top. Each entry: date · decision/change · open issues._

- _(start here)_

---
_[Engine pillar](../pillars/engine.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
