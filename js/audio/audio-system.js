/**
 * Volleybolt - Audio System
 *
 * Comprehensive audio system including:
 * - Web Audio API wrapper for basic sound playback
 * - Tone.js integration for sound therapy and 8-bit effects
 * - Isochronic generator for brainwave entrainment
 * - Music player with bitcrusher effect
 */

// ============================================================
// WEB AUDIO API - Basic Sound System
// ============================================================

let audioCtx = null;
let masterGain = null;
let masterVolume = 0.5;
const soundBuffers = {};
const soundTableWidth = 20;

/**
 * Initialize audio context on first user interaction
 */
export function initAudioContext() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        masterGain = audioCtx.createGain();
        masterGain.gain.value = masterVolume;
        masterGain.connect(audioCtx.destination);
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
    return audioCtx;
}

/**
 * Set master volume (0-1) - controls both Web Audio and Tone.js
 */
export function setMasterVolume(vol) {
    masterVolume = vol;
    // Web Audio API master gain
    if (masterGain) {
        masterGain.gain.value = vol;
    }
    // Tone.js master volume (convert 0-1 to decibels)
    if (typeof Tone !== 'undefined' && Tone.getDestination) {
        if (vol === 0) {
            Tone.getDestination().volume.value = -Infinity;
        } else {
            Tone.getDestination().volume.value = 20 * Math.log10(vol);
        }
    }
}

/**
 * Load a sound file into a buffer
 */
export async function loadSound(name, url) {
    try {
        const response = await fetch(url);
        const arrayBuffer = await response.arrayBuffer();
        initAudioContext();
        const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);
        soundBuffers[name] = audioBuffer;
        console.log("Sound loaded:", name);
    } catch (err) {
        console.error("Failed to load sound:", name, err);
    }
}

/**
 * Convert X position to stereo pan (-0.5 left, +0.5 right) - capped at 50%
 */
export function xToPan(x) {
    return Math.max(-0.5, Math.min(0.5, x / (soundTableWidth / 2) * 0.5));
}

/**
 * Play a sound - routes through Tone.js sound therapy system
 */
