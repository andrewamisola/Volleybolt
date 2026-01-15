# Tasks - Volleybolt (formerly Wizard Duel Arena / BabylonPong)

## Status Legend
- `[ ]` - Not Started
- `[~]` - In Progress
- `[x]` - Completed
- `[!]` - Blocked/Issue
- `[?]` - Needs Discussion

---

## Game Vision

**Wizard Duel Arena** - 1v1 spell-casting game with Pong DNA

| Layer | Description |
|-------|-------------|
| **Core** | Wizard duel (casting, blocking, mana, multi-projectile) |
| **Round** | 30-60 sec bout, damage to tower = round win |
| **Match** | Tug-of-war across 5 zones, level up between rounds |
| **Progression** | Ability picks / upgrades (bullet-heaven style) |

---

## Phase 1: Core Foundation (Current Priority)

### High Priority - Engine Refactor
| Status | Task | Notes |
|--------|------|-------|
| `[x]` | Multi-projectile system | Array of spells, each with own mesh/particles |
| `[x]` | Tower health system | Destructible brick gates, HP bars |
| `[x]` | Active casting | Press 1 to cast fireball |
| `[?]` | Mana system | Decided to skip - using cooldowns instead |

### Medium Priority - Gameplay Depth
| Status | Task | Notes |
|--------|------|-------|
| `[x]` | Cooldown system | 6 sec fireball cooldown, MOBA-style UI |
| `[~]` | Deflection rewards | Planned: block = cooldown reduction |
| `[x]` | Volley damage scaling | 0 volleys=1dmg, 1-2=2dmg, 3+=3dmg (capped) |
| `[x]` | Basic ability variety | Frost Bolt added (freezes for 1s, no damage) |
| `[x]` | Sound system | Web Audio API, stereo panning, volume slider |

### Low Priority - Polish
| Status | Task | Notes |
|--------|------|-------|
| `[x]` | Textures/theming | Gate textures working, floor optional |
| `[x]` | Wizard models | GLB models working, animations hooked up |
| `[x]` | Tower models | Destructible brick gate walls with arch |
| `[x]` | Loading screen | Shows while models load, fades when ready |
| `[x]` | Character flash on block/parry | Emissive glow effect |

---

## Phase 2: Match Structure (Future)

| Status | Task | Notes |
|--------|------|-------|
| `[ ]` | 5-zone lane system | Tug-of-war progression |
| `[ ]` | Round timer | 30-60 second bouts |
| `[ ]` | Zone transitions | Camera/arena shifts on push |
| `[ ]` | Level-up system | Pick ability/upgrade between rounds |
| `[ ]` | Win condition | Destroy enemy core |

---

## Phase 3: Ability System (Future)

### Offensive Spells
| Status | Spell | Effect |
|--------|-------|--------|
| `[x]` | Fireball | Basic projectile, baseline |
| `[x]` | Frost Bolt | Freezes opponent for 1s, no damage, fast |
| `[ ]` | Lightning | Fast but weak |

### Modifiers
| Status | Modifier | Effect |
|--------|----------|--------|
| `[ ]` | Triple Shot | 3 projectiles, longer cooldown |
| `[ ]` | Piercing | Goes through first block |
| `[ ]` | Homing | Curves toward opponent |

### Utility/Defensive
| Status | Ability | Effect |
|--------|---------|--------|
| `[ ]` | Shield Burst | Temporary block boost |
| `[ ]` | Slow Field | Slows incoming spells |

---

## Phase 4: Intro Sequence (Future)

| Status | Task | Notes |
|--------|------|-------|
| `[ ]` | Classic Pong mode | Start with 2D Atari look |
| `[ ]` | Camera reveal | Rotate to show 3D |
| `[ ]` | Theme fade-in | Fantasy world materializes |

---

## Backlog / Ideas
- Music (ambient, battle intensity)
- Two-player local mode
- Online multiplayer (future)
- Different wizard classes?
- Combo system for rapid deflects?
- More spell types (Lightning, etc.)

---

## Known Bugs

| ID | Status | Description | Steps to Reproduce | Notes |
|----|--------|-------------|-------------------|-------|
| BUG-001 | `[x]` | Game crashes when fireball hits gate | 1. Start round 2. Cast fireball 3. Let it hit gate | Fixed: removed undefined aiDamageDealt/playerDamageDealt vars |
| BUG-002 | `[x]` | Particles disappear when any fireball hits gate | 1. Have multiple fireballs 2. One hits gate 3. Others lose particles | Fixed: shared texture was being disposed, added dispose(false) |

