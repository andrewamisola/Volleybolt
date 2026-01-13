/**
 * Volleybolt - UI System
 *
 * Handles all DOM-based UI updates including:
 * - Score display
 * - Messages (Ready, Champion, Defeated)
 * - Cooldown sweeps and timers
 * - Mana bars (player and AI)
 * - Cast bars
 * - Health bars
 * - Damage numbers
 * - Combat text (floating text system)
 * - Gravity Well UI
 * - Talent/Menu screens
 * - Multiplayer lobby
 */

// ============================================================
// SCORE DISPLAY
// ============================================================

/**
 * Update score display elements
 */
export function updateScore() {
    const playerScore = window.playerScore || 0;
    const aiScore = window.aiScore || 0;

    document.getElementById('playerScore').textContent = playerScore;
    document.getElementById('aiScore').textContent = aiScore;

    // Update Babylon.js GUI score (CRT-affected)
    if (window.guiElements && window.guiElements.scoreText) {
        window.guiElements.scoreText.text = playerScore + " - " + aiScore;
    }

    // Update HTML overlay score (crisp text)
    const htmlScore = document.getElementById('htmlScore');
    if (htmlScore) htmlScore.textContent = playerScore + " - " + aiScore;
}

// ============================================================
// MESSAGES (Ready, Champion, Defeated)
// ============================================================

/**
 * Show a center message on screen
 */
export function showMessage(text) {
    const msg = document.getElementById('message');
    msg.textContent = text;
    msg.style.display = 'block';

    // Update Babylon.js GUI message (CRT-affected)
    if (window.guiElements && window.guiElements.messageText) {
        window.guiElements.messageText.text = text;
        window.guiElements.messageText.alpha = 1;
    }

    // Update HTML overlay message (crisp text)
    const htmlMessage = document.getElementById('htmlMessage');
    if (htmlMessage) {
        htmlMessage.textContent = text;
        htmlMessage.classList.add('visible');
    }
}

/**
 * Hide center message
 */
export function hideMessage() {
    document.getElementById('message').style.display = 'none';

    // Update Babylon.js GUI message (CRT-affected)
    if (window.guiElements && window.guiElements.messageText) {
        window.guiElements.messageText.text = "";
        window.guiElements.messageText.alpha = 0;
    }

    // Update HTML overlay message (crisp text)
    const htmlMessage = document.getElementById('htmlMessage');
    if (htmlMessage) {
        htmlMessage.textContent = "";
        htmlMessage.classList.remove('visible');
    }
}

// ============================================================
// COOLDOWN UI
// ============================================================

/**
 * Update ability cooldown displays
 */
