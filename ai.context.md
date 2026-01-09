# AI Context - Volleybolt

> **READ THIS FIRST** at the start of every session.

## Project Overview
- **Name**: Volleybolt (formerly Wizard Duel Arena / BabylonPong)
- **Concept**: 1v1 spell-casting arena game with Pong DNA
- **Tech Stack**: Babylon.js (CDN), vanilla HTML/JS, no build step
- **Main File**: `index.html` (single file contains everything)
- **Live Game**: https://andrewamisola.github.io/Volleybolt/
- **Repository**: https://github.com/andrewamisola/Volleybolt

## Quick Links
| Document | Purpose |
|----------|---------|
| [Tasks.md](./docs/Tasks.md) | Roadmap, features, phases |
| [DevLog.md](./docs/DevLog.md) | Daily development log |
| [Architecture.md](./docs/Architecture.md) | How things work, future plans |
| [Debug.md](./docs/Debug.md) | Test scenarios |

## Current State
- **Last Updated**: 2026-01-09 (Session 15)
- **Game Status**: HotS-style in-game talent system, game starts immediately
- **Active Branch**: gh-pages

### What's Working
- **In-Game Talent System**: HotS-style - earn upgrade points after rounds, click abilities to upgrade
- **TalentTree + TalentState**: Tier 1-3 progression per ability with branching choices
- **Upgrade Indicators**: Golden pulsing badges on ability slots when upgrades available
- **Talent Panel UI**: Click ability → expand panel with tier choices → select to apply
- **Upgrade Points HUD**: Shows available points at top center
- **UpgradeRegistry**: Modular system for defining spell upgrades with hooks
- **Magma Lob Upgrade**: 45-degree arc peaks at midline, splits into 2 bouncing bombs
- **Bouncing Bombs**: Real floor physics (Y=0.22), darker visuals, 1 fixed damage, varied velocities
- **Character Models**: GLB wizard models with animations (idle, strafe, cast, parry)
- **Animation System**: 0.2s crossfade blending, freeze on frostbolt hit
- **Loading Screen**: Shows while models load, fades when ready
- **Cast Time System**: 1s cast for fireball, 5s cooldown after
- **Cast Progress on Icons**: Radial overlay reveals icon as cast completes
- **Mid-Cast Audio**: Looping sound during spell casting
- **Movement cancels cast**: W/S during cast = cancel + mana refund
- **AI Cast Bar**: Shows enemy casting progress
- **AI Mana Bar**: 3 segments matching player style
- **Symmetrical UI**: Player left, AI right
- **Parry Button**: Underneath ability bar with SPACE keybind
- **Input Feedback**: Key presses flash corresponding UI buttons
- **Textures**: Gate stone texture loading (tints by team)
- **Sound System**: Stereo panning, pitch control, victory/defeat sounds
- **Explosive Bricks**: Gate bricks explode outward on hit
- **Ice Shatter**: Ice block breaks into physics shards when freeze ends
- **Character Flash**: Emissive glow on block/parry (tuned intensity)
- **Gravity Sphere**: Commented out for rework

### Talent System (HotS-Style)
```javascript
// TalentTree defines tier structure with branching choices
TalentTree = {
  fireball: {
    tiers: {
      1: { choices: ['magma_lob', 'pyroblast'] },
      2: { choices: ['inferno_trail', 'blazing_speed'] },
      3: { choices: ['phoenix_fire', 'hellfire_barrage'] }
    }
  },
  frostbolt: { /* similar structure */ }
}

// TalentState tracks player progression
TalentState = {
  upgradePoints: 0,        // Available to spend
  abilities: {
    fireball: { currentTier: 0, selectedTalents: [] },
    frostbolt: { currentTier: 0, selectedTalents: [] }
  }
}

// Key functions
canUpgradeAbility(abilityId)    // Check if can upgrade
getAvailableChoices(abilityId)  // Get tier choices
selectTalent(abilityId, upgradeId) // Apply upgrade
awardUpgradePoint(1)            // Called after each round
```

### UpgradeRegistry (Behavior Definitions)
```javascript
UpgradeRegistry = {
  magma_lob: {
    id, name, baseAbility: 'fireball', tier: 1,
    icon: '🌋', description, effects[],
    onSpawn(proj),       // Calculate arc for apex at midline
    onUpdate(proj, dt),  // Custom gravity, bomb bouncing
    shouldSplit(proj),   // Check if crossing midline (x=0)
    onSplit(proj, spawnFunc) // Create 2 bouncing magma bombs
  }
}
```

