// ============================================================
// VOLLEYBOLT - Deterministic simulation
//
// Pure game state advanced in fixed 60Hz ticks. No Babylon, no DOM,
// no Math.random, no wall-clock time. Renderer/audio/UI consume the
// state plus the per-tick `events` queue. Identical (seed, inputs)
// always produce identical state - this is what makes lockstep
// multiplayer possible.
// ============================================================

import * as C from './config.js';
import { ABILITIES, UPGRADES, volleyDamage } from './config.js';
import { mulberry32 } from './rng.js';

export const SIDES = ['left', 'right'];
export const other = (side) => (side === 'left' ? 'right' : 'left');

// Empty input frame: move -1|0|1, parry pressed, cast ability id, pick 0-2
export const EMPTY_INPUT = Object.freeze({ move: 0, parry: false, cast: null, pick: null });

function makeWizard(side) {
    return {
        side,
        x: side === 'left' ? -C.PADDLE_X : C.PADDLE_X,
        z: 0,
        prevZ: 0,
        mana: C.STARTING_MANA,
        regenT: 0,
        freezeT: 0,
        casting: null,        // ability id while channeling
        castProg: 0,
        castTime: 0,
        cooldowns: { fireball: 0, frostbolt: 0, lightning: 0 },
        parryLock: 0,
        lastMove: 0,          // for render animation
        stats: {
            maxMana: C.MAX_MANA,
            moveSpeed: 1,
            parryWindow: 1,
            fireballDmg: 0,
            freezeBonus: 0,
            cooldownMult: 1,
            castTimeMult: 1,
            regenMult: 1
        },
        upgrades: []
    };
}

export function createSim(seed) {
    return {
        seed,
        rng: mulberry32(seed),
        tick: 0,
        phase: 'serve',        // serve | playing | roundEnd | picking | matchEnd
        phaseT: 0,
        wizards: { left: makeWizard('left'), right: makeWizard('right') },
        projectiles: [],
        nextId: 1,
        gateHP: { left: C.MAX_GATE_HP, right: C.MAX_GATE_HP },
        scores: { left: 0, right: 0 },
        roundTimer: C.ROUND_TIME,
        suddenDeath: false,
        hitstop: 0,
        picks: null,           // { options: {left:[idx], right:[idx]}, chosen: {left,right} }
        matchWinner: null,
        events: []
    };
}

const ev = (sim, e) => sim.events.push(e);

// ---------------------------------------------------------------
// Mana
// ---------------------------------------------------------------
function gainMana(sim, w, amount) {
    const before = w.mana;
    w.mana = Math.min(w.stats.maxMana, w.mana + amount);
    if (w.mana !== before) ev(sim, { type: 'mana', side: w.side });
}

function spendMana(sim, w, amount) {
    if (w.mana < amount) return false;
    w.mana -= amount;
    ev(sim, { type: 'mana', side: w.side });
    return true;
}

// ---------------------------------------------------------------
// Projectiles
// ---------------------------------------------------------------
function spawnProjectile(sim, ownerSide, abilityId) {
    const w = sim.wizards[ownerSide];
    const a = ABILITIES[abilityId];
    const dir = ownerSide === 'left' ? 1 : -1;
    // Small random launch angle (deterministic via sim rng)
    const spread = abilityId === 'fireball' ? 0.4 : 0.3;
    const angle = (sim.rng() - 0.5) * spread;

    const proj = {
        id: sim.nextId++,
        type: abilityId,
        owner: ownerSide,
        x: w.x + dir * 1,
        z: w.z,
        y: 0.7,
        prevX: w.x + dir * 1,
        prevZ: w.z,
        prevY: 0.7,
        velX: dir * a.speed,
        velZ: Math.sin(angle) * a.speed * (abilityId === 'fireball' ? 0.3 : 0.2),
        velY: 0,
        speed: a.speed,
        isParried: false,
        parriedBy: null,
        volleyCount: 0,
        approachPlayed: false,
        time: 0
    };
    sim.projectiles.push(proj);
    ev(sim, { type: 'spawn', proj });
    return proj;
}

function destroyProjectile(sim, proj, reason) {
    const idx = sim.projectiles.indexOf(proj);
    if (idx > -1) sim.projectiles.splice(idx, 1);
    ev(sim, { type: 'destroy', id: proj.id, projType: proj.type, reason, x: proj.x, z: proj.z });
}

