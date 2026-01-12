/**
 * Volleybolt - Ability Registry
 *
 * Modular ability definitions and helper functions.
 * Each ability is defined with all its properties in one place.
 */

// ============================================================
// ABILITY REGISTRY
// ============================================================

export const AbilityRegistry = {
    // ========== FIREBALL ==========
    fireball: {
        // === IDENTITY ===
        id: 'fireball',
        name: 'Fireball',
        description: 'Channel a blazing fireball that damages the enemy tower. Damage increases with volleys. Rooted while casting.',
        icon: '🔥',
        element: 'fire',

        // === CORE STATS ===
        manaCost: 1,
        cooldown: 0,
        castTime: 1.0,
        castType: 'channel',
        rootWhileCasting: true,
        pushbackOnHit: 0.3,

        // === PROJECTILE PROPERTIES ===
        projectile: {
            speed: 12,
            size: 0.45,
            damage: 1,
            damageType: 'fire',
            canParry: true,
            canBlock: true,
            destroyedOnPaddleHit: false,
            damageScaling: {
                enabled: true,
                thresholds: [
                    { volleys: 0, damage: 1 },
                    { volleys: 1, damage: 2 },
                    { volleys: 3, damage: 3 }
                ]
            }
        },

        // === VISUAL CONFIG ===
        visuals: {
            meshType: 'sphere',
            coreColor: { r: 1, g: 0.8, b: 0.3 },
            emissiveColor: { r: 1, g: 0.5, b: 0.1 },

            glowEnabled: true,
            glowColor: { r: 1, g: 0.4, b: 0.05 },
            glowSize: 0.8,
            glowAlpha: 0.3,
            glowPulse: true,

            trailEnabled: true,
            trailWidth: 0.25,
            trailLength: 30,
            trailColor: { r: 1, g: 0.3, b: 0.05 },
            trailAlpha: 0.6,

            lightEnabled: true,
            lightColor: { r: 1, g: 0.6, b: 0.2 },
            lightIntensity: 0.8,
            lightRange: 8,
            lightFlicker: true,

            particles: [
                {
                    name: 'core',
                    count: 80,
                    colors: [
                        { r: 1, g: 0.9, b: 0.5, a: 1 },
                        { r: 1, g: 0.5, b: 0.1, a: 1 }
                    ],
                    colorDead: { r: 1, g: 0.2, b: 0, a: 0 },
                    sizeRange: [0.2, 0.5],
                    lifetimeRange: [0.05, 0.15],
                    emitRate: 80,
                    speed: [1, 2],
                    gravity: { x: 0, y: 0, z: 0 }
                },
                {
                    name: 'trail',
                    count: 50,
                    colors: [
                        { r: 1, g: 0.4, b: 0.1, a: 0.8 },
                        { r: 0.8, g: 0.2, b: 0.05, a: 0.6 }
                    ],
                    colorDead: { r: 0.3, g: 0.1, b: 0, a: 0 },
                    sizeRange: [0.3, 0.6],
                    lifetimeRange: [0.15, 0.35],
                    emitRate: 50,
                    speed: [1, 2.5],
                    emitBehind: true,
                    gravity: { x: 0, y: 1, z: 0 }
                }
            ]
        },

        // === SOUND CONFIG ===
        sounds: {
            cast: 'fireballCast',
            loop: 'fireballLoop',
            loopVolume: 0.12,
            impact: 'fireballImpact',
            approaching: 'fireballApproaching'
        },

        // === SPECIAL EFFECTS ===
        effects: [
            {
                type: 'volleyDamageBonus',
                description: 'Volley bonus: +1 damage per 1-2 volleys'
            }
        ],

        // === TOOLTIP ===
        tooltip: {
            stats: [
                { icon: '💥', label: 'Damage', value: '1-3', type: 'damage' },
                { icon: '💧', label: 'Mana', value: '1', type: 'mana' },
                { icon: '⏳', label: 'Cast', value: '1s', type: 'castTime' },
                { icon: '💨', label: 'Speed', value: 'Medium', type: 'speed' }
            ],
            effects: [
                'Volley bonus: <span class="highlight">+1 damage</span> per 1-2 volleys',
                'Can be parried and blocked'
            ]
        }
    },

    // ========== FROST BOLT ==========
    frostbolt: {
        id: 'frostbolt',
        name: 'Frostbolt',
        description: 'Launch a piercing shard of ice. Freezes the enemy on contact, trapping them in a block of ice.',
        icon: '❄️',
        element: 'ice',

        manaCost: 2,
        cooldown: 14,

        projectile: {
            speed: 22,
            size: 0.4,
            damage: 0,
            damageType: 'ice',
            canParry: true,
            canBlock: true,
            destroyedOnPaddleHit: true,
            damageScaling: { enabled: false }
        },

        visuals: {
            meshType: 'icosphere',
            coreColor: { r: 0.7, g: 0.9, b: 1 },
            emissiveColor: { r: 0.4, g: 0.7, b: 0.95 },
            specular: { color: { r: 1, g: 1, b: 1 }, power: 64 },

            glowEnabled: true,
            glowColor: { r: 0.3, g: 0.6, b: 0.9 },
            glowSize: 0.7,
            glowAlpha: 0.25,
            glowPulse: true,

            trailEnabled: true,
            trailWidth: 0.18,
            trailLength: 25,
            trailColor: { r: 0.4, g: 0.7, b: 1 },
            trailAlpha: 0.5,

            lightEnabled: true,
            lightColor: { r: 0.6, g: 0.85, b: 1 },
            lightIntensity: 0.7,
            lightRange: 7,
            lightFlicker: true,
            flickerSpeed: 15,

            rotateCore: true,
            rotateSpeed: 3,

            particles: [
                {
                    name: 'core',
                    count: 60,
                    colors: [
                        { r: 0.9, g: 0.95, b: 1, a: 1 },
                        { r: 0.5, g: 0.8, b: 1, a: 1 }
                    ],
                    colorDead: { r: 0.3, g: 0.5, b: 0.7, a: 0 },
                    sizeRange: [0.08, 0.2],
                    lifetimeRange: [0.1, 0.2],
                    emitRate: 60,
                    speed: [0.8, 1.5]
                },
                {
                    name: 'mist',
                    count: 40,
                    colors: [
                        { r: 0.6, g: 0.8, b: 1, a: 0.6 },
                        { r: 0.4, g: 0.6, b: 0.9, a: 0.4 }
                    ],
                    colorDead: { r: 0.2, g: 0.3, b: 0.5, a: 0 },
                    sizeRange: [0.25, 0.5],
                    lifetimeRange: [0.2, 0.4],
                    emitRate: 40,
                    speed: [0.5, 1.5],
                    emitBehind: true,
                    gravity: { x: 0, y: -0.5, z: 0 }
                },
                {
                    name: 'sparkles',
                    count: 20,
                    colors: [
                        { r: 1, g: 1, b: 1, a: 1 },
                        { r: 0.8, g: 0.95, b: 1, a: 0.8 }
                    ],
                    colorDead: { r: 0.5, g: 0.7, b: 1, a: 0 },
                    sizeRange: [0.05, 0.12],
                    lifetimeRange: [0.3, 0.6],
                    emitRate: 20,
                    speed: [0.5, 1.2],
                    gravity: { x: 0, y: -2, z: 0 }
                }
            ]
        },

        sounds: {
            cast: 'frostboltCast',
            loop: 'frostboltLoop',
            loopVolume: 0.1,
            impact: 'frozen'
        },

        effects: [
            {
                type: 'freeze',
                duration: 1.0,
                description: 'Freezes enemy for 1 second'
            },
            {
                type: 'noDamage',
                description: 'Does not damage towers'
            }
        ],

        tooltip: {
            stats: [
                { icon: '💥', label: 'Damage', value: '0', type: 'damage' },
                { icon: '💧', label: 'Mana', value: '2', type: 'mana' },
                { icon: '⏱️', label: 'Cooldown', value: '14s', type: 'cooldown' },
                { icon: '💨', label: 'Speed', value: 'Fast', type: 'speed' }
            ],
            effects: [
                'Freezes enemy for <span class="highlight">1 second</span>',
                'Destroyed on paddle contact',
                'Does not damage towers'
            ]
        }
    },

    // ========== GRAVITY WELL ==========
    gravity: {
        id: 'gravity',
        name: 'Gravity Well',
        description: 'Create a gravity barrier that captures incoming projectiles. Press again to launch them back as a devastating sphere.',
        icon: '🌀',
        element: 'arcane',

        manaCost: 3,
        cooldown: 15,

        abilityType: 'twoPhase',
        phases: {
            barrier: {
                duration: 2.5,
                maxCapture: 3,
                slowRadius: 4,
                slowFactor: 0.4
            },
            sphere: {
                speed: 10,
                damagePerBall: 2,
                canParry: false,
                canBlock: false
            }
        },

        visuals: {
            barrier: {
                color: { r: 0.4, g: 0.1, b: 0.5 },
                pulseSpeed: 2
            },
            sphere: {
                coreColor: { r: 0.2, g: 0.05, b: 0.3 },
                glowColor: { r: 0.6, g: 0.2, b: 0.8 }
            }
        },

        sounds: {
            cast: 'gravityCast',
            capture: 'gravityCapture',
            release: 'gravityRelease'
        },

        effects: [
            {
                type: 'capture',
                maxCount: 3,
                description: 'Captures up to 3 projectiles'
            },
            {
                type: 'unblockable',
                description: 'Sphere cannot be blocked or parried'
            }
        ],

        tooltip: {
            stats: [
                { icon: '💥', label: 'Damage', value: '2/ball', type: 'damage' },
                { icon: '💧', label: 'Mana', value: '3', type: 'mana' },
                { icon: '⏱️', label: 'Cooldown', value: '15s', type: 'cooldown' },
                { icon: '⏳', label: 'Duration', value: '2.5s', type: 'duration' }
            ],
            effects: [
                'Captures up to <span class="highlight">3 projectiles</span>',
                'Two-phase ability: Barrier → Sphere',
                'Sphere cannot be blocked or parried'
            ]
        }
    }
};