export function playSound(name, x = 0, volume = 1.0, pitch = 1.0) {
    // Route to Tone.js ToneSFX system with panning
    if (window.ToneSFX && window.ToneSFX[name]) {
        if (window.setTonePan) window.setTonePan(x);
        window.ToneSFX[name]();
        return;
    }

    // Fallback to wav buffer system
    const buffer = soundBuffers[name];
    if (!buffer) {
        return;
    }

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

/**
 * Create a looping sound for projectiles
 */
export function createLoopingSound(name, x = 0, volume = 0.3) {
    const buffer = soundBuffers[name];
    if (!buffer) return null;

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

/**
 * Update position of a looping sound
 */
export function updateSoundPan(loopData, x) {
    if (loopData && loopData.panner) {
        loopData.panner.pan.value = xToPan(x);
    }
}

/**
 * Update pitch of a looping sound based on velocity
 */
export function updateSoundPitch(loopData, velocity, baseVelocity = 12) {
    if (loopData && loopData.source) {
        const ratio = velocity / baseVelocity;
        const pitch = Math.max(0.8, Math.min(1.5, 0.8 + (ratio - 0.5) * 0.7));
        loopData.source.playbackRate.value = pitch;
    }
}

/**
 * Stop and dispose a looping sound
 */
export function stopLoopingSound(loopData) {
    if (loopData && loopData.source) {
        try {
            loopData.source.stop();
        } catch (e) {}
    }
}

/**
 * Load all sounds (currently uses Tone.js instead)
 */
export async function loadAllSounds() {
    console.log("Sound therapy system ready (Tone.js)");
}

// ============================================================
// TONE.JS SOUND THERAPY SYSTEM
// ============================================================

let toneStarted = false;
const synths = {};
let therapyReverb = null;
let therapyDelay = null;
let therapyPanner = null;
let chipPanner = null;

// Musical frequency map - B minor pentatonic
const THERAPY_NOTES = {
    B2: 123.47, D3: 146.83, E3: 164.81, Fs3: 185.00, A3: 220,
    B3: 246.94, D4: 293.66, E4: 329.63, Fs4: 369.99, A4: 440,
    B4: 493.88, D5: 587.33, E5: 659.25, Fs5: 739.99, A5: 880, B5: 987.77
};

// Brainwave entrainment rates (Hz)
const BRAINWAVE = {
    delta: 2, theta: 6, alpha: 10, beta: 18, gamma: 40
};

/**
 * Initialize Tone.js audio system
 */
export async function initToneJS() {
    if (toneStarted) return;
    if (typeof Tone === 'undefined') {
        console.warn('Tone.js not loaded');
        return;
    }

    await Tone.start();
    toneStarted = true;
    console.log("Tone.js sound therapy system started");

    // Setup audio chains
    therapyPanner = new Tone.Panner(0).toDestination();

    therapyReverb = new Tone.Reverb({
        decay: 4, wet: 0.6, preDelay: 0.02
    }).connect(therapyPanner);
    await therapyReverb.generate();

    therapyDelay = new Tone.FeedbackDelay({
        delayTime: 0.3, feedback: 0.25, wet: 0.2
    }).connect(therapyReverb);

    // Synths
    synths.therapy = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: "sine" },
        envelope: { attack: 0.15, decay: 0.4, sustain: 0.3, release: 2.0 }
    }).connect(therapyDelay);
    synths.therapy.volume.value = -18;

    synths.harmonic = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: "sine" },
        envelope: { attack: 0.25, decay: 0.5, sustain: 0.2, release: 2.5 }
    }).connect(therapyReverb);
    synths.harmonic.volume.value = -22;

    synths.sub = new Tone.Synth({
        oscillator: { type: "sine" },
        envelope: { attack: 0.2, decay: 0.6, sustain: 0.2, release: 1.5 }
    }).connect(therapyReverb);
    synths.sub.volume.value = -20;

    synths.texture = new Tone.NoiseSynth({
        noise: { type: "pink" },
        envelope: { attack: 0.2, decay: 0.4, sustain: 0.05, release: 0.8 }
    });
    const noiseFilter = new Tone.Filter(1200, "lowpass").connect(therapyReverb);
    synths.texture.connect(noiseFilter);
    synths.texture.volume.value = -28;

    synths.bell = new Tone.Synth({
        oscillator: { type: "sine" },
        envelope: { attack: 0.01, decay: 0.8, sustain: 0.1, release: 1.5 }
    }).connect(therapyReverb);
    synths.bell.volume.value = -20;

    // 8-bit sample layer
    chipPanner = new Tone.Panner(0).toDestination();
    const bitCrusher = new Tone.BitCrusher(6).connect(chipPanner);
    const chipReverb = new Tone.Reverb({ decay: 1.0, wet: 0.2 }).connect(bitCrusher);
    await chipReverb.generate();

    synths.sampleChain = chipReverb;
    synths.bitCrusher = bitCrusher;
    synths.samples = {};

    // Load samples
    const sampleFiles = {
        fireballCast: 'sfx/fireball_cast.wav',
        woosh: 'sfx/woosh.wav',
        block: 'sfx/block.wav',
        parry: 'sfx/parry.wav',
        gateDamage: 'sfx/gate_hit_damage.wav',
        spellReady: 'sfx/spell_ready.wav',
        frostboltCast: 'sfx/frostbolt_cast.wav',
        frozen: 'sfx/frozen.wav',
        gravityCast: 'sfx/gravitysphere_cast.wav',
        gravityAbsorb: 'sfx/gravitysphere_absorb.wav',
        victory: 'sfx/victory.wav',
        defeat: 'sfx/defeat.wav',
        iceShatter: 'sfx/ice-shatter.wav',
        cancel: 'sfx/cancel.wav',
        overpowered: 'sfx/overpowered.wav'
    };

    for (const [name, path] of Object.entries(sampleFiles)) {
        try {
            synths.samples[name] = new Tone.Player(path).connect(chipReverb);
            synths.samples[name].volume.value = -3;
        } catch (e) {
            console.log("Could not load sample:", name);
        }
    }
    if (synths.samples.parry) synths.samples.parry.volume.value = -10;
    if (synths.samples.overpowered) synths.samples.overpowered.volume.value = -10;

    // Casting loops
    const playerCastPanner = new Tone.Panner(0.6).connect(chipReverb);
    synths.playerCastingLoop = new Tone.Player({
        url: 'sfx/mid-cast.wav', loop: true
    }).connect(playerCastPanner);
    synths.playerCastingLoop.volume.value = -8;

    const aiCastPanner = new Tone.Panner(-0.6).connect(chipReverb);
    synths.aiCastingLoop = new Tone.Player({
        url: 'sfx/mid-cast.wav', loop: true
    }).connect(aiCastPanner);
    synths.aiCastingLoop.volume.value = -8;

    // Music
    const musicBitCrusher = new Tone.BitCrusher(8).toDestination();
    synths.music = new Tone.Player({
        url: 'sfx/musica.ogg',
        loop: true,
        fadeIn: 0.5,
        fadeOut: 0.5,
        onload: () => console.log("Music loaded successfully")
    }).connect(musicBitCrusher);
    synths.music.volume.value = -12;

    console.log("Sound therapy + 8-bit samples + music initialized");
}