function clearProjectiles(sim) {
    while (sim.projectiles.length > 0) destroyProjectile(sim, sim.projectiles[0], 'clear');
}

// ---------------------------------------------------------------
// Casting
// ---------------------------------------------------------------
function tryCast(sim, w, abilityId) {
    const a = ABILITIES[abilityId];
    if (!a) return;
    if (w.freezeT > 0) return;
    if (w.cooldowns[abilityId] > 0) return;
    if (a.castTime > 0) {
        // Channeled spell
        if (w.casting) return;
        if (!spendMana(sim, w, a.manaCost)) return;
        w.casting = abilityId;
        w.castProg = 0;
        w.castTime = a.castTime * w.stats.castTimeMult;
        ev(sim, { type: 'castStart', side: w.side, ability: abilityId });
    } else {
        // Instant spell
        if (!spendMana(sim, w, a.manaCost)) return;
        w.cooldowns[abilityId] = a.cooldown * w.stats.cooldownMult;
        spawnProjectile(sim, w.side, abilityId);
        ev(sim, { type: 'castInstant', side: w.side, ability: abilityId, x: w.x });
    }
}

function cancelCast(sim, w, refund) {
    if (!w.casting) return;
    const a = ABILITIES[w.casting];
    if (refund && a) gainMana(sim, w, a.manaCost);
    ev(sim, { type: 'castCancel', side: w.side, ability: w.casting });
    w.casting = null;
    w.castProg = 0;
}

function completeCast(sim, w) {
    const abilityId = w.casting;
    const a = ABILITIES[abilityId];
    w.casting = null;
    w.castProg = 0;
    w.cooldowns[abilityId] = a.cooldown * w.stats.cooldownMult;
    spawnProjectile(sim, w.side, abilityId);
    ev(sim, { type: 'castComplete', side: w.side, ability: abilityId, x: w.x });
}

function applyCastPushback(sim, w) {
    if (!w.casting) return;
    const a = ABILITIES[w.casting];
    const pushback = (a && a.pushbackOnHit) || 0.3;
    w.castProg = Math.max(0, w.castProg - pushback);
    ev(sim, { type: 'castPushback', side: w.side });
}

// ---------------------------------------------------------------
// Parry
// ---------------------------------------------------------------
function tryParry(sim, w) {
    ev(sim, { type: 'parryAttempt', side: w.side });
    if (w.parryLock > 0) return;

    const incoming = w.side === 'left' ? -1 : 1; // velX sign of projectiles coming at us
    const halfDepth = 1.5;
    const windowDist = C.PARRY_WINDOW * w.stats.parryWindow;
    let best = null;
    let bestDist = Infinity;

    for (const proj of sim.projectiles) {
        if (!ABILITIES[proj.type].canParry) continue;
        if (Math.sign(proj.velX) !== incoming) continue;
        // Distance in front of the paddle, toward the incoming projectile
        const dist = (proj.x - w.x) * -incoming;
        if (dist < 0 || dist > windowDist) continue;
        if (Math.abs(proj.z - w.z) > halfDepth) continue;
        if (dist < bestDist) { bestDist = dist; best = proj; }
    }
    if (!best) return;

    // Successful parry
    w.parryLock = C.PARRY_LOCK;
    gainMana(sim, w, C.PARRY_MANA);
    sim.hitstop = C.HITSTOP_TICKS;

    best.isParried = true;
    best.parriedBy = w.side;
    best.speed = Math.min(best.speed * C.PARRY_BOOST, C.MAX_PARRY_SPEED);

    const outDir = w.side === 'left' ? 1 : -1;
    best.velX = outDir * best.speed * 0.85;
    const aim = w.lastMove; // directional parry: aim with held movement
    if (aim !== 0) {
        best.velZ = aim * best.speed * 0.6;
    } else {
        best.velZ *= 0.5;
    }
    best.velY = 0;
    best.y = C.TABLE_Y;

    ev(sim, { type: 'parry', side: w.side, id: best.id, x: best.x, z: best.z });
}

// ---------------------------------------------------------------
// Round / match flow
// ---------------------------------------------------------------
function startRound(sim) {
    sim.phase = 'playing';
    sim.roundTimer = C.ROUND_TIME;
    sim.suddenDeath = false;
    for (const side of SIDES) {
        const w = sim.wizards[side];
        w.mana = C.STARTING_MANA;
        w.regenT = 0;
        w.freezeT = 0;
        w.casting = null;
        w.castProg = 0;
        w.parryLock = 0;
        w.cooldowns = { fireball: 0, frostbolt: 0, lightning: 0 };
        ev(sim, { type: 'mana', side });
    }
    ev(sim, { type: 'roundStart' });
}

