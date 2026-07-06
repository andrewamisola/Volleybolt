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
- During windup: **no damage, no ramp, no fireball disintegration** (the beam doesn't exist yet — only the orb). The caster can move (aiming).
- **Interrupt rule (CHANGED from the mechanic spec, user decision 2026-07-06): frostbolt only interrupts during the WINDUP.** Land a frostbolt on the caster while the orb is charging → freeze + full interrupt (channel ends, juice lost — the hard punish). **Once the beam has erupted, it is uninterruptible**: a frostbolt that hits the beaming caster still applies its normal FREEZE (it is never disintegrated), which **pins the beam's aim** — the frozen caster can't move, so the beam can't chase; the opponent can hold the lane or reposition freely until the freeze ends. Freeze during the beam = "pin it", not "end it". (This supersedes §5 of `2026-07-05-juice-overdrive-beam-design.md`, which allowed interrupt at any time.)
- `tickOverdrive` gates its connect/damage block on `!windingUp`; the vaporize check in `updateNetworkProjectiles` gates on the same derivation; the frostbolt-freeze interrupt block gates on `windingUp`.
- Deterministic (pure arithmetic on existing state). Sim golden re-pins once (from `19595947`); AI golden `5afbc1a6` unaffected.
- Why 0.6s: long enough to read the telegraph and land a reactive frostbolt or step into the lane; short enough that the ult still feels explosive. TUNABLE in the playtest — it is now ALSO the entire interrupt window, so tune with that in mind.

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

### 2.3 Endpoints (REVISED from first playtest, 2026-07-06)
- **Connecting (off-lane opponent):** the beam runs full length to the opponent's gate line. There: an **impact blob** — white sphere in a team-color shell (the DBZ bulb), scale pulsing with `juiceRamp` + spark bursts flying outward + 2–3 short-lived vertical light pillars (FF9 flourish, thin additive planes, ~0.4s life).
  **Damage beats (playtest feedback: "boom boom boom"):** the sim's smooth per-tick drain is too subtle to read. Presentation ACCUMULATES the opponent's observed towerHealth delta while the beam connects and delivers it in discrete beats every ~0.6s: a floating damage number (the accumulated chunk), a health-bar pulse, an impact-blob scale KICK, and a boom SFX (§3). Sim damage stays continuous (no gameplay change) — only the feedback is quantized.
  **NO FX on the opponent's body/paddle while connecting** — the damage is to the GATE; effects on the player read as nonsense (the v1 yellow paddle flash is REMOVED, confirmed confusing in playtest).
- **Blocked (lane-matched) — parry-style chromatic block (playtest feedback):** while the opponent successfully blocks, their SHIELD gets a **persistent chromatic-aberration treatment** — the RGB-split/shake effect the parry already uses (reuse the existing parry chromatic-shake helpers) running CONTINUOUSLY, plus the shield/paddle **violently vibrating** (small high-frequency positional jitter on the shield VISUAL only, never the sim paddle) with sparks spraying perpendicular. The beam length is visibly SHORT (stops at the blocker). Reads as "I am holding this thing back with everything I have." Reduce Motion: chromatic + vibration off, replaced by a steady bright shield glow.
- Endpoint X each frame: blocked → blocker's paddle X; connecting → opponent gate X. The block decision is READ from the same test the sim uses (|casterZ − oppZ| vs BLOCK_TOL) — presentation recomputes it read-only, it never writes.

### 2.4 Atmosphere: the beam is PHYSICAL light (user addition 2026-07-06)

The beam must interact with the arena atmosphere the same way a fireball does, scaled up:

- **Scene lighting:** fireballs carry a `PointLight` (`proj.light`, the `fireLight_*` pattern). The beam gets **2–3 PointLights spaced along its length** (muzzle / midpoint / endpoint), team-colored, with a **much larger radius and higher intensity** than a fireball's — the court, wizards, and walls should visibly glow while it fires. Lights are lazy-created once per side, repositioned per frame along the live beam, disabled with it.
- **Reactive fog — the beam CARVES the fog:** the fog plane's shader already reacts to projectiles via `fogCuts` (carved holes that age out) and `projLights` (up to 12 shader lights, fire/ice typed). While the beam is live:
  - push `fogCuts` sampled along the FULL beam length (every ~1.5 units, with ±Z offsets covering the beam's lane width), on a throttle (~every 0.15s, short maxAge) so the lane stays carved open while firing and the fog rolls back in afterward — a clear channel of visibility where the beam burned through;
  - feed 2–3 entries into the shader's `projLights` along the beam (type: ice-blue for the left/blue beam, fire for the right/red beam) so the surrounding fog GLOWS team-colored around the carved lane.
  - Respect the existing caps (12 shader lights, fog-cut cap) — the beam must not evict all projectile trail cuts; keep its per-push count modest.
- Windup: the charge orb alone gets ONE growing PointLight + a small fog glow (no cuts yet — the fog carves only when the beam erupts, which reads as the eruption's shockwave).
- All presentation-only, driven from the beam block; skipped cleanly on channel end/interrupt (lights off, cuts age out naturally).

### 2.5 Impact feel (cheap, gated)
- **Screen shake:** a subtle sustained rumble while the beam is CONNECTING (amplitude scaling slightly with ramp), one sharper kick on eruption. Uses the existing screen-shake helper; fully skipped under Reduce Motion.
- **Interrupt (frostbolt during WINDUP only):** orb collapses instantly (scale-in over ~0.1s), a brief fizzle burst at the caster, then the existing freeze FX takes over. No lingering meshes.
- **Frozen mid-beam (frostbolt after eruption):** the beam KEEPS FIRING but its aim is pinned — visually, the existing freeze FX plays on the caster while the beam continues at the frozen Z (no special beam change needed; the aim simply stops tracking because the sim stops the paddle). Optionally tint the crackle ice-blue during the freeze if trivial.
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
4. Interrupt: a frostbolt during the WINDUP collapses the whole effect instantly (freeze + channel lost), no orphaned meshes/sounds. A frostbolt AFTER eruption freezes the caster but the beam keeps firing, aim pinned, until the freeze ends or the channel expires.
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
