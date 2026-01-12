/**
 * Volleybolt - Game Systems
 *
 * Core game mechanics including:
 * - Combatant system (create, reset, helpers)
 * - Mana system (gain, spend)
 * - Casting system (start, cancel, pushback)
 * - Ability definitions
 */

// ============================================================
// COMBATANT FACTORY
// ============================================================

/**
 * Create a new combatant object
 */
export function createCombatant(side) {
    const maxTowerHealth = window.maxTowerHealth || 20;

    return {
        // Identity
        side: side,                      // 'left' or 'right'
        inputSource: 'none',             // 'local', 'ai', 'network'
        isLocalPlayer: false,

        // Core State
        score: 0,
        towerHealth: maxTowerHealth,
        mana: 0,
        manaRegen: 0,
        freezeTime: 0,

        // Cooldowns (keyed by ability ID)
        cooldowns: { fireball: 0, frostbolt: 0, gravity: 0 },

        // Casting
        casting: null,                   // ability ID or null
        castProgress: 0,
        castTime: 0,
        castingLoopSource: null,
        pendingManaCost: 0,

        // Gravity Spell
        gravityBarrier: null,
        capturedBalls: 0,
        gravityPhase: 'ready',

        // Upgrades
        upgrades: [],

        // 3D References (assigned after scene init)
        paddle: null,
        castBar3D: null,
        castFill3D: null,
        modelRoot: null,

        // Animation
        modelLoaded: false,
        animations: {},
        skeleton: null,
        currentAnim: 'idle',
        animLocked: false,
        baseRotY: 0,
        targetRotY: 0,

        // Model parts (for procedural characters)
        pickleParts: null,
        accessories: {},

        // Visual Effects
        flashMeshes: [],
        originalColors: [],
        flashActive: false
    };
}

/**
 * Get combatant by side ('left' or 'right')
 */
export function getCombatant(side) {
    const combatants = window.combatants || {};
    return combatants[side];
}

/**
 * Get opponent of a combatant
 */
export function getOpponent(combatant) {
    const combatants = window.combatants || {};
    return combatant.side === 'left' ? combatants.right : combatants.left;
}

/**
 * Legacy adapter - maps 'player'/'ai' to combatant system
 */
export function getCombatantLegacy(caster) {
    const combatants = window.combatants || {};
    return caster === 'player' ? combatants.left : combatants.right;
}

/**
 * Get UI element IDs for a combatant
 */
export function getCombatantUIElements(combatant) {
    const isLeft = combatant.side === 'left';
    return {
        manaPrefix: isLeft ? 'mana' : 'aiMana',
        manaClass: isLeft ? 'mana-segment-fill' : 'ai-mana-segment-fill',
        castBarContainer: isLeft ? 'castBarContainer' : 'aiCastBarContainer',
        castBarLabel: isLeft ? 'castBarLabel' : 'aiCastBarLabel',
        castBarProgress: isLeft ? 'castBarProgress' : 'aiCastBarProgress',
        healthBar: isLeft ? 'playerHealthBar' : 'aiHealthBar'
    };
}

/**
 * Check if combatant is rooted (casting a rooting spell)
 */
export function combatantIsRooted(combatant) {
    if (!combatant || !combatant.casting) return false;
    const getAbility = window.getAbility;
    if (!getAbility) return false;
    const ability = getAbility(combatant.casting);
    return ability && ability.rootWhileCasting;
}

/**
 * Reset combatant state for round start/reset
 */
export function combatantReset(combatant, isStart = false) {
    if (!combatant) return;
    combatant.mana = isStart ? 1 : 0;
    combatant.manaRegen = 0;
    combatant.freezeTime = 0;
    combatant.casting = null;
    combatant.castProgress = 0;
    combatant.castTime = 0;
    combatant.gravityPhase = 'ready';
    combatant.gravityBarrier = null;
    combatant.capturedBalls = 0;
    combatant.pendingManaCost = 0;
}

// ============================================================
// COMBATANT UI HELPERS
// ============================================================

/**
 * Update mana UI for a combatant
 */
