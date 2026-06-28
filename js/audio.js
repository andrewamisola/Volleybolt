// ============================================================
// VOLLEYBOLT - Audio
//
// Web Audio API sound system with stereo panning and velocity-based
// pitch. Consumes sim events; the sim itself never plays sounds.
// ============================================================

const SOUND_FILES = {
    fireballCast: 'sfx/fireball_cast.wav',
    fireballLoop: 'sfx/fireball_loop.wav',
    woosh: 'sfx/woosh.wav',
    block: 'sfx/block.wav',
    parry: 'sfx/parry.wav',
    gateDamage: 'sfx/gate_hit_damage.wav',
    spellReady: 'sfx/spell_ready.wav',
    fireballApproaching: 'sfx/fireball_approaching.wav',
    frostboltCast: 'sfx/frostbolt_cast.wav',
    frostboltLoop: 'sfx/ice_blast_travel.wav',
    frozen: 'sfx/frozen.wav',
    victory: 'sfx/victory.wav',
    defeat: 'sfx/defeat.wav',
    castingLoop: 'sfx/mid-cast.wav',
    iceShatter: 'sfx/ice-shatter.wav'
};

const TABLE_WIDTH = 20;

let audioCtx = null;
let masterGain = null;
let masterVolume = 0.5;
const buffers = {};
const projLoops = new Map();   // projectile id -> loop handle
const castLoops = { left: null, right: null };

export function initAudioContext() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        masterGain = audioCtx.createGain();
        masterGain.gain.value = masterVolume;
        masterGain.connect(audioCtx.destination);
    }
    if (audioCtx.state === 'suspended') audioCtx.resume();
    return audioCtx;
}

export function setMasterVolume(vol) {
    masterVolume = vol;
    if (masterGain) masterGain.gain.value = vol;
}

export async function loadAllSounds() {
    await Promise.all(Object.entries(SOUND_FILES).map(async ([name, url]) => {
        try {
            const response = await fetch(url);
            const arrayBuffer = await response.arrayBuffer();
            initAudioContext();
            buffers[name] = await audioCtx.decodeAudioData(arrayBuffer);
        } catch (err) {
            console.error('Failed to load sound:', name, err);
        }
    }));
}

const xToPan = (x) => Math.max(-0.5, Math.min(0.5, (x / (TABLE_WIDTH / 2)) * 0.5));

export function playSound(name, x = 0, volume = 1.0, pitch = 1.0) {
    const buffer = buffers[name];
    if (!buffer || !audioCtx) return;
    initAudioContext();
    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    source.playbackRate.value = pitch;
    const gainNode = audioCtx.createGain();
    gainNode.gain.value = volume;
    const panner = audioCtx.createStereoPanner();
    panner.pan.value = xToPan(x);
    source.connect(gainNode);
    gainNode.connect(panner);
    panner.connect(masterGain);
    source.start(0);
}

function createLoop(name, x = 0, volume = 0.3) {
    const buffer = buffers[name];
    if (!buffer || !audioCtx) return null;
    initAudioContext();
    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    source.loop = true;
    const gainNode = audioCtx.createGain();
    gainNode.gain.value = volume;
    const panner = audioCtx.createStereoPanner();
    panner.pan.value = xToPan(x);
    source.connect(gainNode);
    gainNode.connect(panner);
    panner.connect(masterGain);
    source.start(0);
    return { source, panner, gainNode };
}

function stopLoop(loop) {
    if (loop && loop.source) {
        try { loop.source.stop(); } catch (e) { /* already stopped */ }
    }
}

const LOOP_BY_TYPE = {
    fireball: { name: 'fireballLoop', volume: 0.12 },
    frostbolt: { name: 'frostboltLoop', volume: 0.1 }
    // lightning is too fast for a loop to register
};

// ---------------------------------------------------------------
// Event consumption
// localSides: array of sides this client controls (for personal cues
// like "spell ready" and the approach warning).
// ---------------------------------------------------------------
export function handleEvents(events, sim, localSides) {
    for (const e of events) {
        switch (e.type) {
            case 'spawn': {
                const castSound = e.proj.type === 'frostbolt' ? 'frostboltCast'
                    : e.proj.type === 'lightning' ? 'woosh' : 'fireballCast';
                const pitch = e.proj.type === 'lightning' ? 1.7 : 1.0;
                playSound(castSound, e.proj.x, e.proj.type === 'lightning' ? 0.9 : 0.8, pitch);
                const loopCfg = LOOP_BY_TYPE[e.proj.type];
                if (loopCfg) {
                    const loop = createLoop(loopCfg.name, e.proj.x, loopCfg.volume);
                    if (loop) projLoops.set(e.proj.id, loop);
                }
                break;
            }
            case 'destroy': {
                stopLoop(projLoops.get(e.id));
                projLoops.delete(e.id);
                break;
            }
            case 'block':
                playSound('block', e.x, 0.7);
                break;
            case 'parry':
                playSound('parry', e.x, 0.9);
                break;
            case 'wallBounce':
                playSound('woosh', e.x, 0.5);
                break;
            case 'gateHit':
                playSound('gateDamage', e.side === 'left' ? -10 : 10, 0.6 + e.damage * 0.15);
                break;
            case 'freeze':
                playSound('frozen', e.x, 0.8, 2.0);
                break;
            case 'unfreeze':
                playSound('iceShatter', sim.wizards[e.side].x, 0.6);
                break;
            case 'approach':
                if (localSides.includes(e.side)) playSound('fireballApproaching', e.x, 0.5);
                break;
            case 'spellReady':
                if (localSides.includes(e.side)) playSound('spellReady', e.x, 0.6);
                break;
            case 'castStart': {
                const w = sim.wizards[e.side];
                stopLoop(castLoops[e.side]);
                castLoops[e.side] = createLoop('castingLoop', w.x, e.side === 'left' ? 0.15 : 0.1);
                break;
            }
            case 'castCancel':
            case 'castComplete':
                stopLoop(castLoops[e.side]);
                castLoops[e.side] = null;
                break;
            case 'suddenDeath':
                playSound('spellReady', 0, 0.8, 0.7);
                break;
            case 'roundEnd': {
                const localWon = localSides.includes(e.winner);
                playSound(localWon || localSides.length > 1 ? 'victory' : 'defeat', 0, 0.8);
                break;
            }
            case 'roundReset':
            case 'matchReset':
                stopAllLoops();
                break;
            default:
                break;
        }
    }
}

// Per-frame: keep loop pan/pitch in sync with projectile motion
export function updateLoops(sim) {
    for (const proj of sim.projectiles) {
        const loop = projLoops.get(proj.id);
        if (!loop) continue;
        loop.panner.pan.value = xToPan(proj.x);
        const speed = Math.sqrt(proj.velX * proj.velX + proj.velZ * proj.velZ);
        const ratio = speed / 12;
        loop.source.playbackRate.value = Math.max(0.8, Math.min(1.5, 0.8 + (ratio - 0.5) * 0.7));
    }
}

export function stopAllLoops() {
    for (const loop of projLoops.values()) stopLoop(loop);
    projLoops.clear();
    stopLoop(castLoops.left);
    stopLoop(castLoops.right);
    castLoops.left = null;
    castLoops.right = null;
}
