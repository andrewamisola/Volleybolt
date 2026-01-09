# Architecture - Wizard Duel Arena

## Project Structure
```
BabylonPong/
├── index.html          # Main game file (all code here)
├── ai.context.md       # AI session starter - READ FIRST
└── docs/
    ├── Tasks.md        # Feature/bug tracking
    ├── DevLog.md       # Daily development log
    ├── Architecture.md # This file
    └── Debug.md        # Test scenarios
```

## Tech Stack
- **Engine**: Babylon.js 7.x (loaded from CDN)
- **Physics**: Manual implementation (not using Havok for gameplay)
- **Rendering**: WebGL via Babylon.js
- **Build**: None - single HTML file runs directly in browser

---

## Current Implementation (Pong Prototype)

### Game Layout
```
        TOP OF SCREEN (negative Z)
    ┌─────────────────────────────────┐
    │                                 │
    │  [AI PADDLE - RED]              │
    │        (right side)             │
    │                                 │
    │           (ball)                │
    │                                 │
    │  [PLAYER PADDLE - BLUE]         │
    │        (left side)              │
    │                                 │
    └─────────────────────────────────┘
       BOTTOM OF SCREEN (positive Z)

Camera: ArcRotateCamera looking down at angle
```

### Coordinate System
- **X-axis**: Left (-) to Right (+) - Ball travel direction
- **Z-axis**: Bottom (+) to Top (-) - Paddle movement direction
- **Y-axis**: Down (-) to Up (+) - Ball bounce direction

### Key Constants (Current)
| Constant | Value | Purpose |
|----------|-------|---------|
| initialBallSpeed | 12 | Starting ball speed |
| gravity | -30 | Downward acceleration |
| bounceRetention | 0 | Velocity kept after bounce (0 = one bounce) |
| tableY | 0.25 | Ground/table Y position |
| maxBounceVel | 7 | Max upward velocity from bounce |
| parryWindow | 1.0 | Distance from paddle for valid parry |
| parryBoost | 1.25 | Speed multiplier on parry |
| maxParrySpeed | 18 | Hard cap on parried ball speed |
| paddleSpeed | 20 | Player paddle movement speed |
| aiSpeed | 11 | AI paddle movement speed |
| maxHitHeight | 0.8 | Ball must be below this to collide |

---

## Visual Effects System

### Ball Stretch (Squash-and-Stretch)
```javascript
// Velocity computed from position delta
const velocity = ball.position.subtract(lastBallPos).scale(1 / dt);
const speed = velocity.length();

// Quaternion rotation toward travel direction
const dir = velocity.normalize();
ball.rotationQuaternion = BABYLON.Quaternion.FromLookDirectionLH(dir, BABYLON.Vector3.Up());

// Stretch along forward axis (Z after rotation)
const stretchFactor = BABYLON.Scalar.Clamp(speed / 20, 1, 2.0);
const compress = 1 / Math.sqrt(stretchFactor);
ball.scaling.set(compress, compress, stretchFactor);
```

### TrailMesh
```javascript
trail = new BABYLON.TrailMesh("trail", ball, scene, 0.15, 20, true);
trailMat.alpha = BABYLON.Scalar.Clamp(speed / 35, 0.1, 0.5);

// Color matches parry type
if (parriedBy === 'player') {
    trailMat.emissiveColor = new BABYLON.Color3(0.5, 0.8, 1);  // Blue
} else {
    trailMat.emissiveColor = new BABYLON.Color3(1, 0.3, 0.5);  // Red/magenta
}
```

### Smear Frame (Cartoon Impact)
```javascript
const smearFrame = () => {
    if (ball.scaling.z < 3) {
        ball.scaling.z *= 1.6;
        scene.onBeforeRenderObservable.addOnce(() => {
            ball.scaling.z /= 1.6;
        });
    }
};
// Called on parry impact
```

---

## Parry System

### Player Parry
1. Player presses SPACE
2. Check: Ball coming toward player (ballVelX < 0)
3. Check: Ball within parryWindow (1.0) distance from paddle
4. Check: Ball within paddle's Z range
5. If all pass:
   - Boost ballSpeed (capped at maxParrySpeed)
   - Set straight trajectory (ballVelY = 0)
   - Apply directional aim if W/S held
   - Trigger visual effects (flash, smear, color change)

### AI Parry
- Triggers when player paddle is out of position
- 70% chance if player > 2.5 units from ball's Z
- 30% chance if player > 1.5 units
- 0% if player is well-positioned
- Aims toward the side player ISN'T on

### Parry Visual States
| State | Ball Color | Trail Color |
|-------|------------|-------------|
| Normal | Orange | Orange (hidden) |
| Player Parried | Blue/White | Blue |
| AI Parried | Red/Magenta | Red/Magenta |

---

## Future Architecture (Wizard Duel)

### Multi-Projectile System
```javascript
// Replace single ball with spell array
const spells = [];

function createSpell(caster, type, position, direction) {
    const spell = {
        mesh: createSpellMesh(type),
        velocity: direction.scale(spellSpeed),
        owner: caster,
        type: type,
        // ... other properties
    };
    spells.push(spell);
    return spell;
}

// Game loop iterates all spells
spells.forEach(spell => {
    updateSpellPosition(spell);
    checkSpellCollisions(spell);
});
```

### Resource System
```javascript
const player = {
    mana: 100,
    maxMana: 100,
    manaRegen: 5,  // per second
    abilities: [
        { name: 'Fireball', cost: 20, cooldown: 2.0, currentCooldown: 0 },
        // ...
    ]
};

function castSpell(caster, abilityIndex) {
    const ability = caster.abilities[abilityIndex];
    if (caster.mana >= ability.cost && ability.currentCooldown <= 0) {
        caster.mana -= ability.cost;
        ability.currentCooldown = ability.cooldown;
        createSpell(caster, ability.name, ...);
    }
}
```

### Tower Health System
```javascript
const towers = {
    player: { hp: 100, maxHp: 100, mesh: null },
    ai: { hp: 100, maxHp: 100, mesh: null }
};

function onSpellPassedDefender(spell, side) {
    towers[side].hp -= spell.damage;
    updateTowerVisuals(towers[side]);
    if (towers[side].hp <= 0) {
        endRound(winner = opposingSide);
    }
}
```

### Match/Zone System
```javascript
const match = {
    currentZone: 3,  // Start at midfield
    zones: [
        { name: 'Player Core', position: 1 },
        { name: 'Player Tower', position: 2 },
        { name: 'Midfield', position: 3 },
        { name: 'AI Tower', position: 4 },
        { name: 'AI Core', position: 5 }
    ]
};

function onRoundEnd(winner) {
    if (winner === 'player') {
        match.currentZone++;
    } else {
        match.currentZone--;
    }
    showLevelUpScreen();
    transitionToZone(match.currentZone);
}
```

---

## Implementation Notes

### Why Manual Physics?
Babylon.js physics (Havok) was initially used but removed because:
- Physics bodies blocked direct position manipulation
- Simpler to implement Pong physics manually
- More control over exact behavior

### Keyboard Input
Using `e.code` instead of `e.key` for:
- Consistent behavior regardless of keyboard layout
- Works with AZERTY, QWERTY, etc.
- Example: `keys['KeyW']` instead of `keys['w']`

### Particle System (Fireball)
- Emitter attached to ball mesh
- Orange/yellow colors normally
- Blue colors when player parried
- Red/magenta when AI parried
- Point light follows ball for glow effect
