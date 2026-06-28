# Agent · Physics  ·  Engine pillar

**Owns.** Havok — the ball, paddle, parry/block collisions, restitution tuning.

**Reports into** → [Engine pillar](../pillars/engine.md) · also reads [Shared Core](../SHARED_CORE.md)

## Grounded in (external canon)
- [Using the Havok plugin](https://doc.babylonjs.com/features/featuresDeepDive/physics/havokPlugin)
- [Physics engine v2 deep dive](https://doc.babylonjs.com/features/featuresDeepDive/physics/usingPhysicsEngine)
- [Havok runtime repo](https://github.com/BabylonJS/havok)

## Internal docs
- `docs/PHYSICS.md` _(author + maintain)_

## Invariants
- Havok is a WASM module — await HavokPhysics() before the plugin is usable.
- Requires WASM SIMD; unsupported on iOS < 16.4 — gate or provide a fallback.
- Use PhysicsAggregate for setup. The CDN build is dev-only, not production.
- Step physics on the fixed timestep, or rollback breaks.

## Working log
_Append-only. Newest at top. Each entry: date · decision/change · open issues._

- _(start here)_

---
_[Engine pillar](../pillars/engine.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