function endRound(sim, winner) {
    sim.scores[winner]++;
    clearProjectiles(sim);
    for (const side of SIDES) cancelCast(sim, sim.wizards[side], false);
    ev(sim, { type: 'roundEnd', winner, scores: { ...sim.scores } });

    if (sim.scores[winner] >= C.WINNING_SCORE) {
        sim.matchWinner = winner;
        sim.phase = 'matchEnd';
        sim.phaseT = C.MATCH_END_DELAY;
        ev(sim, { type: 'matchEnd', winner });
    } else {
        sim.phase = 'roundEnd';
        sim.phaseT = C.ROUND_END_DELAY;
    }
}

function generatePicks(sim) {
    const pickThree = () => {
        const pool = UPGRADES.map((_, i) => i);
        const out = [];
        for (let n = 0; n < 3; n++) {
            const i = Math.floor(sim.rng() * pool.length);
            out.push(pool.splice(i, 1)[0]);
        }
        return out;
    };
    sim.picks = {
        options: { left: pickThree(), right: pickThree() },
        chosen: { left: null, right: null }
    };
    sim.phase = 'picking';
    ev(sim, { type: 'showPicks', picks: sim.picks });
}

function resetForNextRound(sim) {
    sim.gateHP.left = C.MAX_GATE_HP;
    sim.gateHP.right = C.MAX_GATE_HP;
    sim.projectiles.length = 0;
    sim.picks = null;
    sim.phase = 'serve';
    for (const side of SIDES) {
        sim.wizards[side].freezeT = 0;
        sim.wizards[side].z = 0;
        sim.wizards[side].prevZ = 0;
    }
    ev(sim, { type: 'roundReset' });
}

function resetMatch(sim) {
    sim.scores.left = 0;
    sim.scores.right = 0;
    sim.matchWinner = null;
    for (const side of SIDES) {
        const w = sim.wizards[side];
        const fresh = makeWizard(side);
        w.stats = fresh.stats;
        w.upgrades = [];
        w.mana = C.STARTING_MANA;
    }
    resetForNextRound(sim);
    ev(sim, { type: 'matchReset' });
}

// ---------------------------------------------------------------
// Per-wizard update during play
// ---------------------------------------------------------------
function updateWizard(sim, w, input) {
    const dt = C.DT;

    // Cooldowns
    for (const id of Object.keys(w.cooldowns)) {
        if (w.cooldowns[id] > 0) {
            w.cooldowns[id] -= dt;
            if (w.cooldowns[id] <= 0) {
                w.cooldowns[id] = 0;
                ev(sim, { type: 'spellReady', side: w.side, ability: id, x: w.x });
            }
        }
    }
    if (w.parryLock > 0) w.parryLock -= dt;

    // Passive mana regen
    w.regenT += dt;
    if (w.regenT >= C.MANA_REGEN_TIME * w.stats.regenMult) {
        w.regenT = 0;
        gainMana(sim, w, 1);
    }

    // Freeze
    if (w.freezeT > 0) {
        w.freezeT -= dt;
        if (w.freezeT <= 0) {
            w.freezeT = 0;
            ev(sim, { type: 'unfreeze', side: w.side });
        }
        w.prevZ = w.z;
        w.lastMove = 0;
        return; // No actions while frozen
    }

    // Casting progress
    if (w.casting) {
        w.castProg += dt;
        if (w.castProg >= w.castTime) completeCast(sim, w);
    }

    // Movement (cancels channel with refund)
    const move = input.move | 0;
    if (move !== 0 && w.casting) cancelCast(sim, w, true);
    w.prevZ = w.z;
    w.z += move * C.PADDLE_SPEED * w.stats.moveSpeed * dt;
    w.z = Math.max(-C.PADDLE_BOUND, Math.min(C.PADDLE_BOUND, w.z));
    w.lastMove = move;

    // Actions
    if (input.parry) tryParry(sim, w);
    if (input.cast) tryCast(sim, w, input.cast);
}