export function updateCooldownUI() {
    const combatants = window.combatants || {};
    const abilities = window.abilities || {};
    const maxMana = window.maxMana || 3;

    // Get cooldowns and mana from local player combatant
    const localCooldowns = combatants.left ? combatants.left.cooldowns : {
        fireball: window.playerFireballCooldown || 0,
        frostbolt: window.playerFrostboltCooldown || 0,
        gravity: window.playerGravityCooldown || 0
    };
    const mana = combatants.left ? combatants.left.mana : (window.playerMana || 0);

    // Fireball cooldown
    const fireSlot = document.getElementById('fireballSlot');
    const fireCdText = document.getElementById('fireballCDText');
    const fireSweep = document.getElementById('fireballSweep');
    const fireballManaCost = abilities.fireball ? abilities.fireball.manaCost : 1;

    if (!fireSlot || !fireCdText || !fireSweep) {
        console.warn('Cooldown UI elements not found');
        return;
    }

    const fireballCdHtml = document.getElementById('fireballCooldownHtml');

    if (localCooldowns.fireball > 0) {
        fireSlot.classList.remove('ready');
        fireSlot.classList.add('on-cooldown');
        fireCdText.textContent = Math.ceil(localCooldowns.fireball);
        const sweepAngle = (localCooldowns.fireball / (abilities.fireball?.cooldown || 1)) * 360;
        fireSweep.style.setProperty('--sweep-angle', sweepAngle + 'deg');

        if (window.guiElements && window.guiElements.fireballBtn && window.updateAbilityButtonState) {
            const btn = window.guiElements.fireballBtn;
            window.updateAbilityButtonState(btn, 'cooldown');
            btn.cooldownOverlay.height = ((localCooldowns.fireball / (abilities.fireball?.cooldown || 1)) * 100) + "%";
            btn.cooldownText.text = Math.ceil(localCooldowns.fireball).toString();
        }

        if (fireballCdHtml) {
            fireballCdHtml.textContent = Math.ceil(localCooldowns.fireball);
            fireballCdHtml.style.opacity = '1';
        }
    } else if (mana < fireballManaCost) {
        fireSlot.classList.remove('on-cooldown');
        fireSlot.classList.remove('ready');
        fireCdText.textContent = '';
        fireSweep.style.setProperty('--sweep-angle', '0deg');

        if (window.guiElements && window.guiElements.fireballBtn && window.updateAbilityButtonState) {
            window.updateAbilityButtonState(window.guiElements.fireballBtn, 'no-mana');
        }

        if (fireballCdHtml) {
            fireballCdHtml.textContent = '';
            fireballCdHtml.style.opacity = '0';
        }
    } else {
        fireSlot.classList.remove('on-cooldown');
        fireSlot.classList.add('ready');
        fireCdText.textContent = '';
        fireSweep.style.setProperty('--sweep-angle', '0deg');

        if (fireballCdHtml) {
            fireballCdHtml.textContent = '';
            fireballCdHtml.style.opacity = '0';
        }

        if (window.guiElements && window.guiElements.fireballBtn && window.updateAbilityButtonState) {
            window.updateAbilityButtonState(window.guiElements.fireballBtn, 'ready');
        }
    }

    // Frostbolt cooldown
    const frostSlot = document.getElementById('frostboltSlot');
    const frostCdText = document.getElementById('frostboltCDText');
    const frostSweep = document.getElementById('frostboltSweep');
    const frostboltManaCost = abilities.frostbolt ? abilities.frostbolt.manaCost : 2;
    const frostboltCdHtml = document.getElementById('frostboltCooldownHtml');

    if (frostSlot && frostCdText && frostSweep) {
        if (localCooldowns.frostbolt > 0) {
            frostSlot.classList.remove('ready');
            frostSlot.classList.add('on-cooldown');
            frostCdText.textContent = Math.ceil(localCooldowns.frostbolt);
            const sweepAngle = (localCooldowns.frostbolt / (abilities.frostbolt?.cooldown || 1)) * 360;
            frostSweep.style.setProperty('--sweep-angle', sweepAngle + 'deg');

            if (window.guiElements && window.guiElements.frostboltBtn && window.updateAbilityButtonState) {
                const btn = window.guiElements.frostboltBtn;
                window.updateAbilityButtonState(btn, 'cooldown');
                btn.cooldownOverlay.height = ((localCooldowns.frostbolt / (abilities.frostbolt?.cooldown || 1)) * 100) + "%";
                btn.cooldownText.text = Math.ceil(localCooldowns.frostbolt).toString();
            }

            if (frostboltCdHtml) {
                frostboltCdHtml.textContent = Math.ceil(localCooldowns.frostbolt);
                frostboltCdHtml.style.opacity = '1';
            }
        } else if (mana < frostboltManaCost) {
            frostSlot.classList.remove('on-cooldown');
            frostSlot.classList.remove('ready');
            frostCdText.textContent = '';
            frostSweep.style.setProperty('--sweep-angle', '0deg');

            if (window.guiElements && window.guiElements.frostboltBtn && window.updateAbilityButtonState) {
                window.updateAbilityButtonState(window.guiElements.frostboltBtn, 'no-mana');
            }

            if (frostboltCdHtml) {
                frostboltCdHtml.textContent = '';
                frostboltCdHtml.style.opacity = '0';
            }
        } else {
            frostSlot.classList.remove('on-cooldown');
            frostSlot.classList.add('ready');
            frostCdText.textContent = '';
            frostSweep.style.setProperty('--sweep-angle', '0deg');

            if (window.guiElements && window.guiElements.frostboltBtn && window.updateAbilityButtonState) {
                window.updateAbilityButtonState(window.guiElements.frostboltBtn, 'ready');
            }

            if (frostboltCdHtml) {
                frostboltCdHtml.textContent = '';
                frostboltCdHtml.style.opacity = '0';
            }
        }
    }

    // Update mana availability indicators
    updateManaAvailability();
}

// ============================================================
// MANA UI
// ============================================================

/**
 * Update player mana bar (3 segments)
 */
export function updateManaUI() {
    const combatants = window.combatants || {};
    const maxMana = window.maxMana || 3;
    const manaRegenTime = window.manaRegenTime || 3;

    const mana = combatants.left ? combatants.left.mana : (window.playerMana || 0);
    const manaRegen = combatants.left ? combatants.left.manaRegen : (window.playerManaRegen || 0);

    for (let i = 1; i <= maxMana; i++) {
        const segment = document.getElementById('mana' + i);
        if (!segment) continue;

        if (i <= mana) {
            segment.value = 100;
        } else if (i === mana + 1 && mana < maxMana) {
            const progress = (manaRegen / manaRegenTime) * 100;
            segment.value = progress;
        } else {
            segment.value = 0;
        }
    }
    updateManaAvailability();
}