export function updateCombatantManaUI(combatant) {
    const maxMana = window.maxMana || 3;
    const ui = getCombatantUIElements(combatant);
    const pendingCost = combatant.pendingManaCost || 0;
    const isCasting = combatant.casting && pendingCost > 0;

    const manaAfterCast = Math.max(0, combatant.mana - pendingCost);
    const fullMana = Math.floor(combatant.mana);
    const fractionalMana = combatant.mana - fullMana;

    for (let i = 1; i <= maxMana; i++) {
        const segment = document.getElementById(ui.manaPrefix + i);
        if (!segment) continue;

        let fillPercent = 0;
        let isPendingSpend = false;

        if (i <= fullMana) {
            fillPercent = 100;
            segment.value = 100;
            if (isCasting && i > manaAfterCast) {
                isPendingSpend = true;
            }
        } else if (i === fullMana + 1 && combatant.mana < maxMana) {
            fillPercent = fractionalMana * 100;
            segment.value = fillPercent;
        } else {
            fillPercent = 0;
            segment.value = 0;
        }

        // Update Babylon.js GUI mana segments
        if (window.guiElements) {
            const guiSegments = combatant.isLocalPlayer
                ? window.guiElements.playerManaSegments
                : window.guiElements.aiManaSegments;
            if (guiSegments && guiSegments[i - 1]) {
                const guiSeg = guiSegments[i - 1];
                guiSeg.width = fillPercent + "%";

                if (isPendingSpend) {
                    const pulse = 0.4 + Math.sin(Date.now() * 0.008) * 0.3;
                    guiSeg.alpha = pulse;
                } else {
                    guiSeg.alpha = 1.0;
                }
            }
        }
    }

    if (combatant.isLocalPlayer && window.updateManaAvailability) {
        window.updateManaAvailability();
    }
}

/**
 * Update cast bar UI for a combatant
 */
export function updateCombatantCastBarUI(combatant, name, element, progress) {
    const ui = getCombatantUIElements(combatant);
    const label = document.getElementById(ui.castBarLabel);
    const progressBar = document.getElementById(ui.castBarProgress);

    if (label) label.textContent = name;
    if (progressBar) {
        progressBar.value = progress * 100;
    }

    // Update ability icon overlay (local player only)
    if (combatant.isLocalPlayer && combatant.casting) {
        const overlay = document.getElementById(combatant.casting + 'CastProgress');
        if (overlay) {
            const angle = 360 - (progress * 360);
            overlay.style.setProperty('--cast-progress', angle + 'deg');
        }
    }

    // Update Babylon.js GUI cast bars
    if (window.guiElements) {
        const isPlayer = combatant.isLocalPlayer;
        const container = isPlayer ? window.guiElements.playerCastContainer : window.guiElements.aiCastContainer;
        const labelEl = isPlayer ? window.guiElements.playerCastLabel : window.guiElements.aiCastLabel;
        const fill = isPlayer ? window.guiElements.playerCastFill : window.guiElements.aiCastFill;

        if (container) {
            container.isVisible = (progress > 0 && progress < 1);
        }
        if (labelEl) {
            labelEl.text = name;
        }
        if (fill) {
            fill.width = (progress * 100) + "%";
        }

        // Update HTML overlay cast labels
        const htmlLabelId = isPlayer ? 'playerCastLabelHtml' : 'aiCastLabelHtml';
        const htmlLabel = document.getElementById(htmlLabelId);
        if (htmlLabel) {
            htmlLabel.textContent = name;
            if (progress > 0 && progress < 1) {
                htmlLabel.classList.add('visible');
            } else {
                htmlLabel.classList.remove('visible');
            }
        }
    }
}

// ============================================================
// MANA SYSTEM
// ============================================================

/**
 * Gain mana (capped at maxMana)
 */
export function gainMana(caster, amount) {
    const maxMana = window.maxMana || 3;
    const c = getCombatantLegacy(caster);
    if (!c) return;

    c.mana = Math.min(maxMana, c.mana + amount);
    updateCombatantManaUI(c);

    // Sync legacy variables
    if (caster === 'player') {
        window.playerMana = c.mana;
    } else {
        window.aiMana = c.mana;
    }
}

/**
 * Spend mana (returns true if successful)
 */
