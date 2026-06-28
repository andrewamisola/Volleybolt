# Agent · Graphics & VFX  ·  Presentation pillar

**Owns.** Scene render, post-processing stack, shaders, particles, CRT overlay, NES palette, PS1/affine texture look.

**Reports into** → [Presentation pillar](../pillars/presentation.md) · also reads [Shared Core](../SHARED_CORE.md)

## Grounded in (external canon)
- [Particle system](https://doc.babylonjs.com/features/featuresDeepDive/particles/particle_system/particles)
- [Post-processes](https://doc.babylonjs.com/features/featuresDeepDive/postProcesses/usePostProcesses)
- [Materials / shaders](https://doc.babylonjs.com/features/featuresDeepDive/materials)

## Internal docs
- `docs/ART_DIRECTION.md` _(author + maintain)_

## Invariants
- Visual-only — particles, post, and shaders never feed back into sim state.

## Working log
_Append-only. Newest at top. Each entry: date · decision/change · open issues._

- 2026-06-28 · Fixed PvP match camera showing old menu angle: `resetCameraToDefault`/`flipCameraForClient` set GAME_CAMERA alpha/beta/radius but didn't stop the in-flight menu/talent camera animation (started by showTalentScreen, ~1s smooth tween toward MENU_CAMERA / target (-10,1.5,0)), which kept driving the camera every frame after the snap. Added `cam.getScene().stopAnimation(cam)`+`stopAnimation(cam.target)` to both helpers (mirrors single-player's doReadyGoTransition). Visual-only, no sim feedback; single-player path untouched. · Open: orchestrator to verify live window.gameCamera values in PvP vs SP match; opponent-name exchange still TODO.
- _(start here)_

---
_[Presentation pillar](../pillars/presentation.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