---

## Session 34 Priority Tasks

### GUI Migration (Babylon.js GUI)
| Status | Task | Notes |
|--------|------|-------|
| `[ ]` | Move ALL text to Babylon GUI | Enables CRT/letterbox effects on text |
| `[ ]` | Score display → GUI | Currently HTML |
| `[ ]` | Skills/ability bar → GUI | Currently HTML |
| `[ ]` | Victory/defeat text → GUI | Currently HTML |
| `[ ]` | Headers → GUI | "Your Tower", "Enemy Tower" with wide letter-spacing |
| `[ ]` | HTML tooltips with letterbox spacing | Account for 3:4 letterbox when positioning |

### Floating Combat Text (3D Space)
| Status | Task | Notes |
|--------|------|-------|
| `[ ]` | Render in 3D space like cast bar | Position above cast bar |
| `[ ]` | Remove border, use 60% black bar | No white border |
| `[ ]` | Thicker NES font (bold) | More readable |
| `[ ]` | Spell names on cast | "FIREBALL", "FROSTBOLT" |
| `[ ]` | Status ailments | "FROZEN!" etc |
| `[ ]` | Damage numbers (slightly bigger) | Same 60% black bar style |
| `[ ]` | Cancel notifications | When projectiles cancel each other |
| `[ ]` | Queue system | Stack/offset multiple texts |

### Visual Polish
| Status | Task | Notes |
|--------|------|-------|
| `[ ]` | Fix cast radial swipe on ability bar | Currently hexagon shape, should be circular |
| `[ ]` | Darken ground floor | Shadows not visible enough |
| `[ ]` | Text shadows: duplicate only | No blur, pixel shadow offset |
| `[ ]` | Bold text throughout | |
| `[ ]` | Wide letter-spacing on headers | Improve readability |
| `[ ]` | CRT letterbox consistency | Main menu has it, apply everywhere |

### Projectile Collision Enhancement
| Status | Task | Notes |
|--------|------|-------|
| `[ ]` | Fireball vs Fireball | Damage-based: higher wins, continues; lower destroyed |
| `[ ]` | Explosion + burn mark on cancel | Visual feedback |
| `[ ]` | "CANCEL" text on collision | Floating combat text |
| `[ ]` | Frostbolt cancels (already done) | Verify working |

### Tooltip Fixes
| Status | Task | Notes |
|--------|------|-------|
| `[ ]` | Fix fireball tooltip | Says "1-3 damage" but now 2-5 |
| `[ ]` | Clarify frostbolt cancel mechanics | In tooltip description |

---

## Pending Work (Multiplayer)

| Status | Task | Notes |
|--------|------|-------|
| `[x]` | Fix multiplayer camera (was stuck in menu view) | Added full GAME_CAMERA params to flip/reset functions |
| `[x]` | Fix multiplayer inputs not working | Added `gameState = 'playing'` to startMultiplayerMatch |
| `[x]` | Fix multiplayer UI missing | Added full UI setup (health, mana, abilities) to startMultiplayerMatch |
| `[x]` | Fix UI labels for client perspective | Swap "YOUR TOWER" / "ENEMY TOWER" labels for guest |
| `[ ]` | Fix projectile damage logic for client | Client's projectiles damage wrong towers. Need ownership tracking: projectile should damage opponent's tower regardless of screen position. Currently uses X position which breaks for flipped client view. |
| `[ ]` | Fix camera sometimes flipping incorrectly | Intermittent issue - investigate isHost state |

---

## Pending Work (Talent System)

| Status | Task | Notes |
|--------|------|-------|
| `[~]` | Wire up Pyroblast cast time | `modifyAbility.castTime` not read by casting system |
| `[~]` | Wire up Frostbite onHit | Frostbolt collision doesn't call `onHit` hook |
| `[~]` | Implement Glacial Cascade | Trail positions recorded but no visual/slow effect |
| `[ ]` | Add Tier 2-3 upgrades to UpgradeRegistry | TalentTree references them but definitions missing |

---

## Completed Tasks

### 2026-01-12 Session 33 (Git Recovery)
- [x] Restored all features from sessions 16-32 after git wipe
- [x] Updated model loading for p1/p2 folder structure
- [x] Rebuilt documentation

### 2026-01-09 to 2026-01-11 Sessions 16-32 (Consolidated)
**Balance:**
- [x] Fireball damage: 2 base + volleyCount, max 5 (was 1/2/3)
- [x] Mana per block: 0.5 (was 1.0)
- [x] Parry cooldowns: 0.2s success, 3.0s fail (punishes spam)