export function spendMana(caster, amount) {
    const c = getCombatantLegacy(caster);
    if (!c) return false;

    if (c.mana >= amount) {
        c.mana -= amount;
        updateCombatantManaUI(c);

        // Sync legacy variables
        if (caster === 'player') {
            window.playerMana = c.mana;
        } else {
            window.aiMana = c.mana;
        }
        return true;
    }
    return false;
}

// ============================================================
// CASTING SYSTEM
// ============================================================

/**
 * Start casting an ability
 */
export function startCasting(caster, abilityId) {
    const getAbility = window.getAbility;
    const getActiveUpgrades = window.getActiveUpgrades;
    const showCastBar = window.showCastBar;
    const showAICastBar = window.showAICastBar;
    const ToneSFX = window.ToneSFX;
    const playPlayerAnim = window.playPlayerAnim;
    const playAIAnim = window.playAIAnim;

    if (!getAbility) return false;

    const ability = getAbility(abilityId);
    if (!ability || !ability.castTime) return false;

    const c = getCombatantLegacy(caster);
    if (!c) return false;

    // Get upgrades early for stat overrides
    const activeUpgrades = getActiveUpgrades ? getActiveUpgrades(abilityId, caster) : [];
    const effectiveManaCost = (activeUpgrades.length > 0 && activeUpgrades[0].manaCost)
        ? activeUpgrades[0].manaCost
        : ability.manaCost;

    // Check mana
    if (c.mana < effectiveManaCost) return false;

    // Already casting?
    if (c.casting) return false;

    // Store pending mana cost
    c.pendingManaCost = effectiveManaCost;

    // Get display name and effective cast time
    const displayName = activeUpgrades.length > 0 ? activeUpgrades[0].name : ability.name;
    const effectiveCastTime = (activeUpgrades.length > 0 && activeUpgrades[0].castTime)
        ? activeUpgrades[0].castTime
        : ability.castTime;

    // Set combatant casting state
    c.casting = abilityId;
    c.castProgress = 0;
    c.castTime = effectiveCastTime;

    // Stop any existing casting loop sound
    if (ToneSFX) ToneSFX.castingStop();

    const isPlayer = caster === 'player';

    if (isPlayer) {
        // Sync legacy variables
        window.playerCasting = c.casting;
        window.playerCastProgress = c.castProgress;
        window.playerCastTime = c.castTime;

        updateCombatantCastBarUI(c, displayName, ability.element, 0);
        if (showCastBar) showCastBar(true);
        if (playPlayerAnim) playPlayerAnim('cast_loop', true);

        // Add casting class to ability slot
        const slot = document.getElementById(abilityId + 'Slot');
        if (slot) slot.classList.add('casting');
        const castProgressOverlay = document.getElementById(abilityId + 'CastProgress');
        if (castProgressOverlay) castProgressOverlay.style.setProperty('--cast-progress', '360deg');

        // Start casting sound
        if (ToneSFX) ToneSFX.castingStart('player');
    } else {
        // Sync legacy variables
        window.aiCasting = c.casting;
        window.aiCastProgress = c.castProgress;
        window.aiCastTime = c.castTime;

        updateCombatantCastBarUI(c, displayName, ability.element, 0);
        if (showAICastBar) showAICastBar(true);
        if (playAIAnim) playAIAnim('cast_loop', true);

        // Start casting sound
        if (ToneSFX) ToneSFX.castingStart('ai');
    }

    return true;
}

/**
 * Cancel casting (e.g., if stunned or interrupted)
 */