/**
 * Update AI mana bar (3 segments)
 */
export function updateAIManaUI() {
    const combatants = window.combatants || {};
    const maxMana = window.maxMana || 3;
    const manaRegenTime = window.manaRegenTime || 3;

    const mana = combatants.right ? combatants.right.mana : (window.aiMana || 0);
    const manaRegen = combatants.right ? combatants.right.manaRegen : (window.aiManaRegen || 0);

    for (let i = 1; i <= maxMana; i++) {
        const segment = document.getElementById('aiMana' + i);
        if (!segment) continue;

        if (i <= mana) {
            segment.value = 100;
        } else if (i === mana + 1 && mana < maxMana) {
            const progress = (manaRegen / manaRegenTime) * 100;
            segment.value = progress;
        } else {
            segment.value = 0;
        }
    }
}

/**
 * Update ability slots to show if player has enough mana
 */
export function updateManaAvailability() {
    const combatants = window.combatants || {};
    const abilities = window.abilities || {};

    const fireSlot = document.getElementById('fireballSlot');
    const frostSlot = document.getElementById('frostboltSlot');
    const gravitySlot = document.getElementById('gravitySlot');

    const localCooldowns = combatants.left ? combatants.left.cooldowns : {
        fireball: window.playerFireballCooldown || 0,
        frostbolt: window.playerFrostboltCooldown || 0,
        gravity: window.playerGravityCooldown || 0
    };
    const localMana = combatants.left ? combatants.left.mana : (window.playerMana || 0);

    // Fireball
    if (fireSlot) {
        if (localCooldowns.fireball <= 0) {
            if (localMana < (abilities.fireball?.manaCost || 1)) {
                fireSlot.classList.add('no-mana');
            } else {
                fireSlot.classList.remove('no-mana');
            }
        } else {
            fireSlot.classList.remove('no-mana');
        }
    }

    // Frostbolt
    if (frostSlot) {
        if (localCooldowns.frostbolt <= 0) {
            if (localMana < (abilities.frostbolt?.manaCost || 2)) {
                frostSlot.classList.add('no-mana');
            } else {
                frostSlot.classList.remove('no-mana');
            }
        } else {
            frostSlot.classList.remove('no-mana');
        }
    }

    // Gravity Well (disabled for rework)
    if (gravitySlot) {
        const gravityPhase = combatants.left ? combatants.left.gravityPhase : (window.playerGravityPhase || 'ready');
        if (localCooldowns.gravity <= 0 && gravityPhase === 'ready') {
            if (localMana < (abilities.gravity?.manaCost || 3)) {
                gravitySlot.classList.add('no-mana');
            } else {
                gravitySlot.classList.remove('no-mana');
            }
        } else {
            gravitySlot.classList.remove('no-mana');
        }
    }
}

// ============================================================
// CAST BARS
// ============================================================

/**
 * Update player cast bar
 */
export function updateCastBarUI(name, element, progress) {
    const label = document.getElementById('castBarLabel');
    const progressBar = document.getElementById('castBarProgress');

    if (label) label.textContent = name;
    if (progressBar) {
        progressBar.value = progress * 100;
    }

    // Update cast progress overlay on ability icon
    const combatants = window.combatants || {};
    const castingAbility = combatants.left ? combatants.left.casting : window.playerCasting;
    if (castingAbility) {
        const castProgressOverlay = document.getElementById(castingAbility + 'CastProgress');
        if (castProgressOverlay) {
            const angle = 360 - (progress * 360);
            castProgressOverlay.style.setProperty('--cast-progress', angle + 'deg');
        }
    }
}

/**
 * Show/hide player cast bar
 */
export function showCastBar(show) {
    const container = document.getElementById('castBarContainer');
    if (container) {
        if (show) {
            container.classList.add('casting');
        } else {
            container.classList.remove('casting');
        }
    }
}

/**
 * Update AI cast bar
 */
export function updateAICastBarUI(name, element, progress) {
    const label = document.getElementById('aiCastBarLabel');
    const progressBar = document.getElementById('aiCastBarProgress');

    if (label) label.textContent = name;
    if (progressBar) {
        progressBar.value = progress * 100;
    }
}

