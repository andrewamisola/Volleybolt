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

## Completed Tasks

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