export function cancelCasting(caster, refundMana = false) {
    const c = getCombatantLegacy(caster);
    if (!c) return;

    const isPlayer = caster === 'player';
    const ToneSFX = window.ToneSFX;
    const showCastBar = window.showCastBar;
    const showAICastBar = window.showAICastBar;
    const playPlayerAnim = window.playPlayerAnim;
    const playAIAnim = window.playAIAnim;

    // Clear pending mana cost
    c.pendingManaCost = 0;

    // Stop casting sound
    if (ToneSFX) ToneSFX.castingStop(isPlayer ? 'player' : 'ai');

    if (isPlayer) {
        // Reset cast progress overlay
        const castProgressOverlay = document.getElementById(c.casting + 'CastProgress');
        if (castProgressOverlay) castProgressOverlay.style.setProperty('--cast-progress', '360deg');
        const slot = document.getElementById(c.casting + 'Slot');
        if (slot) slot.classList.remove('casting');

        c.casting = null;
        c.castProgress = 0;

        // Sync legacy variables
        window.playerCasting = null;
        window.playerCastProgress = 0;
        window.playerCastingLoopSource = null;

        if (showCastBar) showCastBar(false);
        const playerLabel = document.getElementById('playerCastLabelHtml');
        if (playerLabel) playerLabel.classList.remove('visible');
        if (window.updatePlayer3DCastBar) window.updatePlayer3DCastBar(0, false);
        if (playPlayerAnim) playPlayerAnim('idle', true);
    } else {
        c.casting = null;
        c.castProgress = 0;

        // Sync legacy variables
        window.aiCasting = null;
        window.aiCastProgress = 0;
        window.aiCastingLoopSource = null;

        if (showAICastBar) showAICastBar(false);
        const aiLabel = document.getElementById('aiCastLabelHtml');
        if (aiLabel) aiLabel.classList.remove('visible');
        if (window.updateAI3DCastBar) window.updateAI3DCastBar(0, false);
        if (playAIAnim) playAIAnim('idle', true);
    }
}

/**
 * Apply pushback to cast (when hit)
 */
export function applyCastPushback(caster, amount) {
    const c = getCombatantLegacy(caster);
    if (!c || !c.casting) return;

    const getAbility = window.getAbility;
    const ability = getAbility ? getAbility(c.casting) : null;
    const pushback = amount || (ability ? ability.pushbackOnHit : 0.3) || 0.3;
    c.castProgress = Math.max(0, c.castProgress - pushback);

    // Sync legacy variables
    if (caster === 'player') {
        window.playerCastProgress = c.castProgress;
    } else {
        window.aiCastProgress = c.castProgress;
    }
}

// ============================================================
// LEGACY ABILITY DEFINITIONS
// ============================================================

export const abilities = {
    fireball: {
        cooldown: 4,
        castTime: 1.0,
        speed: 12,
        damage: 1,
        manaCost: 1
    },
    frostbolt: {
        cooldown: 7,
        speed: 24,
        freezeDuration: 1.0,
        manaCost: 2
    },
    gravity: {
        cooldown: 15,
        barrierDuration: 2.5,
        maxCapture: 3,
        sphereSpeed: 10,
        sphereDamage: 2,
        slowRadius: 4,
        slowFactor: 0.4,
        manaCost: 3
    }
};

// ============================================================
// PLAYER STATE HELPERS
// ============================================================

/**
 * Check if player is rooted (legacy wrapper)
 */
export function isPlayerRooted() {
    const combatants = window.combatants || {};
    return combatantIsRooted(combatants.left);
}

/**
 * Check if AI is rooted (legacy wrapper)
 */
export function isAIRooted() {
    const combatants = window.combatants || {};
    return combatantIsRooted(combatants.right);
}

// ============================================================
// BACKWARD COMPATIBILITY - Expose on window
// ============================================================

if (typeof window !== 'undefined') {
    // Combatant system
    window.createCombatant = createCombatant;
    window.getCombatant = getCombatant;
    window.getOpponent = getOpponent;
    window.getCombatantLegacy = getCombatantLegacy;
    window.getCombatantUIElements = getCombatantUIElements;
    window.combatantIsRooted = combatantIsRooted;
    window.combatantReset = combatantReset;
    window.updateCombatantManaUI = updateCombatantManaUI;
    window.updateCombatantCastBarUI = updateCombatantCastBarUI;

    // Mana system
    window.gainMana = gainMana;
    window.spendMana = spendMana;

    // Casting system
    window.startCasting = startCasting;
    window.cancelCasting = cancelCasting;
    window.applyCastPushback = applyCastPushback;

    // Legacy abilities
    window.abilities = abilities;

    // Player state helpers
    window.isPlayerRooted = isPlayerRooted;
    window.isAIRooted = isAIRooted;
}