/**
 * Show/hide AI cast bar
 */
export function showAICastBar(show) {
    const container = document.getElementById('aiCastBarContainer');
    if (container) {
        if (show) {
            container.classList.add('casting');
        } else {
            container.classList.remove('casting');
        }
    }
}

// ============================================================
// HEALTH BARS
// ============================================================

/**
 * Update health bar displays
 */
export function updateHealthBars() {
    const combatants = window.combatants || {};
    const maxTowerHealth = window.maxTowerHealth || 20;

    const leftHealth = combatants.left ? combatants.left.towerHealth : (window.playerTowerHealth || maxTowerHealth);
    const rightHealth = combatants.right ? combatants.right.towerHealth : (window.aiTowerHealth || maxTowerHealth);
    const playerPercent = (leftHealth / maxTowerHealth) * 100;
    const aiPercent = (rightHealth / maxTowerHealth) * 100;

    const playerBar = document.getElementById('playerHealthBar');
    const aiBar = document.getElementById('aiHealthBar');

    if (playerBar) playerBar.value = playerPercent;
    if (aiBar) aiBar.value = aiPercent;

    // Update Babylon.js GUI health bars
    if (window.guiElements) {
        if (window.guiElements.playerHealthFill) {
            window.guiElements.playerHealthFill.width = playerPercent + "%";
        }
        if (window.guiElements.aiHealthFill) {
            window.guiElements.aiHealthFill.width = aiPercent + "%";
        }
    }
}

// ============================================================
// DAMAGE NUMBERS
// ============================================================

const damageTextQueue = { player: [], ai: [] };
let lastDamageStepTime = 0;

/**
 * Show floating damage number at tower
 */
export function showDamageNumber(damage, isPlayerTower, worldZ) {
    const scene = window.scene;
    const BABYLON = window.BABYLON;
    if (!scene || !BABYLON) return;

    const tableWidth = 20;
    const gateX = isPlayerTower ? -(tableWidth/2 + 1.2) : (tableWidth/2 + 1.2);
    const worldPos = new BABYLON.Vector3(gateX, 2.5, worldZ || 0);
    const screenPos = BABYLON.Vector3.Project(
        worldPos,
        BABYLON.Matrix.Identity(),
        scene.getTransformMatrix(),
        scene.activeCamera.viewport.toGlobal(
            scene.getEngine().getRenderWidth(),
            scene.getEngine().getRenderHeight()
        )
    );

    const canvas = scene.getEngine().getRenderingCanvas();
    const canvasRect = canvas.getBoundingClientRect();
    const scaleX = canvasRect.width / scene.getEngine().getRenderWidth();
    const scaleY = canvasRect.height / scene.getEngine().getRenderHeight();

    const dmgEl = document.createElement('div');
    dmgEl.className = 'damage-number';
    dmgEl.textContent = '-' + damage;
    dmgEl.style.left = Math.floor(canvasRect.left + screenPos.x * scaleX) + 'px';
    dmgEl.style.top = Math.floor(canvasRect.top + screenPos.y * scaleY) + 'px';
    dmgEl.style.opacity = '1';
    document.body.appendChild(dmgEl);

    const side = isPlayerTower ? 'player' : 'ai';
    damageTextQueue[side].push({
        el: dmgEl,
        age: 0,
        startY: canvasRect.top + screenPos.y * scaleY
    });
}

/**
 * Update damage text animation (called from render loop)
 */
export function updateDamageText(dt) {
    const scene = window.scene;
    if (!scene) return;
    const now = Date.now();
    const doStep = (now - lastDamageStepTime) >= 100;
    if (doStep) lastDamageStepTime = now;

    for (const side of ['player', 'ai']) {
        for (let i = damageTextQueue[side].length - 1; i >= 0; i--) {
            const item = damageTextQueue[side][i];
            item.age += dt;

            if (item.age > 1.5) {
                if (item.el.parentNode) item.el.remove();
                damageTextQueue[side].splice(i, 1);
                continue;
            }

            if (doStep) {
                if (item.age > 1.0) {
                    const fadeProgress = (item.age - 1.0) / 0.5;
                    const steppedOpacity = fadeProgress < 0.33 ? 1 : fadeProgress < 0.66 ? 0.66 : fadeProgress < 1 ? 0.33 : 0;
                    item.el.style.opacity = String(steppedOpacity);
                }
                const steppedAge = Math.floor(item.age / 0.15) * 0.15;
                item.el.style.top = Math.floor(item.startY - steppedAge * 30) + 'px';
            }
        }
    }
}

