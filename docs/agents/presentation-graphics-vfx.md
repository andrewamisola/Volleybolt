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

- 2026-06-29 · Re-drove SP-only presentation after Step 2.3-C routed singles through the deterministic sim: added `updateSinglePlayerPresentation(dt)` (index.html ~12026) called from `runSinglePlayerFrame` after `simulateNetworkFrame`. Rewired: cast bars (2-D + 3-D + show/hide, ~12032-12056), paddle targetRotY + moveDir from `lastMoveDir` (~12062-12085), player footstep SFX with boundary guard (~12087-12108), ice-block freeze visuals + shatter-on-expire (~12110-12133), cooldown + mana UI at stepped rate (~12135-12140), per-projectile trail anchor + blob shadow + fireball/frostbolt flicker/glow + loop-sound pan/pitch + approach SFX (~12142-12209). FX-only confirmed: zero writes to proj.x/z/velX/velZ, paddleZ, mana, cooldowns, casting, castProgress, freezeTime. Syntax-checked with node --check. · Open: `proj.collisionGraceTime` is never decremented in the new SP path (the sim reads it for proj-vs-proj collision gating but does not tick it — a pre-existing sim gap that affects split-projectile self-collision); fix belongs in js/sim.js when that path is exercised. Frostbolt trail in PvP also undriven (pre-existing gap, separate scope).
- 2026-06-28 · Fixed PvP match camera showing old menu angle: `resetCameraToDefault`/`flipCameraForClient` set GAME_CAMERA alpha/beta/radius but didn't stop the in-flight menu/talent camera animation (started by showTalentScreen, ~1s smooth tween toward MENU_CAMERA / target (-10,1.5,0)), which kept driving the camera every frame after the snap. Added `cam.getScene().stopAnimation(cam)`+`stopAnimation(cam.target)` to both helpers (mirrors single-player's doReadyGoTransition). Visual-only, no sim feedback; single-player path untouched. · Open: orchestrator to verify live window.gameCamera values in PvP vs SP match; opponent-name exchange still TODO.
- _(start here)_

---
_[Presentation pillar](../pillars/presentation.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
