// ============================================================
// VOLLEYBOLT - Shared configuration and ability registry
// Single source of truth for all tuning values.
// ============================================================

export const TICK_RATE = 60;
export const DT = 1 / TICK_RATE;
export const MAX_FRAME_DT = 0.1;     // Clamp wall-clock dt (tab-out protection)
export const MAX_TICKS_PER_FRAME = 6; // Spiral-of-death guard

// Arena
export const TABLE_W = 20;            // X axis (left-right)
export const TABLE_D = 12;            // Z axis (up-down on screen)
export const GOAL_X = TABLE_W / 2 + 1;
export const GATE_X = TABLE_W / 2 + 1.2;
export const PADDLE_X = TABLE_W / 2 - 1.5;     // |x| of each wizard
export const PADDLE_BOUND = TABLE_D / 2 - 1.5;
export const WALL_Z = TABLE_D / 2 - 0.5;       // Projectile bounce plane

// Physics
export const TABLE_Y = 0.6;          // Projectile float height
export const GRAVITY_Y = -30;
export const BALL_R = 0.25;
export const MAX_HIT_HEIGHT = 0.8;

// Wizards
export const PADDLE_SPEED = 20;
export const AI_SPEED_MULT = 0.55;   // AI moves at 55% of player speed (legacy 11 vs 20)
export const PADDLE_HALF_D = 1.25;
export const PADDLE_HALF_W = 0.2;
// Perspective correction: expand hitbox based on character height and camera angle
export const PERSPECTIVE_Z = 0.75;

// Parry
export const PARRY_WINDOW = 1.0;
export const PARRY_BOOST = 1.4;
export const MAX_PARRY_SPEED = 28;
export const PARRY_LOCK = 0.5;       // Seconds between successful parries
export const HITSTOP_TICKS = 3;      // Sim freeze on successful parry (~50ms)

// Resources
export const MAX_MANA = 3;
export const MANA_REGEN_TIME = 5;    // Seconds per 1 mana
export const STARTING_MANA = 1;
export const BLOCK_MANA = 1;
export const PARRY_MANA = 3;

// Match structure
export const MAX_GATE_HP = 20;
export const WINNING_SCORE = 5;
export const ROUND_TIME = 60;        // Seconds; tie at 0 -> sudden death
export const ROUND_END_DELAY = 2.5;
export const MATCH_END_DELAY = 3.0;

// Networking
export const INPUT_DELAY_TICKS = 4;  // Lockstep input delay (~67ms)