// ============================================================
// COMBAT TEXT (Floating Text System)
// ============================================================

const combatTextQueue = { player: [], ai: [] };
const STEP_INTERVAL = 40;  // 25fps to match D2
let lastTextStepTime = 0;

const combatTextColors = {
    fire: '#ffa040',
    frost: '#80d0ff',
    frozen: '#4080ff',
    damage: '#ff4040',
    cancel: '#ffff40',
    default: '#ffffff'
};

/**
 * Create an HTML combat text element
 */
export function createHTMLCombatText(text, type = '') {
    const el = document.createElement('div');
    el.className = 'combat-text' + (type ? ' ' + type : '');
    el.textContent = text.toUpperCase();
    el.style.opacity = '1';
    const container = document.getElementById('gameContainer');
    if (container) container.appendChild(el);
    return el;
}

/**
 * Show combat text above a player/AI
 */
export function showCombatText(isPlayer, text, type = '') {
    const scene = window.scene;
    if (!scene) return;
    const side = isPlayer ? 'player' : 'ai';
    const el = createHTMLCombatText(text, type);
    if (!el) return;

    combatTextQueue[side].push({
        el: el,
        age: 0,
        offsetY: 0,
        targetOffsetY: 0,
        currentScreenY: 0
    });

    if (combatTextQueue[side].length > 4) {
        const old = combatTextQueue[side].shift();
        if (old.el) old.el.remove();
    }
}

// Floating texts at world positions
const floatingTexts = [];

/**
 * Show combat text at a specific 3D world position
 */
export function showCombatTextAt(worldPos, text, type = '') {
    const scene = window.scene;
    const BABYLON = window.BABYLON;
    if (!scene || !BABYLON) return;
    const el = createHTMLCombatText(text, type);
    if (!el) return;

    floatingTexts.push({
        el: el,
        worldPos: worldPos.clone(),
        age: 0
    });
}

let lastFloatStepTime = 0;

/**
 * Update floating texts at world positions (called from render loop)
 */
export function updateFloatingTexts(dt) {
    const scene = window.scene;
    const BABYLON = window.BABYLON;
    if (!scene || !BABYLON) return;
    const now = Date.now();
    const doStep = (now - lastFloatStepTime) >= STEP_INTERVAL;
    if (doStep) lastFloatStepTime = now;

    const canvas = scene.getEngine().getRenderingCanvas();
    const canvasRect = canvas.getBoundingClientRect();
    const renderWidth = scene.getEngine().getRenderWidth();
    const renderHeight = scene.getEngine().getRenderHeight();

    for (let i = floatingTexts.length - 1; i >= 0; i--) {
        const item = floatingTexts[i];
        item.age += dt;

        if (item.age > 2.5) {
            if (item.el) item.el.remove();
            floatingTexts.splice(i, 1);
            continue;
        } else if (item.age > 2.0 && doStep) {
            const fadeProgress = (item.age - 2.0) / 0.5;
            const steppedAlpha = fadeProgress < 0.33 ? 1 : fadeProgress < 0.66 ? 0.66 : fadeProgress < 1 ? 0.33 : 0;
            if (item.el) item.el.style.opacity = steppedAlpha;
        }

        const moveAge = Math.max(0, item.age - 1.0);
        const steppedMoveAge = Math.floor(moveAge / 0.15) * 0.15;

        const screenPos = BABYLON.Vector3.Project(
            new BABYLON.Vector3(item.worldPos.x, item.worldPos.y + steppedMoveAge * 1.5, item.worldPos.z),
            BABYLON.Matrix.Identity(),
            scene.getTransformMatrix(),
            scene.activeCamera.viewport.toGlobal(renderWidth, renderHeight)
        );

        if (doStep && item.el) {
            const scaleX = canvasRect.width / renderWidth;
            const scaleY = canvasRect.height / renderHeight;
            item.el.style.left = Math.floor(screenPos.x * scaleX) + "px";
            item.el.style.top = Math.floor(screenPos.y * scaleY) + "px";
            item.el.style.transform = "translate(-50%, -50%)";
        }
    }
}

const STACK_SPACING = 22;

/**
 * Update combat text positions (called from render loop)
 */