### Magma Lob Details
- **Lob**: Arc calculated so apex is exactly at midline (x=0)
- **Split**: Triggers at midline with explosion particles + sound
- **Bombs**: Bounce on real floor (Y=0.22), darker visuals, no light
- **Damage**: Fixed at 1 (no volley scaling)
- **Velocity**: Varied per bomb (60-140%), minimum 5 to prevent stuck
- **Physics**: Skips main game loop Y-axis, uses own gravity

### Tier 1 Upgrades (Status)
| Upgrade | Spell | Effect | Status |
|---------|-------|--------|--------|
| Magma Lob | Fireball | 45° arc, splits at midline into 2 bouncing bombs | ✅ Working |
| Pyroblast | Fireball | 3s cast, 5 damage | ⚠️ Partial (cast time not wired) |
| Frostbite | Frost Bolt | +0.3s freeze on frozen targets | ❌ onHit not wired |
| Glacial Cascade | Frost Bolt | Leaves slowing trail | ❌ No visual/effect |

**Next session**: Wire up Pyroblast cast time, Frostbite onHit, and Glacial Cascade trail.

### Character Model Files (models/ folder)
- `wizard_combined.glb` - Combined model with all animations
- Animations: idle, left (strafe), right (strafe), parry, cast

---

## The Vision: Wizard Duel Arena

### Theme
Two wizards facing off, casting spells at each other's towers. Blocking is passive (position your wizard), but you can't block everything when overwhelmed.

### Game Layers
| Layer | Description |
|-------|-------------|
| **Core** | Wizard duel (casting, blocking, mana, multi-projectile) |
| **Round** | 30-60 sec bout, damage to tower = round win |
| **Match** | Tug-of-war across 5 zones |
| **Progression** | Pick abilities/upgrades between rounds |

### The 5 Zones (Tug-of-War)
```
[YOUR CORE] - [YOUR TOWER] - [MIDFIELD] - [ENEMY TOWER] - [ENEMY CORE]
     1              2            3              4              5
```
- Win a bout = push forward one zone
- Lose = get pushed back
- Destroy enemy core to win match

### Ability System (Planned)
- Pick 4 abilities pre-match
- Mana limits casting (regenerates)
- Cooldowns per ability
- Types: Offensive (Fireball, Ice Bolt), Modifiers (Triple Shot), Utility (Freeze), Defensive (Shield)

### Intro Sequence (Planned)
1. Classic Atari Pong look (2D)
2. Camera rotates revealing 3D
3. Fantasy world fades in

---

## Current Implementation (Pong Prototype)

### Controls
- **W / Arrow Up**: Move paddle up (cancels cast if casting)
- **S / Arrow Down**: Move paddle down (cancels cast if casting)
- **SPACE**: Parry (grants 3 mana)
- **1**: Cast Fireball (1s cast time, 5s cooldown, 1 mana, damage scales with volleys)
- **2**: Cast Frost Bolt (14s cooldown, 2 mana, freezes enemy 1s)
- ~~**3**: Gravity Well~~ (commented out for rework)

### Mana System
- **Max Mana**: 3 (displayed as 3 segments above ability bar)
- **Passive Regen**: +1 mana every 5 seconds
- **Block**: +1 mana
- **Parry**: +3 mana (fills entire bar)
- **Starting Mana**: 1 (enough for initial fireball)
- Spells require both cooldown AND mana to cast

### Key Mechanics
1. **Parry System**: SPACE near ball (tight timing!) = boost + straight shot + color change
2. **Directional Parry**: Hold W/S while parrying to aim
3. **AI Parry**: AI parries when you're out of position (strategic)
4. **Visual Effects**: TrailMesh, quaternion rotation, squash-and-stretch, smear frames

### Key Constants
```javascript
const parryWindow = 1.0;       // Tight timing
const parryBoost = 1.4;        // Speed multiplier
const maxParrySpeed = 28;      // Hard velocity cap
const paddleSpeed = 20;
const aiSpeed = 11;
const maxTowerHealth = 20;     // Matches brick count
const maxMana = 3;             // Holy Power style segments
const manaRegenTime = 5;       // Passive regen: 1 mana every 5s

// Abilities now defined in AbilityRegistry with full config
// See AbilityRegistry section below for complete structure
```

### Damage Scaling
```javascript
// Volley count determines damage
// 0 volleys = 1 damage, 1-2 = 2 damage, 3+ = 3 damage (capped)
const damage = proj.volleyCount >= 3 ? 3 : (proj.volleyCount >= 1 ? 2 : 1);
```