// ---------------------------------------------------------------
// Paddle collision (swept: catches fast projectiles that would
// cross the paddle plane within a single tick)
// ---------------------------------------------------------------
function checkPaddleHit(sim, proj, w) {
    const incoming = w.side === 'left' ? -1 : 1;
    if (Math.sign(proj.velX) !== incoming) return false;
    if (proj.y >= C.MAX_HIT_HEIGHT) return false;

    // Front face plane x: left wizard faces +x, right wizard faces -x
    const faceX = w.side === 'left' ? w.x + C.PADDLE_HALF_W : w.x - C.PADDLE_HALF_W;
    const backX = w.side === 'left' ? w.x - C.PADDLE_HALF_W : w.x + C.PADDLE_HALF_W;

    const prevEdge = proj.prevX + incoming * C.BALL_R; // leading edge last tick
    const currEdge = proj.x + incoming * C.BALL_R;

    // Crossed (or is inside) the face this tick, but hasn't passed the back
    const crossed = w.side === 'left'
        ? (prevEdge > faceX || proj.prevX > backX) && currEdge <= faceX && proj.x >= backX - 1
        : (prevEdge < faceX || proj.prevX < backX) && currEdge >= faceX && proj.x <= backX + 1;
    if (!crossed) return false;

    const hitDepth = C.PADDLE_HALF_D + C.PERSPECTIVE_Z;
    if (proj.z < w.z - hitDepth || proj.z > w.z + hitDepth) return false;
    return true;
}

function resolvePaddleHit(sim, proj, w, toDestroy) {
    const a = ABILITIES[proj.type];

    if (a.destroyedOnPaddleHit) {
        // Frostbolt: freeze the defender
        const attacker = sim.wizards[other(w.side)];
        const freezeDur = (a.freeze || 1) + (proj.type === 'frostbolt' ? attacker.stats.freezeBonus : 0);
        w.freezeT = freezeDur;
        if (w.casting) cancelCast(sim, w, true);
        ev(sim, { type: 'freeze', side: w.side, duration: freezeDur, x: proj.x, z: proj.z });
        toDestroy.push(proj);
        return;
    }

    // Block: reflect
    proj.x = w.side === 'left'
        ? w.x + C.PADDLE_HALF_W + C.BALL_R
        : w.x - C.PADDLE_HALF_W - C.BALL_R;
    if (proj.isParried && proj.parriedBy === other(w.side)) {
        proj.isParried = false;
        proj.parriedBy = null;
    }
    proj.velX = -proj.velX;
    const hitOffset = (proj.z - w.z) / C.PADDLE_HALF_D;
    proj.velZ += hitOffset * 5;
    proj.volleyCount++;
    gainMana(sim, w, C.BLOCK_MANA);
    if (w.casting) applyCastPushback(sim, w);
    ev(sim, { type: 'block', side: w.side, id: proj.id, volley: proj.volleyCount, x: proj.x, z: proj.z });
}

// ---------------------------------------------------------------
// Gate hit
// ---------------------------------------------------------------
function resolveGateHit(sim, proj, gateSide, toDestroy) {
    const a = ABILITIES[proj.type];
    toDestroy.push(proj);

    if (a.destroyedOnPaddleHit) {
        // Frostbolt fizzles at gates
        ev(sim, { type: 'gateFizzle', side: gateSide, x: proj.x, z: proj.z, projType: proj.type });
        return;
    }

    const attacker = sim.wizards[other(gateSide)];
    const bonus = proj.type === 'fireball' ? attacker.stats.fireballDmg : 0;
    const damage = volleyDamage(proj.type, proj.volleyCount, bonus);
    sim.gateHP[gateSide] = Math.max(0, sim.gateHP[gateSide] - damage);
    ev(sim, {
        type: 'gateHit', side: gateSide, damage, z: proj.z,
        projType: proj.type, hp: sim.gateHP[gateSide]
    });

    if (sim.gateHP[gateSide] <= 0 || sim.suddenDeath) {
        endRound(sim, other(gateSide));
    }
}