export function updateCombatText(dt) {
    const scene = window.scene;
    const BABYLON = window.BABYLON;
    const playerPaddle = window.playerPaddle;
    const aiPaddle = window.aiPaddle;
    if (!scene || !BABYLON) return;

    const now = Date.now();
    const doStep = (now - lastTextStepTime) >= STEP_INTERVAL;
    if (doStep) lastTextStepTime = now;

    const canvas = scene.getEngine().getRenderingCanvas();
    const canvasRect = canvas.getBoundingClientRect();
    const renderWidth = scene.getEngine().getRenderWidth();
    const renderHeight = scene.getEngine().getRenderHeight();
    const scaleX = canvasRect.width / renderWidth;
    const scaleY = canvasRect.height / renderHeight;

    for (const side of ['player', 'ai']) {
        const paddle = side === 'player' ? playerPaddle : aiPaddle;
        if (!paddle) continue;

        const worldPos = new BABYLON.Vector3(paddle.position.x, 2.5, paddle.position.z);
        const screenPos = BABYLON.Vector3.Project(
            worldPos,
            BABYLON.Matrix.Identity(),
            scene.getTransformMatrix(),
            scene.activeCamera.viewport.toGlobal(renderWidth, renderHeight)
        );

        const baseX = screenPos.x * scaleX;
        const baseY = screenPos.y * scaleY;

        for (let i = combatTextQueue[side].length - 1; i >= 0; i--) {
            const item = combatTextQueue[side][i];
            item.age += dt;

            if (item.age > 2.5) {
                if (item.el) item.el.remove();
                combatTextQueue[side].splice(i, 1);
                continue;
            }

            if (item.age > 2.0 && doStep) {
                const fadeProgress = (item.age - 2.0) / 0.5;
                const steppedAlpha = fadeProgress < 0.33 ? 1 : fadeProgress < 0.66 ? 0.66 : fadeProgress < 1 ? 0.33 : 0;
                if (item.el) item.el.style.opacity = steppedAlpha;
            }

            const moveAge = Math.max(0, item.age - 1.0);
            const steppedMoveAge = Math.floor(moveAge / 0.15) * 0.15;
            const slot = combatTextQueue[side].length - 1 - i;
            const slotY = baseY - (slot * STACK_SPACING) - (steppedMoveAge * 30);

            if (doStep && item.el) {
                item.el.style.left = Math.floor(baseX) + "px";
                item.el.style.top = Math.floor(slotY) + "px";
                item.el.style.transform = "translate(-50%, -50%)";
            }
        }
    }
}

// ============================================================
// FROZEN TEXT & SPELL CAST TEXT
// ============================================================

/**
 * Show "#FROZEN" text above player/AI (status ailment)
 */
export function showFrozenText(isPlayer) {
    showCombatText(isPlayer, '#FROZEN', 'frozen');
}

/**
 * Show spell cast text above caster
 */
export function showSpellCastText(isPlayer, spellName, element) {
    showCombatText(isPlayer, spellName, element || 'fire');
}

// ============================================================
// GRAVITY WELL UI
// ============================================================

/**
 * Update gravity spell UI state
 */
export function updateGravityUI() {
    const slot = document.getElementById('gravitySlot');
    if (!slot) return; // Gravity Well is disabled for rework

    const icon = document.getElementById('gravityIcon');
    const captureEl = document.getElementById('captureCount');
    const cdText = document.getElementById('gravityCDText');
    const sweep = document.getElementById('gravitySweep');

    const combatants = window.combatants || {};
    const abilities = window.abilities || {};
    const c = combatants.left;
    const gravityPhase = c ? c.gravityPhase : (window.playerGravityPhase || 'ready');
    const gravityCooldown = c ? c.cooldowns.gravity : (window.playerGravityCooldown || 0);
    const capturedBalls = c ? c.capturedBalls : (window.playerCapturedBalls || 0);

    slot.classList.remove('ready', 'on-cooldown', 'barrier-active', 'sphere-ready');

    if (gravityPhase === 'barrier') {
        slot.classList.add('barrier-active');
        if (icon) icon.textContent = '🌀';
        if (captureEl) captureEl.textContent = capturedBalls + '/' + (abilities.gravity?.maxCapture || 3);
        if (cdText) cdText.textContent = '';
        if (sweep) sweep.style.setProperty('--sweep-angle', '0deg');
    } else if (gravityPhase === 'sphere') {
        slot.classList.add('sphere-ready');
        if (icon) icon.textContent = '💥';
        if (captureEl) captureEl.textContent = capturedBalls;
        if (cdText) cdText.textContent = '';
        if (sweep) sweep.style.setProperty('--sweep-angle', '0deg');
    } else if (gravityCooldown > 0) {
        slot.classList.add('on-cooldown');
        if (icon) icon.textContent = '🌀';
        if (captureEl) captureEl.textContent = '';
        if (cdText) cdText.textContent = Math.ceil(gravityCooldown);
        const sweepAngle = (gravityCooldown / (abilities.gravity?.cooldown || 15)) * 360;
        if (sweep) sweep.style.setProperty('--sweep-angle', sweepAngle + 'deg');
    } else {
        slot.classList.add('ready');
        if (icon) icon.textContent = '🌀';
        if (captureEl) captureEl.textContent = '';
        if (cdText) cdText.textContent = '';
        if (sweep) sweep.style.setProperty('--sweep-angle', '0deg');
    }
}

