# Overdrive Beam — Visual & Feel Design Spec ("Kamehameha pass")

**Date:** 2026-07-06
**Status:** Draft for owner review
**Author:** Claude (with Andrew)
**Depends on:** the Overdrive mechanic (branch `juice-overdrive`, Tasks 1–7 complete: `tickOverdrive` in `js/sim.js`, presentation hooks in `index.html`). This spec REPLACES the v1 placeholder visual (single stretched box + tiny hit flash) with the real effect. Gameplay numbers (DoT ramp, BLOCK_TOL, charge table) are unchanged except one addition: a **0.6s windup**.

**References (user-supplied):**
- DBZ Kamehameha (perler render): the canonical anatomy — charge orb at the hands with crackle arcs, a layered beam (white-hot core inside colored sheath inside glow), a bulbous impact end.
- FF8 Zell limit break: PS1-era pillar-of-light impact — stacked translucent planes, gold wash, additive glow. Matches our PS1/storybook direction.
- Modern beam (cyan): energy density at the MUZZLE and the IMPACT, with the beam itself clean and readable between them. Particles hug the endpoints, not the whole beam.

**The one gameplay-honesty rule (user-stated):** the **three-row beam body IS the blockable band.** Total visual height of core+mid+glow in Z ≈ `2 × BLOCK_TOL` (1.8 world units). If your paddle covers the rows, you are safe. Everything wider/flashier (sparks, flares, pillars) is dressing and must READ as dressing.

---

## 1. Sim change (the only one): windup

