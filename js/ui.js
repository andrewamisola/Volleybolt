// ============================================================
// VOLLEYBOLT - DOM UI
//
// Reads sim state and events; writes only to the DOM. Display is
// perspective-aware: `primarySide` is the local player's wizard, so
// in online play the joiner still sees their own bars on the left.
// ============================================================

import * as C from './config.js';
import { ABILITIES, UPGRADES } from './config.js';
import { other } from './sim.js';
import { pressVirtual, pressVirtualP2 } from './input.js';

const $ = (id) => document.getElementById(id);

const ABILITY_IDS = ['fireball', 'frostbolt', 'lightning'];

let cfg = {
    mode: 'solo',          // solo | duo | online
    primarySide: 'left',
    localSides: ['left']
};
let projectToScreen = null;
let lastPhase = null;

export function configure(options, projectFn) {
    cfg = { ...cfg, ...options };
    if (projectFn) projectToScreen = projectFn;

    // Health bar labels
    if (cfg.mode === 'duo') {
        $('leftHealthLabel').textContent = 'Left Wizard';
        $('rightHealthLabel').textContent = 'Right Wizard';
    } else {
        $('leftHealthLabel').textContent = 'Your Tower';
        $('rightHealthLabel').textContent = cfg.mode === 'online' ? 'Opponent' : 'Enemy Tower';
    }

    // Instructions
    if (cfg.mode === 'duo') {
        $('instructions').textContent =
            'P1: W/S move, SPACE parry, 1/2/3 cast — P2: ↑/↓ move, ENTER parry, 8/9/0 cast';
    } else {
        $('instructions').textContent = 'W/S move · SPACE parry · 1/2/3 cast';
    }
}

// Map a sim side to its display column ('mine' = left UI cluster)
const displayLeftSide = () => cfg.primarySide;
const displayRightSide = () => other(cfg.primarySide);

// ---------------------------------------------------------------
// Static setup: tooltips and ability slot wiring
// ---------------------------------------------------------------
export function buildAbilityBar() {
    for (const id of ABILITY_IDS) {
        const a = ABILITIES[id];
        const tooltipEl = $(id + 'Tooltip');
        if (tooltipEl) {
            let html = `
                <div class="tooltip-header">
                    <span class="tooltip-icon">${a.icon}</span>
                    <span class="tooltip-title">${a.name}</span>
                    <span class="tooltip-element ${a.element}">${a.element}</span>
                </div>
                <div class="tooltip-description">${a.tooltip.description}</div>
                <div class="tooltip-stats">`;
            for (const stat of a.tooltip.stats) {
                html += `
                    <div class="tooltip-stat">
                        <span class="tooltip-stat-icon">${stat.icon}</span>
                        <span class="tooltip-stat-label">${stat.label}:</span>
                        <span class="tooltip-stat-value ${stat.type}">${stat.value}</span>
                    </div>`;
            }
            html += '</div><div class="tooltip-effects">';
            for (const effect of a.tooltip.effects) {
                html += `
                    <div class="tooltip-effect">
                        <span class="tooltip-effect-icon">▸</span>
                        <span class="tooltip-effect-text">${effect}</span>
                    </div>`;
            }
            html += '</div>';
            tooltipEl.innerHTML = html;
        }
        const slot = $(id + 'Slot');
        if (slot) {
            slot.addEventListener('click', () => pressVirtual('cast', id));
        }
    }
    $('parryButton').addEventListener('click', () => pressVirtual('parry'));
}

// ---------------------------------------------------------------
// Mana bars (segment count follows stats.maxMana upgrades)
// ---------------------------------------------------------------
function syncManaBar(containerId, wizard, segClass, fillClass) {
    const container = $(containerId);
    if (container.childElementCount !== wizard.stats.maxMana) {
        container.innerHTML = '';
        for (let i = 0; i < wizard.stats.maxMana; i++) {
            const seg = document.createElement('div');
            seg.className = segClass;
            const fill = document.createElement('div');
            fill.className = fillClass;
            seg.appendChild(fill);
            container.appendChild(seg);
        }
    }
    [...container.children].forEach((seg, i) => {
        seg.classList.toggle('filled', i < wizard.mana);
    });
}

