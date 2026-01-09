# Development Log - Volleybolt (formerly Wizard Duel Arena)

## 2026-01-09

### Session 12 (UI Polish, Audio, Ice Shatter, GitHub Deployment)
**Time**: Night

#### Summary
Final polish session - added parry button UI, input feedback, cast progress on icons, mid-cast audio, ice shatter effect, sound tuning, and deployed game to GitHub Pages. Renamed game to "Volleybolt".

#### Implemented
- [x] **Victory/Defeat Sounds**
  - Added sfx/victory.wav and sfx/defeat.wav
  - Play when game ends (tower destroyed)

- [x] **Parry Button UI**
  - Added button underneath ability bar
  - Shows 🛡️ icon, "Parry" label, SPACE keybind badge
  - Understated styling (70% opacity, muted colors)

- [x] **Input Visual Feedback**
  - Key presses (1, 2, 3, SPACE) show "pressed" state on UI buttons
  - Brief scale + brightness flash (120ms)
  - Works for both keyboard and click

- [x] **Cast Progress on Skill Icons**
  - Radial darkening overlay during cast
  - Uses conic-gradient from top, reveals icon as cast completes
  - Works alongside existing cast bar

- [x] **Mid-Cast Audio**
  - Looping sound plays during spell casting
  - Stops on cast complete or cancel
  - Separate tracking for player/AI

- [x] **Ice Shatter Effect**
  - Ice block breaks into 6 physics shards when freeze ends
  - Shards explode outward with gravity (600ms duration)
  - Added sfx/ice-shatter.wav sound

- [x] **Sound Tuning**
  - Added pitch parameter to playSound() function
  - Frozen sound plays at 2x speed
  - Block flash reduced (0.1 intensity)
  - Parry flash reduced (0.5 intensity)

- [x] **Flash Effect Bug Fix**
  - Original emissive colors now stored once on first flash
  - Prevents color drift when multiple flashes overlap

- [x] **Game Renamed to Volleybolt**
  - Updated title tag and loading screen

- [x] **GitHub Deployment**
  - Repository: https://github.com/andrewamisola/Volleybolt
  - Live game: https://andrewamisola.github.io/Volleybolt/
  - Uses GitHub Actions workflow for deployment

- [x] **UI Cleanup**
  - Simplified instructions to just "W/S to move"

#### Technical Notes
- playSound() now accepts pitch parameter (default 1.0)
- Ice shatter creates temporary meshes with requestAnimationFrame physics
- GitHub Pages deployed via Actions workflow (handles large model files better)

---

### Session 11 (Character Polish, Animation Fixes, Audio & Visual Effects)
**Time**: Night

#### Summary
Polish session focused on character model fixes, animation improvements, audio enhancements, and visual effect additions. Fixed floating characters, wall animation glitches, fireball cooldown bug, and added velocity-based sound pitch, explosive brick physics, and character flash effects on block/parry.

#### Implemented
- [x] **Character Ground Level Fix**
  - Lowered wizard Y position by -0.25 so they stand on ground instead of floating

- [x] **Wall Animation Glitch Fix**
  - Added boundary checks for animations
  - Characters return to idle when at wall and trying to move into it
  - Prevents strafe animation playing when not actually moving

- [x] **Parry Animation Tuning**
  - Changed to 3x speed (from 1.5x)
  - Starts at frame 20 (skips windup)
  - 500ms animation lock

- [x] **Velocity-Based Sound Pitch**
  - Added `updateSoundPitch()` function
  - Traveling projectile sounds pitch up/down based on speed
  - Range: 0.8x to 1.5x pitch, base velocity 12
  - Faster projectiles (after parries) sound higher pitched

- [x] **Fireball Cooldown Bug Fix**
  - Added `playerFireballCooldown <= 0` check to both key press (Digit1) and click handler
  - Was missing from both, allowing cast during cooldown

- [x] **Animation Freeze on Frostbolt Hit**
  - Added `freezePlayerAnim()` / `unfreezePlayerAnim()` functions
  - Animation pauses in place when frozen by frostbolt
  - Resumes when freeze expires