**Frostbolt:**
- [x] Cancels enemy projectiles on collision
- [x] Stops mana regen while frozen
- [x] Cancels active casting when hit

**Visuals (D2 Style):**
- [x] Shadow system: light (12,28,-8), darkness 0.15, characters only
- [x] Post-processing: contrast 1.4, saturation 1.2
- [x] Fog: opacity 0.45, height 0.25
- [x] Stepped fading for impacts/decals
- [x] Text shadows: pixel only (no blur)

**Gameplay:**
- [x] Paddle momentum affects ball (0.4 factor)
- [x] Projectile-projectile collision (damage-based, 0.5s grace)
- [x] Magma bomb simplified (8 particles, shorter trail)

**UI/UX:**
- [x] Menu pauses game properly
- [x] Victory/defeat animations loop
- [x] NES floating combat text (black bars, queue, stepped)

**Multiplayer:**
- [x] Client W/S controls inverted
- [x] Freeze text shows for both players
- [x] Rollback netcode

**Models:**
- [x] Per-player folders (p1, p2, p3, p4)
- [x] Dynamic path loading based on player side

### 2026-01-09 Session 15
- [x] HotS-style in-game talent system (replaces pre-game selection)
- [x] TalentTree data structure (tiers 1-3, branching choices per ability)
- [x] TalentState tracking (upgrade points, selected talents per ability)
- [x] Upgrade indicator badges on ability slots (golden pulsing ⬆)
- [x] Upgrade points HUD (⭐ X at top center)
- [x] Talent panel UI (click ability to expand, tier progression, choice cards)
- [x] Award 1 upgrade point after every round (win or lose)
- [x] Game starts immediately (no pre-game talent screen)
- [x] resetTalentState() on match reset

### 2026-01-09 Session 14
- [x] Magma Lob rework: arc peaks exactly at midline
- [x] Magma bombs bounce on actual floor (not floating tableY)
- [x] Bomb visual distinction (darker, no light, fewer particles)
- [x] Bomb fixed damage (1, no volley scaling)
- [x] Varied bomb velocities (arrive at different times)
- [x] Minimum bomb velocity (5) to prevent stuck projectiles
- [x] Explosion particle burst and sound on split
- [x] Main physics loop skips Y-axis for lobs and bombs

### 2026-01-09 Session 13
- [x] UpgradeRegistry modular system for spell upgrades
- [x] Talent selection UI (shows before game starts)
- [x] playerUpgrades array and helper functions
- [x] Magma Lob upgrade: arc + split at midline
- [x] Defined Pyroblast, Frostbite, Glacial Cascade (not active yet)
- [x] Cast progress indicator fixed to start from top
- [x] Fireball approaching sound tuned (0.15 vol, 3x pitch)

