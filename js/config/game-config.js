/**
 * Volleybolt - Game Configuration
 *
 * Core game constants and configuration values.
 * These are the tunable parameters that define game feel and balance.
 */

// ============================================================
// SCORING & WIN CONDITIONS
// ============================================================
export const SCORING = {
    winningScore: 5,
    maxTowerHealth: 20
};

// ============================================================
// PHYSICS CONSTANTS
// ============================================================
export const PHYSICS = {
    gravity: -30,
    bounceRetention: 0,
    tableY: 0.6,
    maxBounceVel: 7,
    initialBallSpeed: 12
};

// ============================================================
// PARRY SYSTEM
// ============================================================
export const PARRY = {
    window: 0.5,
    boost: 1.4,
    maxSpeed: 28,
    successCooldown: 0.2,
    failCooldown: 3.0,
    hitboxExtend: 2.5
};

// ============================================================
// MANA SYSTEM
// ============================================================
export const MANA = {
    max: 3,
    regenTime: 3,
    startingMana: 1,
    blockGain: 0.5,
    parryGain: 3
};

// ============================================================
// MOVEMENT
// ============================================================
export const MOVEMENT = {
    paddleSpeed: 20,
    aiSpeed: 11,
    momentumFactor: 0.4
};

// ============================================================
// NETCODE (P2P Multiplayer)
// ============================================================
export const NETCODE = {
    maxRollbackFrames: 8,
    inputDelay: 2,
    tickRate: 60,
    tickMs: 1000 / 60
};

// ============================================================
// LEGACY EXPORTS - Individual constants for backward compatibility
// ============================================================
export const winningScore = SCORING.winningScore;
export const maxTowerHealth = SCORING.maxTowerHealth;
export const gravity = PHYSICS.gravity;
export const bounceRetention = PHYSICS.bounceRetention;
export const tableY = PHYSICS.tableY;
export const maxBounceVel = PHYSICS.maxBounceVel;
export const initialBallSpeed = PHYSICS.initialBallSpeed;
export const parryWindow = PARRY.window;
export const parryBoost = PARRY.boost;
export const maxParrySpeed = PARRY.maxSpeed;
export const parrySuccessCooldown = PARRY.successCooldown;
export const parryFailCooldown = PARRY.failCooldown;
export const parryHitboxExtend = PARRY.hitboxExtend;
export const maxMana = MANA.max;
export const manaRegenTime = MANA.regenTime;
export const paddleSpeed = MOVEMENT.paddleSpeed;
export const aiSpeed = MOVEMENT.aiSpeed;

// ============================================================
// BACKWARD COMPATIBILITY - Expose on window for inline scripts
// ============================================================
if (typeof window !== 'undefined') {
    // Grouped configs
    window.GAME_CONFIG = {
        SCORING,
        PHYSICS,
        PARRY,
        MANA,
        MOVEMENT,
        NETCODE
    };

    // Legacy individual constants
    window.winningScore = winningScore;
    window.maxTowerHealth = maxTowerHealth;
    window.gravity = gravity;
    window.bounceRetention = bounceRetention;
    window.tableY = tableY;
    window.maxBounceVel = maxBounceVel;
    window.initialBallSpeed = initialBallSpeed;
    window.parryWindow = parryWindow;
    window.parryBoost = parryBoost;
    window.maxParrySpeed = maxParrySpeed;
    window.parrySuccessCooldown = parrySuccessCooldown;
    window.parryFailCooldown = parryFailCooldown;
    window.parryHitboxExtend = parryHitboxExtend;
    window.maxMana = maxMana;
    window.manaRegenTime = manaRegenTime;
    window.paddleSpeed = paddleSpeed;
    window.aiSpeed = aiSpeed;
}