// ---------------------------------------------------------------
// Per-frame update
// ---------------------------------------------------------------
export function update(sim) {
    const mine = sim.wizards[displayLeftSide()];
    const theirs = sim.wizards[displayRightSide()];

    // Health bars
    $('leftHealthFill').style.width = (sim.gateHP[mine.side] / C.MAX_GATE_HP) * 100 + '%';
    $('rightHealthFill').style.width = (sim.gateHP[theirs.side] / C.MAX_GATE_HP) * 100 + '%';

    // Score
    $('playerScore').textContent = sim.scores[mine.side];
    $('aiScore').textContent = sim.scores[theirs.side];

    // Round timer
    const timerEl = $('roundTimer');
    if (sim.phase === 'playing') {
        if (sim.suddenDeath) {
            timerEl.textContent = 'SUDDEN DEATH';
            timerEl.classList.add('sudden-death');
        } else {
            timerEl.textContent = Math.ceil(sim.roundTimer);
            timerEl.classList.toggle('sudden-death', sim.roundTimer <= 10);
        }
        timerEl.style.display = 'block';
    } else {
        timerEl.style.display = 'none';
    }

    // Mana
    syncManaBar('manaBar', mine, 'mana-segment', 'mana-segment-fill');
    syncManaBar('aiManaBar', theirs, 'ai-mana-segment', 'ai-mana-segment-fill');

    // Ability slots (primary wizard)
    for (const id of ABILITY_IDS) {
        const a = ABILITIES[id];
        const slot = $(id + 'Slot');
        const cdText = $(id + 'CDText');
        const sweep = $(id + 'Sweep');
        const cd = mine.cooldowns[id];
        if (cd > 0) {
            slot.classList.remove('ready');
            slot.classList.add('on-cooldown');
            cdText.textContent = Math.ceil(cd);
            const total = a.cooldown * mine.stats.cooldownMult;
            sweep.style.setProperty('--sweep-angle', (cd / total) * 360 + 'deg');
            slot.classList.remove('no-mana');
        } else {
            slot.classList.remove('on-cooldown');
            slot.classList.add('ready');
            cdText.textContent = '';
            sweep.style.setProperty('--sweep-angle', '0deg');
            slot.classList.toggle('no-mana', mine.mana < a.manaCost);
        }
        slot.classList.toggle('casting', mine.casting === id);
    }

    // Cast bars
    updateCastBar('castBar', mine);
    updateCastBar('aiCastBar', theirs);

    // Cast progress overlay on the channeled ability's icon
    if (mine.casting) {
        const overlay = $(mine.casting + 'CastProgress');
        if (overlay) {
            const angle = 360 - (mine.castProg / mine.castTime) * 360;
            overlay.style.setProperty('--cast-progress', angle + 'deg');
        }
    }

    // Phase messages
    if (sim.phase !== lastPhase) {
        lastPhase = sim.phase;
        if (sim.phase === 'serve') {
            showMessage(cfg.mode === 'duo' ? 'Ready — Space or Enter' : 'Ready');
        } else if (sim.phase === 'playing') {
            hideMessage();
        }
        // roundEnd / matchEnd messages come from events (they carry the winner)
        if (sim.phase !== 'picking') hidePicks();
    }
}

function updateCastBar(prefix, wizard) {
    const container = $(prefix + 'Container');
    const label = $(prefix + 'Label');
    const fill = $(prefix + 'Fill');
    if (wizard.casting) {
        const a = ABILITIES[wizard.casting];
        container.classList.add('casting');
        label.textContent = a.name;
        fill.style.width = (wizard.castProg / wizard.castTime) * 100 + '%';
        fill.className = '';
        fill.classList.add(a.element);
    } else {
        container.classList.remove('casting');
    }
}

// ---------------------------------------------------------------
// Events
// ---------------------------------------------------------------
export function handleEvents(events, sim) {
    for (const e of events) {
        switch (e.type) {
            case 'gateHit':
                spawnDamageNumber(e.damage, e.side, e.z);
                break;
            case 'freeze':
                spawnFrozenText(sim, e.side);
                break;
            case 'castPushback': {
                if (e.side === displayLeftSide()) {
                    const fill = $('castBarFill');
                    fill.classList.add('pushback');
                    setTimeout(() => fill.classList.remove('pushback'), 200);
                }
                break;
            }
            case 'roundEnd': {
                if (sim.matchWinner) break; // matchEnd message takes over
                if (cfg.mode === 'duo') {
                    showMessage(e.winner === 'left' ? 'Left Wizard!' : 'Right Wizard!');
                } else {
                    showMessage(e.winner === cfg.primarySide ? 'Victory' : 'Defeat');
                }
                break;
            }
            case 'matchEnd': {
                if (cfg.mode === 'duo') {
                    showMessage(e.winner === 'left' ? 'Left Champion!' : 'Right Champion!');
                } else {
                    showMessage(e.winner === cfg.primarySide ? 'Champion' : 'Defeated');
                }
                break;
            }
            case 'suddenDeath':
                showMessage('Sudden Death');
                setTimeout(hideMessage, 1500);
                break;
            case 'showPicks':
                showPicks(sim);
                break;
            case 'picked':
                refreshPickPanels(sim);
                break;
            default:
                break;
        }
    }
}