### 2026-01-09 Session 12
- [x] Victory/defeat sounds (sfx/victory.wav, sfx/defeat.wav)
- [x] Parry button UI underneath ability bar
- [x] Input visual feedback on key presses
- [x] Cast progress shown on skill icons (radial overlay)
- [x] Mid-cast looping audio during spell casting
- [x] Ice shatter effect with physics shards
- [x] Ice shatter sound (sfx/ice-shatter.wav)
- [x] Sound pitch parameter added to playSound()
- [x] Frozen sound plays at 2x speed
- [x] Block/parry flash intensity tuned (0.1/0.5)
- [x] Flash effect color persistence bug fixed
- [x] Game renamed to "Volleybolt"
- [x] GitHub deployment (https://andrewamisola.github.io/Volleybolt/)
- [x] UI simplified ("W/S to move" only)

### 2026-01-09 Session 11
- [x] Character ground level fix (no longer floating)
- [x] Wall animation glitch fix (idle at boundaries)
- [x] Parry animation tuning (3x speed, frame 20 start, 500ms lock)
- [x] Velocity-based sound pitch for projectiles
- [x] Fireball cooldown bug fix (was missing check)
- [x] Animation freeze on frostbolt hit
- [x] Loading screen while models load
- [x] Explosive brick physics on gate hit
- [x] Character flash effect on block/parry

### 2026-01-09 Session 10
- [x] Cast cancellation on movement (W/S cancels cast, refunds mana)
- [x] Gravity Sphere commented out for rework (slot 3 removed)
- [x] Fireball cooldown fixed (5s after cast + 1s cast time)
- [x] AI respects fireball cooldown now
- [x] AI checks for dangerous projectiles before casting
- [x] AI cast bar (top right, red-tinted)
- [x] AI mana bar (3 segments, matching player style)
- [x] Symmetrical UI layout (player left, AI right)
- [x] Texture system for gates (auto-loads gate_stone.png)
- [x] Texture system for floor (optional stage_floor.png)
- [x] Character model loading (FBX from Mixamo)
- [x] Animation blending system (0.2s crossfade)
- [x] Animations hooked to gameplay (strafe, cast, idle)

### 2026-01-08 Session 6
- [x] Web Audio API sound system with stereo panning
- [x] All sound effects hooked up (cast, loop, block, parry, damage, etc.)
- [x] Frost Bolt ability (Key 2) - freezes for 1s, no damage
- [x] Frost Bolt ice visuals and dedicated sounds
- [x] "FROZEN!" combat text above frozen paddle
- [x] Volume slider UI with mute toggle
- [x] Fireballs float higher, removed paddle bounce
- [x] UTF-8 charset for emoji support

### 2026-01-08 Session 5
- [x] Fixed BUG-001 (crash on gate hit)
- [x] Fixed BUG-002 (particles disappearing - shared texture issue)
- [x] Volley damage scaling (0=1dmg, 1-2=2dmg, 3+=3dmg)
- [x] Damage numbers at gate position (3D to screen projection)
- [x] Impact flash effects (gate hit, parry)
- [x] Fixed hexagon border on ability UI
- [x] Volley tier visual via particle lifetime (no extra systems)
- [x] Removed TrailMesh, parry colors, paddle flash, mesh stretch
- [x] Performance optimizations for bullet-heaven scalability

### 2026-01-08 Session 4
- [x] Multi-projectile system (array of fireballs)
- [x] Destructible brick gate walls with arch design
- [x] Position-based brick destruction
- [x] Active fireball casting (press 1)
- [x] AI fireball casting with cooldown
- [x] MOBA-style ability UI (hex button, cooldown sweep, shine)
- [x] Fantasy font (Cinzel) throughout
- [x] Removed timer - first to destroy gate wins
- [x] Clean one-word messages (Victory, Defeat, etc.)
- [x] Parry system works with multiple projectiles
- [x] Increased parry speed cap (18 → 28)

### 2026-01-08 Session 3
- [x] Tighter parry window (1.0 distance)
- [x] AI parry ability (strategic, position-based)
- [x] Straight shot parries (no bounce)
- [x] Velocity cap (max speed 18)
- [x] Quaternion ball rotation
- [x] TrailMesh motion effect
- [x] Smear frame on impact
- [x] Dynamic ball stretch

### 2026-01-08 Session 1-2
- [x] Basic Pong implementation
- [x] Fireball visual effects
- [x] Parry mechanic
- [x] Directional parry
- [x] Bouncing physics
- [x] Height collision check
- [x] Documentation system

---

## Multiplayer Determinism & Perspective Plan

### Scope
Fix determinism, ownership, and perspective issues in PvP so host/guest see identical outcomes and the simulation is rollback-safe.

### Summary of Issues, Desired Outcome, and Proposed Fixes

#### 1) Non-deterministic projectile launch (PvP)
- **Issue**: `fireFireball` uses `Math.random` for launch angle, which can diverge between peers and break rollback determinism.
- **Desired outcome**: Projectile launch direction depends only on player state/input and is identical on host/guest.
- **Proposed code changes**:
  - Replace `Math.random` in fireball launch with deterministic input-based aim.
  - When the caster is moving, derive `velZ` from input direction and/or paddle velocity (deterministic); when stationary, set `velZ = 0`.
  - Use `seededRandom()` only for cosmetic effects (non-simulated), not for simulation-critical physics.
- **Targets**:
  - `C:\Users\andre\BabylonPong\index.html:13178` (`fireFireball`)

#### 2) World-side tower damage (PvP)
- **Issue**: Gate collision currently resolves damage based on world X instead of ownership, so perspective can be wrong.
- **Desired outcome**: Damage applies to the tower of the opponent of the projectile owner, regardless of camera flip.
- **Proposed code changes**:
  - Ensure `dealDamageToTower(isPlayerTower, ...)` uses `proj.owner` to decide which tower takes damage.
  - Update projectile ownership on any paddle block/parry or direction reversal.
- **Targets**:
  - `C:\Users\andre\BabylonPong\index.html:9349` (main physics gate collision)
  - `C:\Users\andre\BabylonPong\index.html:12191` (network physics gate collision)
  - `C:\Users\andre\BabylonPong\index.html:9164` (parry/blocks should set `proj.owner`)

#### 3) Rollback state missing projectile ownership
- **Issue**: `syncProjectilesToState` updates velocity/position but doesn’t reapply `owner`, so damage attribution can be wrong after rollback.
- **Desired outcome**: Rollback always restores projectile ownership consistently.
- **Proposed code changes**:
  - In `syncProjectilesToState`, update `existing.owner = sp.owner` for existing projectiles.
- **Targets**:
  - `C:\Users\andre\BabylonPong\index.html:11440` (`syncProjectilesToState`)

#### 4) Rollback missing combatant movement accumulator
- **Issue**: `combatant.moveAccum` drives step movement; not restoring it can cause divergent movement after rollback.
- **Desired outcome**: Movement state restores exactly so resimulation matches.
- **Proposed code changes**:
  - Capture and restore `moveAccum` for left/right combatants in rollback state.
- **Targets**:
  - `C:\Users\andre\BabylonPong\index.html:11330` (`captureGameState`/`restoreGameState`)

#### 5) Rollback crossing stage transitions
- **Issue**: `currentStage` and related gate health arrays are not captured; rollback during/around transitions can desync stages.
- **Desired outcome**: Either disallow rollback across transitions or fully capture/restore stage state.
- **Proposed code changes**:
  - Capture `currentStage`, `playerGateHealthByStage`, `aiGateHealthByStage`, `stageResults`, `totalRoundsPlayed`, `lastRoundAtStage`.
  - Alternatively, prevent rollback if `roundTransitioning` or `waitingToServe` is true.
- **Targets**:
  - `C:\Users\andre\BabylonPong\index.html:11330`

#### 6) Perspective-correct win/lose and scores
- **Issue**: `endRound('player'|'ai')` and `updateScore()` are world-side; guest may see wrong victory/defeat.
- **Desired outcome**: Winner is determined by side (left/right), but UI/animations reflect local vs remote.
- **Proposed code changes**:
  - Change `endRound` to accept a side (`left`/`right`) and derive local win/lose inside.
  - In PvP, map winner side to local/remote before showing victory/defeat text and animations.
  - Update `updateScore()` to show local score on left and remote score on right for guest.
- **Targets**:
  - `C:\Users\andre\BabylonPong\index.html:13654` (`endRound`)
  - `C:\Users\andre\BabylonPong\index.html:12289` (`updateScore`)

#### 7) PvP determinism audit (remaining randomness)
- **Issue**: `Math.random` is used in AI and visuals; if called inside PvP simulation it can desync.
- **Desired outcome**: PvP simulation uses only deterministic randomness or no randomness.
- **Proposed code changes**:
  - Replace any simulation-time randomness with `seededRandom()`.
  - Gate VFX randomness to render-only paths that don’t affect simulation state.
- **Targets**:
  - `C:\Users\andre\BabylonPong\index.html` (any `Math.random` inside PvP simulation paths)

#### 8) UI update efficiency (medium)
- **Issue**: PvP loop updates DOM every tick for health/score/mana; can be wasteful.
- **Desired outcome**: UI updates are throttled or change-driven to reduce overhead.
- **Proposed code changes**:
  - Throttle UI updates to 10–15 Hz or only when values change.
- **Targets**:
  - `C:\Users\andre\BabylonPong\index.html:11572` (PvP loop)

### Proposed Implementation Order
1. Deterministic fireball launch + remove PvP `Math.random` from physics.
2. Ownership-based tower damage + owner updates on block/parry.
3. Rollback state completeness (owner + moveAccum + stage state).
4. Perspective-correct win/lose and scores.
5. PvP determinism audit and UI efficiency pass.

### Verification Checklist
- Host and guest see identical hit attribution and tower damage.
- Score display matches local/remote perspective for guest.
- Parry/block always switches projectile ownership.
- Rollback resimulation produces identical results (no drift).
- No random input in PvP simulation unless `seededRandom()`.

---

## Task Template
```
| Status | Task | Notes |
|--------|------|-------|
| `[ ]` | Task description | Additional context |
```

## Bug Template
```
| ID | Status | Description | Steps to Reproduce | Notes |
|----|--------|-------------|-------------------|-------|
| BUG-001 | `[ ]` | What's wrong | 1. Do X 2. See Y | Context |
```
