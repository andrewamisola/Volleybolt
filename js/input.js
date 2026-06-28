// ============================================================
// VOLLEYBOLT - Input
//
// Keyboard state plus edge-latched action presses, sampled once per
// sim tick into plain input frames {move, parry, cast, pick}.
// The sim never touches the keyboard - any input source (keyboard,
// AI, network) produces the same frame shape.
// ============================================================

const keys = {};
let listenersAttached = false;

// Latched one-shot presses per player slot, consumed on sample.
const latched = {
    p1: { parry: false, cast: null, pick: null },
    p2: { parry: false, cast: null, pick: null }
};

export const KEYMAPS = {
    // Solo: P1 gets both WASD and arrows
    p1Solo: {
        up: ['KeyW', 'ArrowUp'], down: ['KeyS', 'ArrowDown'],
        parry: ['Space'],
        casts: { Digit1: 'fireball', Digit2: 'frostbolt', Digit3: 'lightning' },
        picks: { Digit1: 0, Digit2: 1, Digit3: 2 }
    },
    // Local 2P: P1 left side of keyboard
    p1Duo: {
        up: ['KeyW'], down: ['KeyS'],
        parry: ['Space'],
        casts: { Digit1: 'fireball', Digit2: 'frostbolt', Digit3: 'lightning' },
        picks: { Digit1: 0, Digit2: 1, Digit3: 2 }
    },
    // Local 2P: P2 right side of keyboard
    p2Duo: {
        up: ['ArrowUp'], down: ['ArrowDown'],
        parry: ['Enter', 'NumpadEnter'],
        casts: { Digit8: 'fireball', Digit9: 'frostbolt', Digit0: 'lightning' },
        picks: { Digit8: 0, Digit9: 1, Digit0: 2 }
    }
};

let activeMaps = { p1: KEYMAPS.p1Solo, p2: null };
let onFirstInteraction = null;
let onKeyFeedback = null;

export function setKeymaps(p1Map, p2Map) {
    activeMaps.p1 = p1Map;
    activeMaps.p2 = p2Map;
}

export function setCallbacks({ firstInteraction, keyFeedback }) {
    onFirstInteraction = firstInteraction || null;
    onKeyFeedback = keyFeedback || null;
}

function latchFor(slot, map, code) {
    if (!map) return;
    const l = latched[slot];
    if (map.parry.includes(code)) l.parry = true;
    if (map.casts[code]) l.cast = map.casts[code];
    if (map.picks[code] !== undefined) l.pick = map.picks[code];
}

export function attachKeyboard() {
    if (listenersAttached) return;
    listenersAttached = true;

    document.addEventListener('keydown', (e) => {
        keys[e.code] = true;
        if (onFirstInteraction) onFirstInteraction();
        if (onKeyFeedback) onKeyFeedback(e.code);
        latchFor('p1', activeMaps.p1, e.code);
        latchFor('p2', activeMaps.p2, e.code);
        // Don't let Space/arrows scroll the page
        if (['Space', 'ArrowUp', 'ArrowDown'].includes(e.code)) e.preventDefault();
    });
    document.addEventListener('keyup', (e) => { keys[e.code] = false; });

    // Stuck-key fix: clear all held keys when the window loses focus
    window.addEventListener('blur', () => {
        for (const k of Object.keys(keys)) keys[k] = false;
    });
}

function moveFrom(map) {
    let move = 0;
    if (map.up.some(k => keys[k])) move = 1;
    if (map.down.some(k => keys[k])) move = -1;
    return move;
}

// Synthetic presses from on-screen buttons route into P1's latch.
export function pressVirtual(action, value) {
    if (action === 'parry') latched.p1.parry = true;
    else if (action === 'cast') latched.p1.cast = value;
    else if (action === 'pick') latched.p1.pick = value;
}

export function pressVirtualP2(action, value) {
    if (action === 'pick') latched.p2.pick = value;
}

// Sample an input frame for a player slot; consumes latched presses.
export function sample(slot) {
    const map = activeMaps[slot];
    if (!map) return { move: 0, parry: false, cast: null, pick: null };
    const l = latched[slot];
    const frame = {
        move: moveFrom(map),
        parry: l.parry,
        cast: l.cast,
        pick: l.pick
    };
    l.parry = false;
    l.cast = null;
    l.pick = null;
    return frame;
}

// Flip vertical movement (online joiner sees a mirrored camera).
export function flipMove(frame) {
    return { ...frame, move: -frame.move };
}