// ============================================================
// ABILITY HELPER FUNCTIONS
// ============================================================

/**
 * Get ability definition by ID
 */
export function getAbility(id) {
    return AbilityRegistry[id] || null;
}

/**
 * Get all abilities of a specific element
 */
export function getAbilitiesByElement(element) {
    return Object.values(AbilityRegistry).filter(a => a.element === element);
}

/**
 * Calculate damage based on volley count
 */
export function calculateDamage(abilityId, volleyCount) {
    const ability = getAbility(abilityId);
    if (!ability || !ability.projectile) return 0;

    const proj = ability.projectile;
    if (!proj.damageScaling || !proj.damageScaling.enabled) {
        return proj.damage;
    }

    let damage = proj.damage;
    for (const threshold of proj.damageScaling.thresholds) {
        if (volleyCount >= threshold.volleys) {
            damage = threshold.damage;
        }
    }
    return damage;
}

/**
 * Generate tooltip HTML from ability definition
 */
export function generateTooltipHTML(abilityId) {
    const ability = getAbility(abilityId);
    if (!ability) return '';

    let html = `
        <div class="tooltip-header">
            <span class="tooltip-icon">${ability.icon}</span>
            <span class="tooltip-title">${ability.name}</span>
            <span class="tooltip-element ${ability.element}">${ability.element}</span>
        </div>
        <div class="tooltip-description">${ability.description}</div>
        <div class="tooltip-stats">
    `;

    for (const stat of ability.tooltip.stats) {
        html += `
            <div class="tooltip-stat">
                <span class="tooltip-stat-icon">${stat.icon}</span>
                <span class="tooltip-stat-label">${stat.label}:</span>
                <span class="tooltip-stat-value ${stat.type}">${stat.value}</span>
            </div>
        `;
    }

    html += '</div><div class="tooltip-effects">';

    for (const effect of ability.tooltip.effects) {
        html += `
            <div class="tooltip-effect">
                <span class="tooltip-effect-icon">▸</span>
                <span class="tooltip-effect-text">${effect}</span>
            </div>
        `;
    }

    html += '</div>';
    return html;
}

/**
 * Get visual color as object with r, g, b properties
 */
export function getColor3(colorObj) {
    return { r: colorObj.r, g: colorObj.g, b: colorObj.b };
}

/**
 * Log available abilities (debug)
 */
export function listAbilities() {
    console.log('=== REGISTERED ABILITIES ===');
    for (const [id, ability] of Object.entries(AbilityRegistry)) {
        console.log(`${ability.icon} ${ability.name} (${id}) - ${ability.element} - ${ability.manaCost} mana`);
    }
}

// ============================================================
// BACKWARD COMPATIBILITY - Expose on window for inline scripts
// ============================================================
if (typeof window !== 'undefined') {
    window.AbilityRegistry = AbilityRegistry;
    window.getAbility = getAbility;
    window.getAbilitiesByElement = getAbilitiesByElement;
    window.calculateDamage = calculateDamage;
    window.generateTooltipHTML = generateTooltipHTML;
    window.getColor3 = getColor3;
    window.listAbilities = listAbilities;
}
