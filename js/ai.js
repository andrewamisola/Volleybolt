// ============================================================
// VOLLEYBOLT - AI controller
//
// Produces input frames just like a keyboard would. Decisions run on
// a think timer (frame-rate independent - the old per-frame dice
// rolls made the AI ~2.4x harder on 144Hz monitors). AI only exists
// in offline modes, so it may use its own non-seeded randomness.
// ============================================================

import * as C from './config.js';
import { ABILITIES, PARRY_WINDOW } from './config.js';
import { other } from './sim.js';
import { mulberry32 } from './rng.js';

const THINK_INTERVAL = 0.45;       // Seconds between spell decisions
// Per-think probabilities tuned to match the legacy per-frame rates at 60fps
const FIREBALL_CHANCE = 0.35;
const FROSTBOLT_CHANCE = 0.22;
const LIGHTNING_INTERRUPT_CHANCE = 0.5;
const INITIAL_DELAY = 2.0;         // Grace period at round start

export function createAI(side, seed = 12345) {
    const rng = mulberry32(seed ^ 0x9E3779B9);
    let thinkT = 0;
    let roundDelay = INITIAL_DELAY;
    let queuedCast = null;
    const parryRolled = new Set();  // Projectile ids we already decided on
    let pendingPick = null;
    let pickDelay = 0;

    return function getInput(sim) {
        const w = sim.wizards[side];
        const opp = sim.wizards[other(side)];
        const dt = C.DT;

        // --- Upgrade picking ---
        if (sim.phase === 'picking') {
            if (sim.picks && sim.picks.chosen[side] === null) {
                if (pendingPick === null) {
                    pendingPick = Math.floor(rng() * 3);
                    pickDelay = 0.8 + rng() * 0.8; // "thinking" pause
                }
                pickDelay -= dt;
                if (pickDelay <= 0) {
                    const pick = pendingPick;
                    pendingPick = null;
                    return { move: 0, parry: false, cast: null, pick };
                }
            }
            return { move: 0, parry: false, cast: null, pick: null };
        }
        pendingPick = null;

        if (sim.phase !== 'playing') {
            roundDelay = INITIAL_DELAY;
            parryRolled.clear();
            return { move: 0, parry: false, cast: null, pick: null };
        }

        if (roundDelay > 0) roundDelay -= dt;

        const incomingSign = side === 'left' ? -1 : 1; // velX of threats
        const frame = { move: 0, parry: false, cast: null, pick: null };

        // --- Movement: track the nearest incoming projectile ---
        let nearest = null;
        let nearestDist = Infinity;
        for (const proj of sim.projectiles) {
            if (Math.sign(proj.velX) !== incomingSign) continue;
            const dist = (proj.x - w.x) * -incomingSign;
            if (dist > 0 && dist < nearestDist) { nearestDist = dist; nearest = proj; }
        }
        if (nearest) {
            const diff = nearest.z - w.z;
            if (Math.abs(diff) > 0.2) frame.move = Math.sign(diff);
        }

        // --- Parry: decide once per projectile as it enters the window ---
        for (const proj of sim.projectiles) {
            if (Math.sign(proj.velX) !== incomingSign) continue;
            if (!ABILITIES[proj.type].canParry) continue;
            const dist = (proj.x - w.x) * -incomingSign;
            if (dist < 0 || dist > PARRY_WINDOW * w.stats.parryWindow) continue;
            if (Math.abs(proj.z - w.z) > 1.5) continue;
            if (parryRolled.has(proj.id)) continue;
            parryRolled.add(proj.id);
            // Strategic: parry harder to return when the opponent is out of position
            const oppOffset = Math.abs(proj.z - opp.z);
            const chance = oppOffset > 2.5 ? 0.7 : (oppOffset > 1.5 ? 0.3 : 0);
            if (rng() < chance) frame.parry = true;
        }
        // Forget ids of projectiles that no longer exist
        if (parryRolled.size > 32) {
            const alive = new Set(sim.projectiles.map(p => p.id));
            for (const id of parryRolled) if (!alive.has(id)) parryRolled.delete(id);
        }

        // --- Spell decisions on a timer ---
        if (queuedCast) {
            frame.cast = queuedCast;
            queuedCast = null;
            return frame;
        }

        thinkT += dt;
        if (thinkT < THINK_INTERVAL || roundDelay > 0 || w.freezeT > 0) return frame;
        thinkT = 0;

        const dangerClose = sim.projectiles.some(p =>
            Math.sign(p.velX) === incomingSign &&
            (p.x - w.x) * -incomingSign > 0 &&
            (p.x - w.x) * -incomingSign < 8.5);

        // Lightning to interrupt an enemy channel (its whole purpose)
        if (opp.casting && w.cooldowns.lightning <= 0 && w.mana >= ABILITIES.lightning.manaCost) {
            if (rng() < LIGHTNING_INTERRUPT_CHANCE) { queuedCast = 'lightning'; return frame; }
        }
        // Frostbolt occasionally
        if (w.cooldowns.frostbolt <= 0 && w.mana >= ABILITIES.frostbolt.manaCost &&
            sim.projectiles.length < 10 && rng() < FROSTBOLT_CHANCE) {
            queuedCast = 'frostbolt';
            return frame;
        }
        // Fireball when it's safe to stand still and channel
        if (!w.casting && w.cooldowns.fireball <= 0 && w.mana >= ABILITIES.fireball.manaCost &&
            sim.projectiles.length < 10 && !dangerClose && rng() < FIREBALL_CHANCE) {
            queuedCast = 'fireball';
            return frame;
        }
        return frame;
    };
}