// Helper to play sample
function playSample(name) {
    if (synths.samples && synths.samples[name]) {
        try { synths.samples[name].stop(); } catch(e) {}
        synths.samples[name].start();
    }
}

// ============================================================
// ISOCHRONIC GENERATOR
// ============================================================

export class IsochronicGenerator {
    constructor() {
        this.initialized = false;
        this.oscillator = null;
        this.tremolo = null;
        this.volume = null;
        this.carrierFreq = THERAPY_NOTES.B3;
        this.pulseRate = BRAINWAVE.alpha;
    }

    async init() {
        if (this.initialized) return;
        if (!toneStarted) await initToneJS();

        this.oscillator = new Tone.Oscillator(this.carrierFreq, "sine").start();
        this.tremolo = new Tone.Tremolo(this.pulseRate, 0.8).start();
        this.volume = new Tone.Volume(-30);

        this.oscillator.connect(this.tremolo);
        this.tremolo.connect(this.volume);
        this.volume.connect(therapyReverb);
        this.volume.mute = true;
        this.initialized = true;
    }

    async setCarrier(freq) {
        await this.init();
        this.carrierFreq = freq;
        this.oscillator.frequency.rampTo(freq, 1);
    }

    async setBrainwave(state) {
        await this.init();
        const rate = BRAINWAVE[state] || BRAINWAVE.alpha;
        this.pulseRate = rate;
        this.tremolo.frequency.rampTo(rate, 2);
    }

    async start() {
        await this.init();
        this.volume.mute = false;
    }

    stop() {
        if (this.volume) this.volume.mute = true;
    }

    async rampTo(brainwaveState, durationSec = 2) {
        await this.init();
        const rate = BRAINWAVE[brainwaveState] || BRAINWAVE.alpha;
        this.tremolo.frequency.rampTo(rate, durationSec);
    }
}

export const isoGenerator = new IsochronicGenerator();

// ============================================================
// TONE SFX - Sound Effects
// ============================================================

const N = THERAPY_NOTES;

