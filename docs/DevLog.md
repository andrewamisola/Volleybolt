# Development Log - Volleybolt (formerly Wizard Duel Arena)

## 2026-01-12

### Session 33 (Git Disaster Recovery & Documentation)
**Time**: Night

#### Summary
Recovered from devastating git pull that wiped progress from sessions 16-32. Restored all features from memory/conversation history. Updated model loading to use new per-player folder structure (models/p1/, p2/, etc.).

#### Restored/Verified
- All features from sessions 16-32 (see below)
- Model paths updated for p1/p2 folder structure
- Documentation rebuild

---

### Sessions 16-32 (Consolidated - Recovered from Git Wipe)
**Time**: 2026-01-09 through 2026-01-11

#### Summary
These sessions were lost in a git pull disaster. Features have been restored but original session logs are unrecoverable. Below is the consolidated list of all implemented features.

#### Balance Changes
- [x] **Fireball Damage Scaling**: Changed from 1/2/3 to 2 base + volleyCount (max 5)
- [x] **Mana Per Block**: Reduced from 1.0 to 0.5 mana per block
- [x] **Parry Cooldown Rework**: Success = 0.2s cooldown, Fail = 3.0s cooldown (punishes spam)

#### Frostbolt Enhancements
- [x] **Cancels Enemy Projectiles**: Frostbolt destroys fireballs on collision
- [x] **Stops Mana Regen**: Frozen players don't regenerate mana
- [x] **Cancels Casting**: Getting frozen interrupts active spell casts

#### Visual Overhaul (Diablo 2 Style)
- [x] **Shadow System**: Light at (12, 28, -8), darkness 0.15, only characters cast shadows
- [x] **Scene Post-Processing**: Contrast 1.4, saturation 1.2
- [x] **Fog Settings**: Opacity 0.45, height 0.25, color (0.25, 0.28, 0.35)
- [x] **Stepped Fading**: Impact flashes and decals use discrete alpha steps (retro feel)
- [x] **Text Shadows**: Simplified to pixel shadows only (no blur)

#### Gameplay Mechanics
- [x] **Paddle Momentum**: Ball trajectory affected by paddle velocity (0.4 factor)
- [x] **Projectile-Projectile Collision**: Damage-based resolution with 0.5s grace period
- [x] **Magma Bomb Simplification**: 8 particles, trail length 8, width 0.15, no outer flames

#### UI/UX Improvements
- [x] **Menu System**: Game properly stops/pauses when in background
- [x] **Victory/Defeat Animations**: Now loop correctly
- [x] **NES-Styled Floating Combat Text**: Black background with white border, queue system, model-anchored, stepped movement (80ms intervals)

#### Multiplayer (P2P via PeerJS)
- [x] **Client Controls Fix**: W/S inverted for client (right-side player)
- [x] **Rollback Netcode**: State synchronization with prediction
- [x] **Freeze Text in Multiplayer**: Shows "FROZEN!" for both players

#### Model System
- [x] **Per-Player Folders**: models/p1/, p2/, p3/, p4/ for different character skins
- [x] **P2 File Naming**: Animations use `_P2_` suffix in p2 folder
- [x] **Dynamic Path Loading**: Loader selects correct folder based on player side

---

## 2026-01-09

### Session 15 (HotS-Style In-Game Talent System)
**Time**: Night

#### Summary
Major UX overhaul replacing pre-game talent selection with Heroes of the Storm-style in-game progression. Players now earn upgrade points after every round and can select talents by clicking glowing ability icons during gameplay.

#### Implemented
- [x] **TalentTree Data Structure**
  - Defines tiers 1-3 for each ability (Fireball, Frostbolt)
  - Each tier has branching choices (2-3 options)
  - Structure: `TalentTree.fireball.tiers[1].choices = ['magma_lob', 'pyroblast']`

- [x] **TalentState Tracking**
  - `upgradePoints` - Available points to spend
  - `abilities[abilityId].currentTier` - Current upgrade level (0-3)
  - `abilities[abilityId].selectedTalents` - Array of chosen upgrade IDs

- [x] **Upgrade Indicator UI**
  - Golden pulsing badge (⬆) on ability slots when upgradeable
  - `.upgradeable` class adds golden glow to ability hex
  - CSS animations: pulse and glow effects

- [x] **Upgrade Points HUD**
  - Shows `⭐ X` at top center when points available
  - Appears after first point earned
  - Pulses when points available to spend

- [x] **Talent Panel UI**
  - Click ability with upgrade available → panel expands
  - Shows tier progression (1-2-3) with completed/active/locked states
  - Displays 2-3 talent choice cards with icon, name, description
  - Click card to select talent → panel closes

- [x] **Progression System**
  - Award 1 upgrade point after EVERY round (win or lose)
  - Points persist across rounds until spent
  - Match reset clears all talents (`resetTalentState()`)

- [x] **Game Flow Change**
  - Removed pre-game talent selection screen
  - Game starts immediately after loading
  - Talents selected during gameplay between rounds

#### Technical Notes
- `TalentTree` defines structure, `UpgradeRegistry` defines behavior
- `getActiveUpgrades(abilityId)` returns all selected talents for ability
- `applyUpgradesToProjectile()` now uses `TalentState` instead of old `playerUpgrades` array
- Click handlers on ability slots toggle talent panel
- ESC or click outside closes panel