---

## Modular Ability System (AbilityRegistry)

The game now has a **modular ability registry** that makes adding new abilities straightforward. Each ability is defined with all its properties in one place.

### Adding a New Ability

1. **Add to AbilityRegistry** in `index.html`:
```javascript
AbilityRegistry.lightning = {
    // Identity
    id: 'lightning',
    name: 'Chain Lightning',
    description: 'Strikes the enemy and chains to nearby projectiles.',
    icon: '⚡',
    element: 'lightning',  // fire, ice, lightning, arcane, nature, shadow

    // Core Stats
    manaCost: 2,
    cooldown: 8,

    // Projectile Properties
    projectile: {
        speed: 30,
        size: 0.3,
        damage: 1,
        damageType: 'lightning',
        canParry: true,
        canBlock: true,
        destroyedOnPaddleHit: false,
        damageScaling: { enabled: false }
    },

    // Visual Config (see existing abilities for full options)
    visuals: {
        meshType: 'sphere',
        coreColor: { r: 1, g: 1, b: 0.5 },
        // ... glow, trail, light, particles
    },

    // Sound Config
    sounds: {
        cast: 'lightningSfx',
        loop: 'lightningLoop',
        impact: 'lightningImpact'
    },

    // Special Effects
    effects: [
        { type: 'chain', targets: 2, description: 'Chains to 2 nearby targets' }
    ],

    // Tooltip
    tooltip: {
        stats: [
            { icon: '💥', label: 'Damage', value: '1', type: 'damage' },
            // ...
        ],
        effects: ['Chains to <span class="highlight">2 targets</span>']
    }
};
```

2. **Add HTML slot** in ability bar (or use dynamic generation)
3. **Add spawner function** (or use generic spawner with AbilityRegistry data)
4. **Wire up keybind and click handler**

### Ability Properties Reference

| Property | Type | Description |
|----------|------|-------------|
| `element` | string | fire, ice, lightning, arcane, nature, shadow |
| `projectile.canParry` | bool | Can be parried by player |
| `projectile.canBlock` | bool | Can be blocked by paddle |
| `projectile.destroyedOnPaddleHit` | bool | Destroyed on contact (like frostbolt) |
| `projectile.damageScaling.enabled` | bool | Damage increases with volleys |
| `visuals.glowPulse` | bool | Glow size animates |
| `visuals.rotateCore` | bool | Core mesh rotates (crystals) |
| `visuals.lightFlicker` | bool | Light intensity fluctuates |
| `effects[].type` | string | freeze, chain, burn, noDamage, unblockable, etc. |

### Helper Functions

```javascript
getAbility(id)           // Get ability definition
getAbilitiesByElement(e) // Get all abilities of element
calculateDamage(id, v)   // Calculate damage with volley count
generateTooltipHTML(id)  // Generate tooltip from definition
canCastAbility(caster, id) // Check mana + cooldown
listAbilities()          // Console log all abilities
```

### Tooltips

Abilities have rich tooltips that appear on hover. Tooltips show:
- Name, icon, element badge
- Description
- Stats (damage, mana, cooldown, speed)
- Special effects

---

## Phase 1 Priority (Next Steps)

| Priority | Task | Status |
|----------|------|--------|
| 1 | More spell types | Lightning? Shield? |
| 2 | Wizard models | Replace paddles with characters |
| 3 | Visual polish | Particle effects, better UI |

**Completed**: Multi-projectile, tower health, active casting, cooldowns, volley damage scaling, sound system, Frost Bolt spell, volume control, mana system (block = +1, parry = +3, passive +1/5s), **AbilityRegistry** (modular ability definitions), **tooltips** (hover abilities for details), **enhanced visuals** (fireball trail/glow, frostbolt crystals, ice block freeze effect), **cast time system** (1s cast, movement cancels), **AI cast/mana bars**, **symmetrical UI**, **texture system** (gates, floor), **character model loading** (FBX, animations)

**Performance note**: Keep bullet-heaven in mind - many projectiles at once. No extra particle systems per projectile.

---

## Session Handoff Protocol
Before ending a session:
1. Update DevLog.md with what was done
2. Update Tasks.md with completed/new tasks
3. Update this file's "Current State" section
4. Note any pending work or decisions needed

## Important Notes for AI
- Read Tasks.md for current priorities and full roadmap
- Check DevLog.md for recent changes and context
- Architecture.md has code patterns and future plans
- After major changes, update documentation