// ---------------------------------------------------------------
// Messages
// ---------------------------------------------------------------
export function showMessage(text) {
    const msg = $('message');
    msg.textContent = text;
    msg.style.display = 'block';
}
export function hideMessage() {
    $('message').style.display = 'none';
}

// ---------------------------------------------------------------
// Floating combat text
// ---------------------------------------------------------------
function spawnDamageNumber(damage, gateSide, worldZ) {
    if (!projectToScreen) return;
    const gateX = gateSide === 'left' ? -C.GATE_X : C.GATE_X;
    const pos = projectToScreen(gateX, 2, worldZ || 0);
    const el = document.createElement('div');
    el.className = 'damage-number';
    el.textContent = '-' + damage;
    el.style.left = pos.x + 'px';
    el.style.top = pos.y + 'px';
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 1000);
}

function spawnFrozenText(sim, side) {
    if (!projectToScreen) return;
    const w = sim.wizards[side];
    const pos = projectToScreen(w.x, 1.5, w.z);
    const el = document.createElement('div');
    el.className = 'frozen-text';
    el.textContent = 'FROZEN!';
    el.style.left = pos.x + 'px';
    el.style.top = pos.y + 'px';
    el.style.transform = 'translate(-50%, -50%)';
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 1000);
}

// ---------------------------------------------------------------
// Between-round upgrade picks
// ---------------------------------------------------------------
function pickPanelFor(sim, side, slotLabel, pressFn, keyHints) {
    const options = sim.picks.options[side];
    const chosen = sim.picks.chosen[side];
    const panel = document.createElement('div');
    panel.className = 'pick-panel';
    panel.dataset.side = side;
    const title = document.createElement('div');
    title.className = 'pick-title';
    title.textContent = chosen !== null ? slotLabel + ' — Ready!' : slotLabel + ': Choose an upgrade';
    panel.appendChild(title);
    const cards = document.createElement('div');
    cards.className = 'pick-cards';
    options.forEach((upgradeIdx, i) => {
        const u = UPGRADES[upgradeIdx];
        const card = document.createElement('div');
        card.className = 'pick-card' + (chosen === i ? ' chosen' : chosen !== null ? ' dimmed' : '');
        card.innerHTML = `
            <div class="pick-icon">${u.icon}</div>
            <div class="pick-name">${u.name}</div>
            <div class="pick-desc">${u.desc}</div>
            <div class="pick-key">${keyHints[i]}</div>`;
        if (chosen === null && pressFn) {
            card.addEventListener('click', () => pressFn('pick', i));
        }
        cards.appendChild(card);
    });
    panel.appendChild(cards);
    return panel;
}

function showPicks(sim) {
    refreshPickPanels(sim);
    $('upgradeOverlay').style.display = 'flex';
}

function refreshPickPanels(sim) {
    if (!sim.picks) return;
    const container = $('upgradePanels');
    container.innerHTML = '';
    if (cfg.mode === 'duo') {
        container.appendChild(pickPanelFor(sim, 'left', 'Player 1', pressVirtual, ['1', '2', '3']));
        container.appendChild(pickPanelFor(sim, 'right', 'Player 2',
            (a, v) => pressVirtualP2(a, v), ['8', '9', '0']));
    } else {
        const side = cfg.primarySide;
        container.appendChild(pickPanelFor(sim, side, 'You', pressVirtual, ['1', '2', '3']));
        const opp = other(side);
        const oppPanel = document.createElement('div');
        oppPanel.className = 'pick-panel pick-waiting';
        oppPanel.textContent = sim.picks.chosen[opp] !== null
            ? (cfg.mode === 'online' ? 'Opponent is ready' : 'Enemy has chosen')
            : (cfg.mode === 'online' ? 'Waiting for opponent…' : 'Enemy is choosing…');
        container.appendChild(oppPanel);
    }
}

export function hidePicks() {
    $('upgradeOverlay').style.display = 'none';
}

// ---------------------------------------------------------------
// Net status indicator
// ---------------------------------------------------------------
export function setNetStatus(text) {
    const el = $('netStatus');
    if (!text) {
        el.style.display = 'none';
    } else {
        el.textContent = text;
        el.style.display = 'block';
    }
}