// ---------------------------------------------------------------
// Main tick
// ---------------------------------------------------------------
export function simTick(sim, inputLeft, inputRight) {
    sim.tick++;
    const inputs = { left: inputLeft || EMPTY_INPUT, right: inputRight || EMPTY_INPUT };
    const dt = C.DT;

    switch (sim.phase) {
        case 'serve': {
            // Either side pressing parry/serve starts the round (deterministic:
            // both clients see both inputs).
            if (inputs.left.parry || inputs.right.parry) startRound(sim);
            return;
        }
        case 'roundEnd': {
            sim.phaseT -= dt;
            if (sim.phaseT <= 0) generatePicks(sim);
            return;
        }
        case 'matchEnd': {
            sim.phaseT -= dt;
            if (sim.phaseT <= 0) resetMatch(sim);
            return;
        }
        case 'picking': {
            for (const side of SIDES) {
                const pick = inputs[side].pick;
                if (sim.picks.chosen[side] === null && pick !== null && pick !== undefined) {
                    const idx = Math.max(0, Math.min(2, pick | 0));
                    sim.picks.chosen[side] = idx;
                    const upgrade = UPGRADES[sim.picks.options[side][idx]];
                    upgrade.apply(sim.wizards[side], sim);
                    sim.wizards[side].upgrades.push(upgrade.id);
                    ev(sim, { type: 'picked', side, upgradeId: upgrade.id });
                }
            }
            if (sim.picks.chosen.left !== null && sim.picks.chosen.right !== null) {
                resetForNextRound(sim);
            }
            return;
        }
        case 'playing':
            break;
        default:
            return;
    }

    // --- Hit-stop: brief deterministic freeze after a parry ---
    if (sim.hitstop > 0) {
        sim.hitstop--;
        return;
    }

    // --- Round timer / sudden death ---
    sim.roundTimer -= dt;
    if (sim.roundTimer <= 0 && !sim.suddenDeath) {
        sim.roundTimer = 0;
        if (sim.gateHP.left !== sim.gateHP.right) {
            endRound(sim, sim.gateHP.left > sim.gateHP.right ? 'left' : 'right');
            return;
        }
        sim.suddenDeath = true;
        ev(sim, { type: 'suddenDeath' });
    }

    // --- Wizards ---
    updateWizard(sim, sim.wizards.left, inputs.left);
    if (sim.phase !== 'playing') return; // a cast/effect may have ended the round
    updateWizard(sim, sim.wizards.right, inputs.right);
    if (sim.phase !== 'playing') return;

    // --- Projectiles ---
    const toDestroy = [];
    for (const proj of sim.projectiles) {
        proj.prevX = proj.x;
        proj.prevZ = proj.z;
        proj.prevY = proj.y;
        proj.time += dt;

        proj.x += proj.velX * dt;
        proj.z += proj.velZ * dt;

        // Vertical physics: settle to float height
        proj.velY += C.GRAVITY_Y * dt;
        proj.y += proj.velY * dt;
        if (proj.y < C.TABLE_Y) {
            proj.y = C.TABLE_Y;
            proj.velY = 0;
        }

        // Wall bounces
        if (proj.z < -C.WALL_Z) {
            proj.z = -C.WALL_Z;
            proj.velZ = -proj.velZ;
            ev(sim, { type: 'wallBounce', x: proj.x, z: proj.z });
        } else if (proj.z > C.WALL_Z) {
            proj.z = C.WALL_Z;
            proj.velZ = -proj.velZ;
            ev(sim, { type: 'wallBounce', x: proj.x, z: proj.z });
        }

        // Approach warning (parry audio cue)
        const movingToward = proj.velX < 0 ? 'left' : 'right';
        const nearThreshold = proj.velX < 0 ? proj.x < -4 : proj.x > 4;
        if (nearThreshold && !proj.approachPlayed) {
            proj.approachPlayed = true;
            ev(sim, { type: 'approach', side: movingToward, x: proj.x });
        } else if (!nearThreshold) {
            proj.approachPlayed = false;
        }

        // Paddle collisions
        const defender = proj.velX < 0 ? sim.wizards.left : sim.wizards.right;
        if (checkPaddleHit(sim, proj, defender)) {
            resolvePaddleHit(sim, proj, defender, toDestroy);
            if (sim.phase !== 'playing') break;
            continue;
        }

        // Gate collisions
        if (proj.x < -C.GOAL_X) {
            resolveGateHit(sim, proj, 'left', toDestroy);
            if (sim.phase !== 'playing') break;
        } else if (proj.x > C.GOAL_X) {
            resolveGateHit(sim, proj, 'right', toDestroy);
            if (sim.phase !== 'playing') break;
        }
    }

    for (const proj of toDestroy) {
        if (sim.projectiles.includes(proj)) destroyProjectile(sim, proj, 'hit');
    }
}

// Drain the event queue (consumers call once per rendered frame).
export function drainEvents(sim) {
    const out = sim.events;
    sim.events = [];
    return out;
}