export const ToneSFX = {
    fireballCast: async () => {
        if (!toneStarted) await initToneJS();
        playSample('fireballCast');
    },
    frostboltCast: async () => {
        if (!toneStarted) await initToneJS();
        playSample('frostboltCast');
    },
    block: async () => {
        if (!toneStarted) await initToneJS();
        playSample('block');
    },
    parry: async () => {
        if (!toneStarted) await initToneJS();
        playSample('parry');
    },
    gateDamage: async () => {
        if (!toneStarted) await initToneJS();
        playSample('gateDamage');
    },
    spellReady: async () => {
        if (!toneStarted) await initToneJS();
        playSample('spellReady');
    },
    frozen: async () => {
        if (!toneStarted) await initToneJS();
        playSample('frozen');
    },
    victory: async () => {
        if (!toneStarted) await initToneJS();
        playSample('victory');
    },
    defeat: async () => {
        if (!toneStarted) await initToneJS();
        playSample('defeat');
    },
    woosh: async () => {
        if (!toneStarted) await initToneJS();
        playSample('woosh');
    },
    iceShatter: async () => {
        if (!toneStarted) await initToneJS();
        playSample('iceShatter');
    },
    cancel: async () => {
        if (!toneStarted) await initToneJS();
        playSample('cancel');
    },
    overpowered: async () => {
        if (!toneStarted) await initToneJS();
        playSample('overpowered');
    },
    gravityCast: async () => {
        if (!toneStarted) await initToneJS();
        playSample('gravityCast');
    },
    gravityAbsorb: async () => {
        if (!toneStarted) await initToneJS();
        playSample('gravityAbsorb');
    },
    castingStart: async (side = 'player') => {
        const loop = side === 'player' ? synths.playerCastingLoop : synths.aiCastingLoop;
        if (loop && loop.loaded) {
            try { loop.start(); } catch (e) {}
        }
    },
    castingStop: async (side = 'all') => {
        if (side === 'all' || side === 'player') {
            if (synths.playerCastingLoop) {
                try { synths.playerCastingLoop.stop(); } catch (e) {}
            }
        }
        if (side === 'all' || side === 'ai') {
            if (synths.aiCastingLoop) {
                try { synths.aiCastingLoop.stop(); } catch (e) {}
            }
        }
    },
    gameplayStart: async () => {
        if (!toneStarted) await initToneJS();
        await Tone.loaded();
        if (synths.music && synths.music.state !== 'started') {
            synths.music.start();
            console.log("Music started");
        }
    },
    roundEnd: async () => {},
    uiHover: async () => {},
    uiConfirm: async () => {},
    uiBack: async () => {},
    musicStart: async () => {
        if (!toneStarted) await initToneJS();
        if (synths.music && synths.music.state !== 'started') {
            synths.music.start();
        }
    },
    musicStop: async () => {
        if (synths.music && synths.music.state === 'started') {
            synths.music.stop();
        }
    },
    musicFadeOut: async (duration = 1) => {
        if (synths.music && synths.music.state === 'started') {
            synths.music.volume.rampTo(-60, duration);
            setTimeout(() => {
                synths.music.stop();
                synths.music.volume.value = -12;
            }, duration * 1000);
        }
    },
    musicSetVolume: (db) => {
        if (synths.music) {
            synths.music.volume.value = db;
        }
    }
};

/**
 * Set stereo pan based on X position
 */
export function setTonePan(x) {
    const pan = Math.max(-0.5, Math.min(0.5, x / 8 * 0.5));
    if (therapyPanner) therapyPanner.pan.value = pan;
    if (chipPanner) chipPanner.pan.value = pan;
}

/**
 * Play synth sound wrapper
 */
export async function playSynthSound(name, x = 0) {
    if (ToneSFX[name]) {
        setTonePan(x);
        await ToneSFX[name]();
    }
}

// ============================================================
// BACKWARD COMPATIBILITY - Expose on window
// ============================================================

if (typeof window !== 'undefined') {
    window.initAudioContext = initAudioContext;
    window.setMasterVolume = setMasterVolume;
    window.loadSound = loadSound;
    window.playSound = playSound;
    window.createLoopingSound = createLoopingSound;
    window.updateSoundPan = updateSoundPan;
    window.updateSoundPitch = updateSoundPitch;
    window.stopLoopingSound = stopLoopingSound;
    window.loadAllSounds = loadAllSounds;
    window.initToneJS = initToneJS;
    window.ToneSFX = ToneSFX;
    window.setTonePan = setTonePan;
    window.playSynthSound = playSynthSound;
    window.isoGenerator = isoGenerator;
}