// ============================================================
// KEY PRESS FEEDBACK
// ============================================================

const keyToUIElement = {
    'Space': () => document.getElementById('parryButton'),
    'Digit1': () => document.getElementById('fireballSlot'),
    'Digit2': () => document.getElementById('frostboltSlot'),
    'Digit3': () => document.getElementById('gravitySlot')
};

/**
 * Show visual feedback when a key is pressed
 */
export function showKeyPressedFeedback(keyCode) {
    const getElement = keyToUIElement[keyCode];
    if (getElement) {
        const element = getElement();
        if (element) {
            element.classList.add('pressed');
            setTimeout(() => element.classList.remove('pressed'), 120);
        }
    }
}

// ============================================================
// TALENT SCREEN
// ============================================================

/**
 * Show talent/menu screen
 */
export function showTalentScreen() {
    const talentScreen = document.getElementById('talentScreen');

    // Stop any running game before showing menu
    window.roundActive = false;
    window.gameOver = false;
    window.gameMode = 'single';
    if (window.clearAllProjectiles) window.clearAllProjectiles();

    // Stop any casting sounds and background music
    if (window.ToneSFX) {
        window.ToneSFX.castingStop();
        window.ToneSFX.musicStop();
    }

    // Cancel any active casts and reset mana for both combatants
    const combatants = window.combatants || {};
    for (const c of [combatants.left, combatants.right]) {
        if (c) {
            c.casting = null;
            c.castProgress = 0;
            c.castTime = 0;
            c.mana = 0;
            c.manaRegen = 0;
        }
    }

    hideMessage();

    window.selectedUpgrade = 'default';

    const gameContainer = document.getElementById('gameContainer');
    if (gameContainer) gameContainer.style.display = 'block';

    if (window.guiElements && window.guiElements.menuTitle) {
        window.guiElements.menuTitle.alpha = 1;
    }

    const abilityBar = document.getElementById('abilityBar');
    if (abilityBar) abilityBar.style.display = 'none';
    const parryButton = document.getElementById('parryButton');
    if (parryButton) parryButton.style.display = 'none';

    talentScreen.classList.add('visible');
}

/**
 * Hide talent/menu screen
 */
export function hideTalentScreen() {
    const talentScreen = document.getElementById('talentScreen');
    talentScreen.classList.remove('visible');

    const gameContainer = document.getElementById('gameContainer');
    if (gameContainer) gameContainer.style.display = 'block';
    if (window.gameEngine && window.gameRenderLoop) {
        window.gameEngine.runRenderLoop(window.gameRenderLoop);
    }

    if (window.guiElements && window.guiElements.menuTitle) {
        window.guiElements.menuTitle.alpha = 0;
    }

    const abilityBar = document.getElementById('abilityBar');
    if (abilityBar) abilityBar.style.display = 'flex';
    const parryButton = document.getElementById('parryButton');
    if (parryButton) parryButton.style.display = 'block';
}

/**
 * Update ability UI based on selected upgrade
 */