- [x] **Loading Screen**
  - Shows "Wizard Duel Arena" title with spinner while loading
  - Paddles hidden until models load
  - Fades out smoothly when both player and AI models ready

- [x] **Explosive Brick Physics**
  - Bricks now explode outward when gate is hit
  - Random upward burst, outward velocity, sideways scatter
  - Wild spinning on all axes
  - Gravity eventually pulls them down, fade out in flight

- [x] **Character Flash Effect on Block/Parry**
  - Removed shield barrier system (wasn't rendering properly)
  - Added character model flash effect instead
  - On block: subtle blue (player) or red (AI) glow
  - On parry: brighter cyan/pink flash
  - Smoothly fades back to normal

#### Attempted but Removed
- Shield barrier effect (Dune-style) - tried multiple approaches (torus, cylinder, sphere) but visibility/rendering issues prevented it from working
- Will revisit in future session with different approach

#### Technical Notes
- `mesh.visibility` property used for shield (was causing issues)
- Fresnel effects caused dark edge artifacts
- Character mesh flash uses emissive color manipulation with fade

---

### Session 10 (Cast System Polish, AI Improvements, Textures & Character Setup)
**Time**: Night

#### Summary
Major polish session - fixed cast cancellation on movement, improved AI behavior, added symmetrical UI for both players, implemented texture system for gates/floor, and set up character model loading with animation blending.

#### Implemented
- [x] **Cast Cancellation on Movement**
  - Moving (W/S) while casting now cancels cast and refunds mana
  - Removed isPlayerRooted() blocking - movement always works

- [x] **Gravity Sphere Disabled**
  - Commented out for rework (HTML, keybind, click handler, AI usage)
  - Added null checks to prevent JS errors
  - Ability bar now shows only 2 abilities

- [x] **Fireball Cooldown Fixed**
  - Added 5 second cooldown after cast completes (in addition to 1s cast time)
  - AI now respects cooldown (was missing check)

- [x] **AI Behavior Improvements**
  - AI checks for dangerous incoming projectiles before casting
  - Won't cast if projectile approaching (x > 0 and x < 8)
  - Reduced cast frequency slightly for balance

- [x] **AI Cast Bar**
  - Shows in top right when AI is casting
  - Same style as player cast bar
  - Red-tinted border to distinguish

- [x] **AI Mana Bar**
  - 3 segments matching player style
  - Red-tinted border
  - Updates on gain/spend/regen

- [x] **Symmetrical UI Layout**
  - Player cast/mana bars: bottom left (120px from edge, 370/320px from bottom)
  - AI cast/mana bars: bottom right (mirrored position)

- [x] **Texture System**
  - Gate textures: `textures/gate_stone.png` (tints blue for player, red for AI)
  - Stage floor: `textures/stage_floor.png` (optional, falls back to dark color)
  - Auto-loads if files exist

- [x] **Character Model System**
  - FBX loading from `models/` folder
  - Babylon.js loaders library added
  - Base model: `idle.fbx`
  - Animations: `left_strafe.fbx`, `right_strafe.fbx`, `wizard_cast.fbx`

- [x] **Animation Blending**
  - 0.2s crossfade between animations
  - Strafe left/right on W/S movement
  - Cast animation on spell cast
  - Return to idle when stopped

#### In Progress / Known Issues
- Character models loading but not visible (scale/position debugging needed)
- Models load (200 OK in server logs) but may be positioned wrong or too small

#### Technical Notes
- Babylon.js loaders required for FBX: `babylonjs.loaders.min.js`
- FBX from Mixamo typically needs ~0.01-0.02 scale
- Animations stored in separate dictionaries for player/AI
- TransformNode used as parent container for all character meshes

#### Files Added
```
textures/gate_stone.png   (~2MB)
textures/stage_ground.png (~2.6MB, renamed to stage_floor.png for cleaner fallback)
models/idle.fbx           (~65MB)
models/left_strafe.fbx    (~65MB)
models/right_strafe.fbx   (~65MB)
models/wizard_cast.fbx    (~65MB)
```

---

## 2026-01-08

### Session 6 (Sound System & Frost Bolt)
**Time**: Night

#### Summary
Major audio implementation session - added complete sound system with stereo panning, plus new Frost Bolt ability that freezes enemies.

#### Implemented
- [x] **Web Audio API Sound System**
  - Custom sound system using Web Audio API (not Babylon's audio engine)
  - Stereo panning based on X position (capped at ±50%)
  - Master volume control with gain node
  - Support for one-shot and looping sounds

- [x] **Sound Effects Hooked Up**
  - `fireball_cast.wav` - Casting fireball
  - `fireball_loop.wav` - Looping while fireball travels
  - `woosh.wav` - Wall bounce
  - `block.wav` - Passive paddle deflection
  - `parry.wav` - Active parry hit
  - `gate_hit_damage.wav` - Tower takes damage
  - `spell_ready.wav` - Cooldown complete
  - `fireball_approaching.wav` - Warning when fireball approaches player

- [x] **Frost Bolt Ability (Key 2)**
  - New spell type with ice/cyan visuals
  - Freezes enemy paddle for 1.0 second on hit
  - Does NOT damage gates (utility spell)
  - Much faster than fireball (speed 22 vs 12)
  - 10 second cooldown
  - AI can cast it too (less frequently than fireball)
  - Own sounds: `frostbolt_cast.wav`, `ice_blast_travel.wav`, `frozen.wav`

- [x] **"FROZEN!" Combat Text**
  - Floats above frozen paddle
  - Icy blue styling with animation
  - Shows for both player and AI

- [x] **Volume Slider UI**
  - Bottom-right corner, minimal design
  - Drag slider to adjust (0-100%)
  - Click icon to toggle mute
  - Icon changes: 🔊 → 🔉 → 🔇

- [x] **Visual Tweaks**
  - Fireballs float higher (Y=0.6 vs 0.25)
  - Removed bounce from paddle hits (spells stay level)
  - Added `<meta charset="UTF-8">` for emoji support

#### Technical Notes
- Babylon.js audio engine wasn't loading sounds properly, switched to raw Web Audio API
- Sounds loaded via fetch + decodeAudioData
- All sounds route through masterGain for volume control
- Local server required for audio (file:// blocks fetch)

---

### Session 5 (Polish & Bug Fixes)
**Time**: Night

#### Summary
Visual polish session - fixed critical bugs, improved visual feedback, and optimized for future bullet-heaven gameplay with many projectiles.

#### Bug Fixes
- [x] **BUG-001**: Fixed crash when fireball hits gate (removed undefined `aiDamageDealt`/`playerDamageDealt` variables)
- [x] **BUG-002**: Fixed particles disappearing when any fireball hit gate (shared texture was being disposed - added `dispose(false)` to preserve texture)

#### Implemented
- [x] **Volley Damage Scaling**
  - 0 volleys = 1 damage (1 brick)
  - 1-2 volleys = 2 damage (2 bricks)
  - 3+ volleys = 3 damage cap (3 bricks)
  - Bricks fall with staggered timing for visual effect

- [x] **Damage Numbers at Gate Position**
  - Numbers now float at actual 3D gate position where hit occurs
  - Uses Babylon.js Vector3.Project for world-to-screen conversion

- [x] **Impact Flash Effects**
  - Gate impact: Orange/yellow flash, size scales with damage
  - Parry: Bright flash (blue for player, magenta for AI)
  - Expanding sphere that fades out

- [x] **Hexagon Border Fix**
  - Fixed ability UI border using CSS pseudo-element
  - Perfect hexagonal gold border when ready

- [x] **Volley Tier Visual (Particle Trail)**
  - Higher volley count = longer particle lifetime = visible trail
  - Tier 1: base particles
  - Tier 2: slightly longer trail
  - Tier 3: longest trail
  - Kept simple for performance (reuses existing particle system)

#### Removed/Simplified
- Removed TrailMesh (looked bad - "sperm trail")
- Removed parry color changes (confusing with future ability colors)
- Removed paddle hit flash (too intense)
- Disabled mesh stretch/rotation (was breaking particle direction)

#### Performance Considerations
- No extra particle systems for trails (reuses main fire particles)
- Shared texture preserved across projectile disposal
- Designed for bullet-heaven with many simultaneous projectiles

#### Notes
- User confirmed particles now work correctly after texture fix
- Visual feedback is now: tier indicated by particle trail length, damage by floating numbers + brick destruction + impact flash

---

### Session 4 (Major Transformation - Ability System & Gates)
**Time**: Evening/Night

#### Summary
Massive session transforming the game from Pong prototype to active spell-casting wizard duel. Replaced automatic ball with player-cast fireballs, added destructible gate walls, MOBA-style UI, and removed timer for "first to destroy gate wins" gameplay.

#### Implemented
- [x] **Destructible Gate System**
  - Replaced cylinder towers with brick wall gates
  - Arched doorway design with keystones
  - Position-based destruction (brick nearest to hit falls)
  - Bricks fall with physics, tumble, fade to rubble
  - Gates rebuild each round

- [x] **Active Ability System**
  - Removed automatic ball/serve system
  - Player presses 1 to cast Fireball
  - AI casts fireballs on cooldown (6 sec)
  - Multiple projectiles can exist simultaneously
  - Each projectile has own mesh, particles, light, trail

- [x] **MOBA-Style Ability UI**
  - Hexagonal button with clip-path
  - Fireball emoji icon (🔥)
  - Cooldown overlay with big number
  - Radial sweep animation during cooldown
  - Golden glow + shine animation when ready
  - Clickable or press 1

- [x] **Visual Polish**
  - Fantasy font (Cinzel from Google Fonts) everywhere
  - Clean one-word messages: Ready, Victory, Defeat, Champion, Defeated
  - Timer removed - cleaner UI

- [x] **Win Condition Overhaul**
  - Removed 30-second timer entirely
  - First to destroy enemy gate wins the round
  - Gate has ~20 HP (matches brick count)
  - Health bars show gate status

- [x] **Parry System Updated**
  - Works with multiple projectiles
  - Finds nearest parryable projectile
  - Parry boost increased (1.25 → 1.4, cap 18 → 28)

#### Code Architecture Changes
```javascript
// Old: Single ball with global velocity
let ball, ballVelX, ballVelZ;

// New: Projectile array with per-projectile state
let projectiles = [];
// Each projectile: { mesh, velX, velZ, velY, owner, isParried, parriedBy, particles, light, trail, ... }

// Spawning: window.spawnFireball(owner, startX, startZ, velX, velZ)
// Cleanup: window.destroyProjectile(proj)
```

#### Known Bug
- **CRASH**: Game crashes when fireball hits gate
  - Likely in dealDamageToTower or destroyBrickAt
  - Needs investigation next session

#### Pending Implementation
- Volley-based damage scaling (more volleys = more damage, cap at 3x)
- Cooldown reduction on block/parry

#### Notes
- Brick count reduced for faster rounds (~20 bricks vs 55)
- AI casting has 2 sec delay at round start
- Health bars work, gates visually crumble
- Game feels much more like active wizard duel now

---

### Session 3 (Parry Improvements + Game Vision)
**Time**: Evening

#### Summary
- Improved parry mechanics (tighter timing, AI can parry back)
- Added cartoon speed effects (quaternion rotation, TrailMesh, smear frames)
- Major design discussion: evolving from Pong to **Wizard Duel Arena**

#### Implemented
- [x] Tighter parry window (2.5 -> 1.0) - must time it close to contact
- [x] AI parry ability - AI parries when player is out of position
- [x] AI parry is strategic (70% chance when player far out of position, 30% medium, 0% when aligned)
- [x] Straight shot parries (no bounce arc, locks to table level)
- [x] Reduced parry velocity (boost 1.8 -> 1.25, hard cap at speed 18)
- [x] Quaternion-based ball rotation (faces travel direction)
- [x] TrailMesh for motion trail effect (color matches parry type)
- [x] Smear frame on parry impact (cartoon punch effect)
- [x] Dynamic ball stretch based on velocity (squash-and-stretch)

#### Visual Effects System
```javascript
// Velocity tracking from position delta
const velocity = ball.position.subtract(lastBallPos).scale(1 / dt);

// Quaternion rotation toward travel direction
ball.rotationQuaternion = BABYLON.Quaternion.FromLookDirectionLH(dir, BABYLON.Vector3.Up());

// Stretch along forward axis
ball.scaling.set(compress, compress, stretchFactor);

// TrailMesh with dynamic alpha
trail = new BABYLON.TrailMesh("trail", ball, scene, 0.15, 20, true);
trailMat.alpha = BABYLON.Scalar.Clamp(speed / 35, 0.1, 0.5);
```

#### Game Vision: Wizard Duel Arena
Major pivot from "Pong with effects" to full game concept:

**Theme**: Two wizards dueling, casting spells at each other's towers

**Core Loop**:
1. Pick 4 abilities pre-match
2. Cast spells (costs mana, has cooldowns)
3. Block/deflect incoming spells by positioning
4. Spells that pass deal damage to tower
5. Tug-of-war across 5 zones (push forward on win, back on loss)
6. Level up / pick upgrades between rounds
7. Destroy enemy core to win

**The 5 Zones**:
```
[YOUR CORE] - [YOUR TOWER] - [MIDFIELD] - [ENEMY TOWER] - [ENEMY CORE]
```

**Ability Categories** (planned):
- Offensive: Fireball, Ice Bolt, Lightning
- Modifiers: Triple Shot, Piercing, Homing
- Utility/CC: Freeze, Slow, Blind
- Defensive: Shield burst, Reflect boost

**Intro Sequence** (planned):
1. Classic Atari Pong look (2D, minimal)
2. Camera rotates revealing 3D
3. Fantasy world fades in (wizards, towers, arena)

#### Notes
- Blocking is passive (always there, position to intercept)
- Overwhelm is the challenge - can't block everything when too many spells
- Mana system prevents spam casting
- Deflection rewards (cooldown reduction, mana regen) add depth

#### Next Steps (Priority Order)
1. Multi-projectile support (refactor from single ball)
2. Tower health system (replace score)
3. Active casting (player spawns fireballs)
4. Mana/resource system
5. Cooldown system
6. Deflection rewards

---

### Session 2 (Documentation Setup)
**Time**: Evening

#### Summary
- Setting up project documentation system for AI continuity
- Creating tracking files and handoff protocol

#### Implemented
- [x] ai.context.md - Central index file
- [x] DevLog.md - This file
- [x] Tasks.md - Feature/bug tracking
- [x] Architecture.md - Implementation notes
- [x] Debug.md - Test scenarios
- [x] /handoff command (in .claude/commands/)
- [x] /start command (in .claude/commands/)

#### Notes
- Custom commands in .claude/commands/ need to be executed manually (not auto-registered as skills)
- For handoff, just ask "do a handoff" and AI will follow the protocol

---

### Session 1 (Initial Development)
**Time**: ~Morning-Afternoon

#### Summary
- Started as Godot project, switched to Babylon.js due to workflow difficulties
- Built complete playable Pong prototype in single HTML file

#### Implemented
- [x] Basic 3D scene with orthographic camera view
- [x] Player paddle (blue, left side)
- [x] AI paddle (red, right side)
- [x] Ball with fireball particle effects and glow
- [x] Score tracking and display
- [x] Ball serving system (SPACE to start)
- [x] Parry mechanic (SPACE near ball = speed boost + shrink + color change)
- [x] Directional parry (hold W/S while parrying to aim)
- [x] Bouncing physics (one bounce per volley, visual only)
- [x] Height collision check (ball must be below Y=0.8 to hit paddles)

#### Bug Fixes
- Fixed paddle not moving (removed physics aggregate)
- Fixed reversed controls (W/S mapping)
- Fixed camera orientation (alpha to -PI/2)
- Fixed directional parry not working (speed boost order)
- Fixed ball bouncing over paddles (added maxHitHeight check)
- Increased paddle speed (12 -> 20) for better reactivity

#### Notes
- Babylon.js loaded from CDN, no build step needed
- Manual physics instead of Havok for paddle movement
- Using `e.code` instead of `e.key` for keyboard input

---

<!-- Template for new entries:

## YYYY-MM-DD

### Session N (Description)
**Time**: Time of day

#### Summary
Brief description of what was worked on

#### Implemented
- [ ] Feature 1
- [ ] Feature 2

#### Bug Fixes
- Fixed X by doing Y

#### Notes
Any important observations

-->
