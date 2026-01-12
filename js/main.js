/**
 * Volleybolt - Main Entry Point
 *
 * This file imports and verifies all extracted modules.
 * The game initialization still runs from index.html during the refactor.
 *
 * Module Architecture:
 * - Config modules define game constants and ability data
 * - Audio module handles Web Audio and Tone.js sound effects
 * - UI module manages all DOM-based UI updates
 * - Rendering module provides color palettes and visual effects
 * - Systems module contains core game mechanics (mana, casting, combatants)
 */

// ============================================================
// MODULE IMPORTS
// ============================================================

// Config
import { SCORING, PHYSICS, PARRY, MANA, MOVEMENT, NETCODE } from './config/game-config.js';
import { AbilityRegistry, getAbility, calculateDamage } from './config/ability-registry.js';

// Audio
import {
    initAudioContext,
    playSound,
    loadAllSounds,
    initToneJS,
    ToneSFX,
    IsochronicGenerator
} from './audio/audio-system.js';

// UI
import {
    updateScore,
    showMessage,
    hideMessage,
    updateCooldownUI,
    updateManaUI,
    updateAIManaUI,
    updateHealthBars,
    showDamageNumber,
    showCombatText,
    showFrozenText,
    updateGravityUI,
    showTalentScreen,
    hideTalentScreen,
    showMultiplayerLobby,
    hideMultiplayerLobby
} from './ui/ui-system.js';

// Rendering
import {
    NES_PALETTE,
    GRAYBOX_PALETTE,
    getNESColors,
    getGrayboxColors,
    applyRetroResolution,
    create4to3Handler,
    screenShake,
    createImpactDecal,
    shouldStepUI,
    setPS1Framerate
} from './rendering/rendering-utils.js';

// Game Systems
import {
    createCombatant,
    getCombatant,
    getCombatantLegacy,
    combatantReset,
    combatantIsRooted,
    gainMana,
    spendMana,
    startCasting,
    cancelCasting,
    applyCastPushback,
    abilities,
    isPlayerRooted,
    isAIRooted
} from './systems/game-systems.js';

// ============================================================
// MODULE VERIFICATION
// ============================================================

console.log('%c=== VOLLEYBOLT MODULAR BUILD ===', 'color: #c9a44a; font-weight: bold; font-size: 14px;');
console.log('%cModules loaded:', 'color: #58D854;');

// Verify config
const configLoaded = SCORING && PHYSICS && PARRY && MANA && MOVEMENT && NETCODE && AbilityRegistry;
console.log(`  - Config: ${configLoaded ? 'OK' : 'MISSING'}`);

// Verify audio
const audioLoaded = typeof initAudioContext === 'function' && typeof playSound === 'function';
console.log(`  - Audio: ${audioLoaded ? 'OK' : 'MISSING'}`);

// Verify UI
const uiLoaded = typeof updateScore === 'function' && typeof showMessage === 'function';
console.log(`  - UI: ${uiLoaded ? 'OK' : 'MISSING'}`);

// Verify rendering
const renderingLoaded = NES_PALETTE && typeof screenShake === 'function';
console.log(`  - Rendering: ${renderingLoaded ? 'OK' : 'MISSING'}`);

// Verify game systems
const systemsLoaded = typeof createCombatant === 'function' && typeof startCasting === 'function';
console.log(`  - Game Systems: ${systemsLoaded ? 'OK' : 'MISSING'}`);

// Summary
const allLoaded = configLoaded && audioLoaded && uiLoaded && renderingLoaded && systemsLoaded;
if (allLoaded) {
    console.log('%cAll modules loaded successfully!', 'color: #58D854; font-weight: bold;');
} else {
    console.warn('Some modules failed to load. Check console for errors.');
}

// ============================================================
// GAME CONFIG SUMMARY
// ============================================================

console.log('%cGame Config:', 'color: #3CBCFC;');
console.log(`  - Winning Score: ${SCORING.winningScore}`);
console.log(`  - Max Tower Health: ${SCORING.maxTowerHealth}`);
console.log(`  - Max Mana: ${MANA.max}`);
console.log(`  - Parry Window: ${PARRY.window}s`);
console.log(`  - Abilities: ${Object.keys(AbilityRegistry).join(', ')}`);

// ============================================================
// EXPORTS (for potential future use)
// ============================================================

export {
    // Config
    SCORING, PHYSICS, PARRY, MANA, MOVEMENT, NETCODE,
    AbilityRegistry, getAbility, calculateDamage,

    // Audio
    initAudioContext, playSound, loadAllSounds, initToneJS, ToneSFX, IsochronicGenerator,

    // UI
    updateScore, showMessage, hideMessage, updateCooldownUI, updateManaUI,
    updateAIManaUI, updateHealthBars, showDamageNumber, showCombatText,
    showFrozenText, updateGravityUI, showTalentScreen, hideTalentScreen,
    showMultiplayerLobby, hideMultiplayerLobby,

    // Rendering
    NES_PALETTE, GRAYBOX_PALETTE, getNESColors, getGrayboxColors,
    applyRetroResolution, create4to3Handler, screenShake, createImpactDecal,
    shouldStepUI, setPS1Framerate,

    // Game Systems
    createCombatant, getCombatant, getCombatantLegacy, combatantReset,
    combatantIsRooted, gainMana, spendMana, startCasting, cancelCasting,
    applyCastPushback, abilities, isPlayerRooted, isAIRooted
};