// ============================================================
// ABILITY REGISTRY
// ============================================================
export const ABILITIES = {
    fireball: {
        id: 'fireball',
        name: 'Fireball',
        icon: '\u{1F525}',
        element: 'fire',
        manaCost: 1,
        cooldown: 5,
        castTime: 1.0,            // Channeled; movement cancels with refund
        rootWhileCasting: true,
        pushbackOnHit: 0.3,       // Seconds added to cast when blocked while casting
        speed: 12,
        canParry: true,
        destroyedOnPaddleHit: false,
        // Volley damage scaling: 0 volleys = 1, 1-2 = 2, 3+ = 3
        volleyDamage: [1, 2, 2, 3],
        tooltip: {
            description: 'Channel a blazing fireball. Damage increases with volleys. Rooted while casting.',
            stats: [
                { icon: '\u{1F4A5}', label: 'Damage', value: '1-3', type: 'damage' },
                { icon: '\u{1F4A7}', label: 'Mana', value: '1', type: 'mana' },
                { icon: '\u{23F3}', label: 'Cast', value: '1s', type: 'cooldown' },
                { icon: '\u{1F4A8}', label: 'Speed', value: 'Medium', type: 'speed' }
            ],
            effects: [
                'Volley bonus: <span class="highlight">+1 damage</span> per 1-2 volleys',
                'Can be parried and blocked'
            ]
        }
    },
    frostbolt: {
        id: 'frostbolt',
        name: 'Frost Bolt',
        icon: '\u{2744}\u{FE0F}',
        element: 'ice',
        manaCost: 2,
        cooldown: 14,
        castTime: 0,              // Instant
        speed: 22,
        freeze: 1.0,
        canParry: true,
        destroyedOnPaddleHit: true,
        volleyDamage: [0],
        tooltip: {
            description: 'Launch a piercing shard of ice. Freezes the enemy on contact.',
            stats: [
                { icon: '\u{1F4A5}', label: 'Damage', value: '0', type: 'damage' },
                { icon: '\u{1F4A7}', label: 'Mana', value: '2', type: 'mana' },
                { icon: '\u{23F1}\u{FE0F}', label: 'Cooldown', value: '14s', type: 'cooldown' },
                { icon: '\u{1F4A8}', label: 'Speed', value: 'Fast', type: 'speed' }
            ],
            effects: [
                'Freezes enemy for <span class="highlight">1 second</span>',
                'Interrupts enemy casting',
                'Destroyed on contact, no tower damage'
            ]
        }
    },
    lightning: {
        id: 'lightning',
        name: 'Lightning',
        icon: '\u{26A1}',
        element: 'lightning',
        manaCost: 1,
        cooldown: 8,
        castTime: 0,              // Instant
        speed: 30,
        canParry: false,          // Cannot be parried - punishes turtling
        destroyedOnPaddleHit: false,
        volleyDamage: [1],        // Always 1, no scaling
        tooltip: {
            description: 'A crackling bolt of lightning. Too fast to parry - can only be blocked.',
            stats: [
                { icon: '\u{1F4A5}', label: 'Damage', value: '1', type: 'damage' },
                { icon: '\u{1F4A7}', label: 'Mana', value: '1', type: 'mana' },
                { icon: '\u{23F1}\u{FE0F}', label: 'Cooldown', value: '8s', type: 'cooldown' },
                { icon: '\u{1F4A8}', label: 'Speed', value: 'Very Fast', type: 'speed' }
            ],
            effects: [
                '<span class="highlight">Cannot be parried</span>',
                'Great for interrupting enemy casts',
                'No volley damage scaling'
            ]
        }
    }
};

export function volleyDamage(abilityId, volleyCount, bonus = 0) {
    const table = ABILITIES[abilityId] ? ABILITIES[abilityId].volleyDamage : [1];
    const dmg = table[Math.min(volleyCount, table.length - 1)];
    return dmg > 0 ? dmg + bonus : 0;
}

// ============================================================
// BETWEEN-ROUND UPGRADES
// ============================================================
export const UPGRADES = [
    {
        id: 'mana', name: 'Arcane Battery', icon: '\u{1F537}',
        desc: '+1 maximum mana',
        apply: (w) => { w.stats.maxMana += 1; }
    },
    {
        id: 'pyro', name: 'Pyromancer', icon: '\u{1F525}',
        desc: 'Fireball deals +1 damage',
        apply: (w) => { w.stats.fireballDmg += 1; }
    },
    {
        id: 'frost', name: 'Deep Freeze', icon: '\u{2744}\u{FE0F}',
        desc: 'Your freezes last +0.5s',
        apply: (w) => { w.stats.freezeBonus += 0.5; }
    },
    {
        id: 'swift', name: 'Swift Robes', icon: '\u{1F4A8}',
        desc: '+15% movement speed',
        apply: (w) => { w.stats.moveSpeed *= 1.15; }
    },
    {
        id: 'reflex', name: 'Battle Reflexes', icon: '\u{1F6E1}\u{FE0F}',
        desc: '+30% parry window',
        apply: (w) => { w.stats.parryWindow *= 1.3; }
    },
    {
        id: 'chrono', name: 'Chronomancer', icon: '\u{23F3}',
        desc: '-20% spell cooldowns',
        apply: (w) => { w.stats.cooldownMult *= 0.8; }
    },
    {
        id: 'spring', name: 'Mana Spring', icon: '\u{1F30A}',
        desc: 'Mana regenerates 25% faster',
        apply: (w) => { w.stats.regenMult *= 0.75; }
    },
    {
        id: 'haste', name: 'Quick Cast', icon: '\u{2728}',
        desc: 'Fireball casts 25% faster',
        apply: (w) => { w.stats.castTimeMult *= 0.75; }
    }
];