- New constant `OVERDRIVE.WINDUP = 0.6` (seconds).
- The 6s channel now = **0.6s windup + 5.4s beam**. The phase is **derived, not stored**: `windingUp = (DURATION - juiceTimer) < WINDUP`. No new state fields → no hash/snapshot changes.
- During windup: **no damage, no ramp, no fireball disintegration** (the beam doesn't exist yet — only the orb). The caster can move (aiming). Frostbolt interrupt works throughout (freeze already ends the channel at any point).
- `tickOverdrive` gates its connect/damage block on `!windingUp`; the vaporize check in `updateNetworkProjectiles` gates on the same derivation.
- Deterministic (pure arithmetic on existing state). Sim golden re-pins once (from `19595947`); AI golden `5afbc1a6` unaffected.
- Why 0.6s: long enough to read the telegraph and step into the lane from ~1 lane away; short enough that the ult still feels explosive. TUNABLE in the playtest.

## 2. Visual anatomy (presentation-only, per side)

All meshes lazy-created once per side and reused (enable/disable, never per-frame allocation). All materials emissive + additive, `renderingGroupId 1` (above floor, with characters). Colors from the team palette with a shared white-hot core:

| Layer | Blue (left) | Red (right) | Z-height (world) |
|---|---|---|---|
| CORE (white-hot) | `#FFFFFF` | `#FFFFFF` | 0.5 |
| MID | bright team blue `#0078F8` | bright orange-red `#F87800`-ish | 1.2 |
| GLOW | deep blue `#0000BC` | deep red `#A81000`-ish | **1.8 = 2×BLOCK_TOL** |

(Exact hexes snapped to the NES palette at implementation; the right side reads `window.TEAM_RIGHT` so colorblind mode's orange swap applies automatically.)

### 2.1 Charge orb (windup star, persists as muzzle)
- Two concentric spheres at the caster's hands (paddle X ± forward offset, y≈0.6, caster's Z): white inner + team-color outer (additive, alpha ~0.7).
- Over the 0.6s windup: scales 0.3 → 1.6 with an accelerating pulse (it *swells*). On beam eruption it snaps to ~1.1 and stays as the **muzzle core** for the whole beam.
- **Crackle arcs**: 3–5 short jagged line/plane meshes around the orb, re-randomized every few frames (presentation-side randomness is allowed), FF8/DBZ zigzag energy. Skipped under Reduce Motion (orb still swells, no crackle/pulse).

### 2.2 Beam body — the three rows
- Three flattened boxes stacked in Z (heights per the table), y≈0.5, spanning X from the muzzle to the **endpoint** (§2.3). Length set per frame; the body tracks the caster's Z every frame (the sweep is the aim).
- CORE: slight lengthwise scale-jitter (±2%, per-frame) so it feels alive; MID/GLOW steady. Jitter off under Reduce Motion.
- **Ramp feedback:** as `juiceRamp` grows 0 → RAMP_TIME, CORE height scales ×1.0 → ×1.5 and the orb/impact pulse faster — the beam visibly "digs in" the longer it connects. Blocked (ramp reset) → instantly back to base. This makes the block/connect state readable from the beam itself.
- Eruption (first ~0.15s after windup): the three rows scale out from the muzzle to full length (fast wipe), not a pop-in.

### 2.3 Endpoints
- **Connecting (off-lane opponent):** the beam runs full length to the opponent's gate line. There: an **impact blob** — white sphere in a team-color shell (the DBZ bulb), scale pulsing with `juiceRamp` (bigger = more damage/sec) + spark bursts flying outward (reuse the existing spark/zap particle pattern, throttled ~5Hz like the current hit flash) + 2–3 short-lived vertical light pillars (FF8 flourish, thin additive planes, ~0.4s life). Damage is already visible via the health bar; the blob is the "it's working" read.
- **Blocked (lane-matched):** the beam terminates AT the blocker's paddle in a **deflection flare** — a bright flattened burst hugging the paddle face, sparks spraying perpendicular (up/down in Z), the beam length visibly SHORT. Reads as "I am holding it." No damage FX beyond the flare.
- Endpoint X each frame: blocked → blocker's paddle X; connecting → opponent gate X. The block decision is READ from the same test the sim uses (|casterZ − oppZ| vs BLOCK_TOL) — presentation recomputes it read-only, it never writes.

### 2.4 Impact feel (cheap, gated)
- **Screen shake:** a subtle sustained rumble while the beam is CONNECTING (amplitude scaling slightly with ramp), one sharper kick on eruption. Uses the existing screen-shake helper; fully skipped under Reduce Motion.
- **Interrupt (frostbolt):** beam + orb collapse instantly (scale-in over ~0.1s), a brief fizzle burst at the caster, then the existing freeze FX takes over. No lingering meshes.
- **Natural end (timer):** beam thins out over the last ~0.3s (read the timer), then off.

## 3. Audio (Tone.js, presentation-only)

- **Windup:** rising whoosh/shimmer over 0.6s (pitch/filter sweep).
- **Beam:** a roar loop while the beam is live. **Edge-triggered per side and state-driven** — same discipline as the casting-loop fix: start on (channel live && !winding), stop on end/interrupt, never gated on isResimulating for state, never started during resim. Both sides can roar simultaneously (two channels or shared with refcount).
- **Eruption:** one boom at windup→beam transition. **Deflection:** crackle while blocked (or reuse spark SFX at low volume). **Interrupt:** the existing freeze sound already lands; add a short power-down.
- Volumes through the SFX bus (Settings-respecting).

## 4. Constraints (unchanged laws)

- **Presentation reads, never writes**: everything in §2–3 reads `juiceActive` / `juiceTimer` / `juiceRamp` / paddle positions / TEAM colors only.
- **Symmetry:** identical anatomy both sides; only palette differs.
- **Perf:** all meshes created once and reused; particles throttled; zero per-frame allocations in the steady state (cache Color3s/Vector3s, use `.set()`/`copyFrom`).
- **Reduce Motion:** no crackle, no jitter, no shake, no pulse — beam/orb/flare render static.
- **MP:** all of it runs in `updateMatchPresentation` positionally (left combatant → left-side FX), no `getLocalSide` branching.

## 5. Acceptance

1. Windup: press Q → orb swells 0.6s with crackle → beam erupts wide. Opponent sees the same telegraph (MP: sync stays green; sim golden re-pinned once, reproducible ×3, AI golden unchanged).
2. The three rows are unmistakable (white core / team mid / deep glow) and their total height visually matches the blockable band — standing "on" the beam rows = blocked, confirmed in play.
3. Blocked: beam visibly stops at the blocker with the deflection flare; connecting: full-length beam + growing impact blob + pillars; ramp growth is readable (core widens, pulses faster).
4. Interrupt: frostbolt freeze collapses the whole effect instantly, no orphaned meshes/sounds.
5. Sound starts/stops exactly with the phases; no loop leaks (the Tone.js casting-loop bug class).
6. 0 console errors through repeated channels, rematches, and MP; Reduce Motion honored; no visible perf hit at 60fps.

## 6. Tunables (starting points)

```
OVERDRIVE.WINDUP        = 0.6      // s (sim; the only gameplay addition)
BEAM_HEIGHTS            = { core: 0.5, mid: 1.2, glow: 1.8 }   // glow == 2*BLOCK_TOL, keep locked to it
ORB_SCALE               = 0.3 -> 1.6 (windup), 1.1 (muzzle)
RAMP_CORE_SCALE         = 1.0 -> 1.5 across RAMP_TIME
ERUPTION_WIPE           = 0.15s;  END_THIN = 0.3s;  COLLAPSE = 0.1s
IMPACT_SPARK_THROTTLE   = ~5Hz;   PILLAR_LIFE = 0.4s
SHAKE                   = eruption kick + low sustained rumble (ramp-scaled)
```