export function updateAbilityUI() {
    const fireballSlot = document.getElementById('fireballSlot');
    const fireballIcon = fireballSlot?.querySelector('.ability-icon');
    const fireballTooltip = document.getElementById('fireballTooltip');
    const playerUpgrades = window.playerUpgrades || [];

    if (!fireballSlot || !fireballIcon || !fireballTooltip) return;

    if (playerUpgrades.includes('magma_lob')) {
        fireballIcon.className = 'ability-icon fireball-icon';
        fireballTooltip.innerHTML = `
            <div class="tooltip-title">Magma Lob</div>
            <div class="tooltip-stats-row">
                <div class="tooltip-stats-left">
                    <span class="tooltip-stat-item mana"><span class="icon">*</span><span class="value">1 Mana</span></span>
                    <span class="tooltip-stat-item cast"><span class="icon">></span><span class="value">1s Cast</span></span>
                </div>
                <span class="tooltip-stat-item cooldown"><span class="icon">@</span><span class="value">5s CD</span></span>
            </div>
            <div class="tooltip-description">
                Lob a <span class="tt-spell">Magma Bomb</span> in an arc. At the <span class="tt-mechanic">Midline</span>, it explodes into <span class="tt-value">2</span> bouncing bombs that deal <span class="tt-value">1</span> <span class="tt-fire">Fire</span> damage each.
            </div>
        `;
    } else {
        fireballIcon.className = 'ability-icon fireball-icon';
        fireballTooltip.innerHTML = `
            <div class="tooltip-title">Fireball</div>
            <div class="tooltip-stats-row">
                <div class="tooltip-stats-left">
                    <span class="tooltip-stat-item mana"><span class="icon">*</span><span class="value">1 Mana</span></span>
                    <span class="tooltip-stat-item cast"><span class="icon">></span><span class="value">1s Cast</span></span>
                </div>
                <span class="tooltip-stat-item cooldown"><span class="icon">@</span><span class="value">5s CD</span></span>
            </div>
            <div class="tooltip-description">
                Throw a <span class="tt-spell">Fireball</span> in front of you, dealing <span class="tt-value">2</span> <span class="tt-fire">Fire</span> damage, scaling up to <span class="tt-value">5</span> with <span class="tt-mechanic">Volleys</span>.
            </div>
        `;
    }
}

// ============================================================
// MULTIPLAYER LOBBY
// ============================================================

/**
 * Show multiplayer lobby
 */
export function showMultiplayerLobby() {
    window.roundActive = false;
    window.gameOver = false;
    window.gameMode = 'single';
    if (window.clearAllProjectiles) window.clearAllProjectiles();

    if (window.ToneSFX) {
        window.ToneSFX.castingStop();
        window.ToneSFX.musicStop();
    }

    const combatants = window.combatants || {};
    for (const c of [combatants.left, combatants.right]) {
        if (c) {
            c.casting = null;
            c.castProgress = 0;
            c.castTime = 0;
        }
    }

    const gameContainer = document.getElementById('gameContainer');
    if (gameContainer) gameContainer.style.display = 'none';

    if (window.gameEngine) window.gameEngine.stopRenderLoop();

    document.getElementById('talentScreen').classList.remove('visible');
    document.getElementById('multiplayerLobby').style.display = 'flex';
    document.getElementById('lobbyModeSelect').style.display = 'block';
    document.getElementById('lobbyHostView').style.display = 'none';
    document.getElementById('lobbyJoinView').style.display = 'none';
    document.getElementById('lobbyConnectedView').style.display = 'none';
}

/**
 * Hide multiplayer lobby
 */
export function hideMultiplayerLobby() {
    document.getElementById('multiplayerLobby').style.display = 'none';

    const gameContainer = document.getElementById('gameContainer');
    if (gameContainer) gameContainer.style.display = 'block';
    if (window.gameEngine && window.gameRenderLoop) {
        window.gameEngine.runRenderLoop(window.gameRenderLoop);
    }
}

/**
 * Show specific lobby view
 */
export function showLobbyView(viewId) {
    document.getElementById('lobbyModeSelect').style.display = 'none';
    document.getElementById('lobbyHostView').style.display = 'none';
    document.getElementById('lobbyJoinView').style.display = 'none';
    document.getElementById('lobbyConnectedView').style.display = 'none';

    const view = document.getElementById(viewId);
    if (view) view.style.display = 'block';
}

// ============================================================
// BACKWARD COMPATIBILITY - Expose on window
// ============================================================
// NOTE: Many UI functions are STILL DEFINED in index.html and should NOT
// be overwritten here. The inline versions have proper access to scene,
// combatants, and other game state.

if (typeof window !== 'undefined') {
    // Only expose functions NOT defined in index.html
    // Most UI functions are still inline - do not overwrite them!

    // NOTE: The following are STILL DEFINED in index.html:
    // - updateScore, showMessage, hideMessage
    // - updateCooldownUI, updateManaUI, updateAIManaUI, updateManaAvailability
    // - updateCastBarUI, showCastBar, updateAICastBarUI, showAICastBar
    // - updateHealthBars, showDamageNumber, updateDamageText
    // - showCombatText, showCombatTextAt, updateFloatingTexts, updateCombatText
    // - showFrozenText, showSpellCastText
    // - updateGravityUI, showKeyPressedFeedback
    // - showTalentScreen, hideTalentScreen, updateAbilityUI
    // - showMultiplayerLobby, hideMultiplayerLobby, showLobbyView

    // Export only color constants (safe, no function conflicts)
    window.combatTextColors = combatTextColors;
}