#### Known Issues
- Only Magma Lob fully functional
- Pyroblast: `modifyAbility.castTime` not wired to casting system
- Frostbite: `onHit` hook not called from frostbolt collision
- Glacial Cascade: Trail positions recorded but no visual/slow effect

#### Next Session
- Wire up Pyroblast cast time modification
- Wire up Frostbite onHit hook
- Implement Glacial Cascade trail visuals and slow effect

---

### Session 14 (Magma Lob Rework - Bouncing Bombs)
**Time**: Night

#### Summary
Major rework of the Magma Lob upgrade. Changed from simple split-at-midline to a full grenade launcher experience with physics-based bouncing bombs that roll on the actual floor.

#### Implemented
- [x] **Lob Arc Physics**
  - Calculated velY dynamically so apex is exactly at midline (x=0)
  - Formula: `velY = gravity * (distanceToMid / velX)`
  - Consistent, predictable arc every time
  - Lob has its own physics (skips main game loop Y-axis)

- [x] **Midline Split Trigger**
  - Changed from apex-based to position-based
  - Splits when crossing x=0 (center/net)
  - Explosion particle burst (60 particles) on split
  - Plays fireball_cast.wav at lower pitch (0.7) for boom

- [x] **Real Floor Physics for Bombs**
  - Bombs bounce off actual ground (Y=0.22, ball radius)
  - Skips main game loop's tableY (0.6) floating
  - Bounce coefficient 0.65 with velocity threshold
  - Minimum velocity enforced (5) to prevent stuck bombs

- [x] **Bomb Visual Distinction**
  - Darker magma material (0.6, 0.2, 0.05 emissive)
  - No point light (removed for bombs)
  - Dimmer glow sphere, shorter trail
  - Fewer, darker particles (30 core, 15 outer vs 80/50)

- [x] **Bomb Damage**
  - Fixed at 1 damage (no volley scaling)
  - Uses `proj.damage` property checked at gate hit

- [x] **Varied Bomb Velocities**
  - Bomb 1: 60-110% speed, lower pop (1-5)
  - Bomb 2: 90-140% speed, higher pop (3-7)
  - Different Z spread angles
  - Bombs arrive at different times for counterplay

#### Technical Notes
- Main physics loop now skips Y-axis for `proj.isLob` and `proj.isMagmaBomb`
- Parry code also skips Y reset for these projectile types
- `window.flareTexture` made global for upgrade registry access
- spawnFireball() accepts options object: `{ isMagmaBomb, startY, velY }`

#### Architecture
```javascript
// Lob physics calculation
const distanceToMid = Math.abs(proj.mesh.position.x);
const timeToMid = distanceToMid / Math.abs(proj.velX);
proj.velY = proj.lobGravity * timeToMid;  // Apex at midline

// Bomb ground physics (separate from tableY)
const groundLevel = 0.22;  // Ball radius, sits ON floor
proj.velY -= 12 * dt;  // Gravity
if (proj.mesh.position.y <= groundLevel) {
    proj.velY = Math.abs(proj.velY) * 0.65;  // Bounce
}
```

---

### Session 13 (Upgrade System & Talent Selection)
**Time**: Night

#### Summary
Built modular upgrade/talent system foundation. Added talent selection screen that shows before game starts, UpgradeRegistry for defining spell upgrades, and implemented first upgrade "Magma Lob" for testing.

#### Implemented
- [x] **UpgradeRegistry System**
  - Modular registry for defining upgrades with hooks: `onSpawn`, `onUpdate`, `shouldSplit`, `onSplit`, `onHit`
  - Helper functions: `hasUpgrade()`, `getUpgrade()`, `getUpgradesForAbility()`
  - `applyUpgradesToProjectile()` and `updateProjectileUpgrades()` for runtime behavior

- [x] **Talent Selection UI**
  - Full-screen overlay after loading, before game starts
  - Shows upgrade cards with icon, name, description, effects list
  - Click to select, "Start Battle" button to begin
  - CSS: Dark theme, golden selection border, hover effects

- [x] **Magma Lob Upgrade (Fireball)**
  - Fireball arcs through the air (velY=6, gravity pulls down)
  - Splits into 2 fireballs when crossing midline (x=0)
  - Split projectiles travel at angles with Z spread
  - Split projectiles roll low along ground (Y=0.35)

- [x] **Defined Future Upgrades (not active)**
  - Pyroblast: 3s cast, 5 damage, unblockable
  - Frostbite: +0.3s freeze on frozen targets
  - Glacial Cascade: Frost bolt leaves slowing trail

- [x] **Minor Fixes**
  - Cast progress indicator now starts from top (from 0deg not -90deg)
  - Fireball approaching sound: 0.15 volume, 3x pitch

#### Technical Notes
- UpgradeRegistry uses callback pattern for flexible behavior modification
- Projectiles now have `type: 'fireball'` for proper identification
- `markedForSplit` flag triggers destruction after split spawns children
- Talent screen shows after `checkAllLoaded()` completes

#### Architecture
```javascript
UpgradeRegistry = {
  upgrade_id: {
    id, name, baseAbility, tier, icon, description, effects[],
    onSpawn(proj),      // Called when projectile created
    onUpdate(proj, dt), // Called every frame
    shouldSplit(proj),  // Returns true when split should occur
    onSplit(proj, spawnFunc), // Creates split projectiles
    onHit(target, freezeTime) // For effects on impact
  }
}
```

---

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
