// ============================================================
// Volleybolt — deterministic PvP sim (Babylon-free ES module)
// ============================================================
//
// The first function lifted out of the inline script in index.html. It runs the
// authoritative, rollback-deterministic projectile physics and touches NOTHING
// from Babylon, the DOM, audio, RNG, or wall-clock time. Everything external is
// either pure sim STATE (passed in via `ctx`, mutated in place by reference) or
// an injected effect callback (`ctx.deps.*`, defaulting in index.html to the
// inline implementations — the SIM_DEPS object).
//
// Contract — ctx = {
//   projectiles,      // Array<proj>, mutated in place (proj.x/y/z, velX/Y/Z, ...)
//   combatants,       // { left, right } with .paddleX/.paddleZ/.mana/...
//   abilities,        // ability data (read-only here: abilities.frostbolt.freezeDuration)
//   isResimulating,   // boolean snapshot for this call (gates presentation effects)
//   deps,             // SIM_DEPS — all external effects (sounds, damage, spawn, mirror, ...)
// }
//
// Determinism law (see docs/SHARED_CORE.md): same (state, inputs) -> same state.
// No Math.random / Date.now / performance.now here. Verify any change against the
// dbg.determinism golden-hash oracle in index.html (seed 12345 -> 14e88256).
//
// This module is loaded with <script type="module"> and attaches itself to
// window.VolleyboltSim so the classic inline script can call into it. The inline
// script no longer defines these functions, so there is no shadowing.

(function () {
    'use strict';

    function updateNetworkProjectiles(dt, ctx) {
        const { projectiles, combatants, abilities, isResimulating, deps: D } = ctx;
        const toDestroy = [];
        const tableY = 0.6;
        const gravity = -30;
        // Use effective depth based on game mode (half of full depth)
        const effectiveFullDepth = D.getEffectiveTableDepth();
        const tableDepth = effectiveFullDepth / 2;
        const goalX = 14;  // tableWidth/2 + 1 = 13 + 1

        for (const proj of projectiles) {
            // Clean up zombie projectiles (no mesh or disposed mesh)
            if (D.isProjectileMeshDead(proj)) {
                toDestroy.push(proj);
                continue;
            }

            // Check for projectiles marked for destruction
            if (proj.shouldDestroy) {
                toDestroy.push(proj);
                continue;
            }

            // Clean up stuck projectiles (near-zero velocity)
            const speed = Math.sqrt(proj.velX * proj.velX + proj.velZ * proj.velZ);
            if (speed < 1) {
                toDestroy.push(proj);
                continue;
            }

            // Clean up projectiles with orphaned/disposed emitter
            if (D.isProjectileEmitterDead(proj)) {
                toDestroy.push(proj);
                continue;
            }

            // Move projectile (pure sim position; mesh is mirrored at the end of the loop)
            proj.x += proj.velX * dt;
            proj.z += proj.velZ * dt;

            // Gravity for lobbed projectiles
            if (proj.velY !== undefined && proj.velY !== 0) {
                proj.velY += gravity * dt;
                proj.y += proj.velY * dt;

                // Projectiles bounce on table
                if (proj.y < tableY + 0.3) {
                    proj.y = tableY + 0.3;
                    proj.bounceCount = (proj.bounceCount || 0) + 1;
                    if (proj.bounceCount >= 2) {
                        proj.velY = 0;
                    } else {
                        proj.velY = -proj.velY * 0.6;
                    }
                }
            }

            // Wall collisions
            const halfDepth = tableDepth / 2 - 0.5;
            if (proj.z < -halfDepth) {
                proj.z = -halfDepth;
                proj.velZ = -proj.velZ;
                if (!isResimulating) D.playSound('woosh', proj.x, 0.5);
            }
            if (proj.z > halfDepth) {
                proj.z = halfDepth;
                proj.velZ = -proj.velZ;
                if (!isResimulating) D.playSound('woosh', proj.x, 0.5);
            }

            // Paddle collisions
            const projRadius = proj.hitboxRadius || 0.25;
            const paddleHalfWidth = 0.2;
            const paddleHalfDepth = 0.8;
            const maxHitHeight = 1.3;

            // Left paddle (player) collision
            if (proj.velX < 0 && proj.y < maxHitHeight && combatants.left && combatants.left.paddleX !== undefined) {
                const px = combatants.left.paddleX;   // pure paddle position (mirrored to the mesh)
                const pz = combatants.left.paddleZ;
                if (proj.x - projRadius < px + paddleHalfWidth &&
                    proj.x > px - paddleHalfWidth &&
                    proj.z > pz - paddleHalfDepth - 0.75 &&
                    proj.z < pz + paddleHalfDepth + 0.75) {

                    // Lightning Shield auto-block check (left/player)
                    if (combatants.left && combatants.left.lightningShield && combatants.left.lightningShield.charges > 0) {
                        D.useShieldCharge(combatants.left);
                        D.parryProjectile(proj, 'player');
                        if (!isResimulating) D.playSound('parry', px, 0.5);
                        continue;
                    }

                    if (proj.type === 'frostbolt') {
                        // Freeze left player
                        combatants.left.freezeTime = abilities.frostbolt.freezeDuration;
                        if (!isResimulating) {
                            D.playSound('frozen', px, 0.7);
                            D.showFrozenText(!!(combatants.left && combatants.left.isLocalPlayer));
                        }
                        toDestroy.push(proj);
                    } else {
                        // Bounce fireball with angle based on hit position
                        proj.x = px + paddleHalfWidth + projRadius;

                        // Hit offset: -1 (bottom edge) to +1 (top edge)
                        const hitOffset = (proj.z - pz) / paddleHalfDepth;

                        // Pong-style angling: edge hits = sharp angles, center hits = straight
                        // Use the current speed to maintain momentum but redirect it (min speed 10)
                        const currentSpeed = Math.max(Math.sqrt(proj.velX * proj.velX + proj.velZ * proj.velZ), 10);
                        const maxAngle = 0.7;  // ~45 degrees max deflection at edges
                        const angleStrength = hitOffset * maxAngle;

                        // Redirect velocity: more angle = less forward speed, more sideways
                        proj.velX = currentSpeed * Math.cos(angleStrength) * (proj.velX > 0 ? -1 : 1);
                        proj.velZ = currentSpeed * Math.sin(angleStrength) * Math.sign(hitOffset || 1);

                        proj.owner = 'player';
                        proj.volleyCount++;
                        D.updateFireballScale(proj);  // Scale up with damage
                        // Only give block mana if not parried (parry already gives mana)
                        if (combatants.left && !proj.isParried) combatants.left.mana = Math.min(D.getMaxMana('left'), combatants.left.mana + 0.5);
                        if (!isResimulating) D.playSound('block', px, 0.6);
                    }
                }
            }

            // Right paddle (AI/guest) collision
            if (proj.velX > 0 && proj.y < maxHitHeight && combatants.right && combatants.right.paddleX !== undefined) {
                const px = combatants.right.paddleX;   // pure paddle position (mirrored to the mesh)
                const pz = combatants.right.paddleZ;
                if (proj.x + projRadius > px - paddleHalfWidth &&
                    proj.x < px + paddleHalfWidth &&
                    proj.z > pz - paddleHalfDepth - 0.75 &&
                    proj.z < pz + paddleHalfDepth + 0.75) {

                    // Lightning Shield auto-block check (right/AI)
                    if (combatants.right && combatants.right.lightningShield && combatants.right.lightningShield.charges > 0) {
                        D.useShieldCharge(combatants.right);
                        D.parryProjectile(proj, 'ai');
                        if (!isResimulating) D.playSound('parry', px, 0.5);
                        continue;
                    }

                    if (proj.type === 'frostbolt') {
                        // Freeze right player
                        combatants.right.freezeTime = abilities.frostbolt.freezeDuration;
                        if (!isResimulating) {
                            D.playSound('frozen', px, 0.7);
                            D.showFrozenText(!!(combatants.right && combatants.right.isLocalPlayer));
                        }
                        toDestroy.push(proj);
                    } else {
                        // Bounce fireball with angle based on hit position
                        proj.x = px - paddleHalfWidth - projRadius;

                        // Hit offset: -1 (bottom edge) to +1 (top edge)
                        const hitOffset = (proj.z - pz) / paddleHalfDepth;

                        // Pong-style angling: edge hits = sharp angles, center hits = straight
                        // Use the current speed to maintain momentum but redirect it (min speed 10)
                        const currentSpeed = Math.max(Math.sqrt(proj.velX * proj.velX + proj.velZ * proj.velZ), 10);
                        const maxAngle = 0.7;  // ~45 degrees max deflection at edges
                        const angleStrength = hitOffset * maxAngle;

                        // Redirect velocity: more angle = less forward speed, more sideways
                        proj.velX = currentSpeed * Math.cos(angleStrength) * (proj.velX > 0 ? -1 : 1);
                        proj.velZ = currentSpeed * Math.sin(angleStrength) * Math.sign(hitOffset || 1);

                        proj.owner = 'ai';
                        proj.volleyCount++;
                        D.updateFireballScale(proj);  // Scale up with damage
                        // Only give block mana if not parried (parry already gives mana)
                        if (combatants.right && !proj.isParried) combatants.right.mana = Math.min(D.getMaxMana('right'), combatants.right.mana + 0.5);
                        if (!isResimulating) D.playSound('block', px, 0.6);
                    }
                }
            }

            // Gate collisions
            if (proj.x < -goalX) {
                const isPlayerTower = proj.owner === 'ai';
                // Hit left gate (player's tower)
                if (proj.type !== 'frostbolt') {
                    const damage = Math.min(2 + proj.volleyCount, 6);  // Fireball damage
                    D.dealDamageToTower(isPlayerTower, damage, proj.z);
                }
                toDestroy.push(proj);
            } else if (proj.x > goalX) {
                const isPlayerTower = proj.owner === 'ai';
                // Hit right gate (AI/guest tower)
                if (proj.type !== 'frostbolt') {
                    const damage = Math.min(2 + proj.volleyCount, 6);  // Fireball damage
                    D.dealDamageToTower(isPlayerTower, damage, proj.z);
                }
                toDestroy.push(proj);
            }

            // Render mirror: copy the authoritative sim position onto the mesh (via dep,
            // so the physics above is pure number math with no direct Babylon touch).
            D.mirrorProjectileToMesh(proj);
        }

        // Destroy projectiles
        for (const proj of toDestroy) {
            D.destroyProjectile(proj);
        }
    }

    // Apply movement for network play. Pure-number paddle motion (combatant.paddleZ);
    // the mesh is mirrored via ctx.deps.mirrorPaddleToMesh.
    function applyNetworkMovement(combatant, moveDir, dt, ctx) {
        const D = ctx.deps;
        if (!combatant || combatant.freezeTime > 0) return;
        // Defensive: ensure the authoritative paddle position exists (never NaN).
        // Always set at match init / restore / round-reset, so this never triggers.
        if (combatant.paddleZ === undefined) combatant.paddleZ = 0;
        if (combatant.paddleX === undefined) combatant.paddleX = 0;
        if (moveDir === 0) return;

        const STEP_SIZE = 0.3;
        const speed = 20;  // paddleSpeed

        if (!combatant.moveAccum) combatant.moveAccum = 0;
        combatant.moveAccum += moveDir * speed * dt;

        if (Math.abs(combatant.moveAccum) >= STEP_SIZE) {
            const steps = Math.trunc(combatant.moveAccum / STEP_SIZE);
            // Pure-number movement; the mesh is mirrored from it below.
            combatant.paddleZ += steps * STEP_SIZE;
            combatant.moveAccum -= steps * STEP_SIZE;

            // Clamp to boundaries
            const boundary = 2.7;
            combatant.paddleZ = Math.max(-boundary, Math.min(boundary, combatant.paddleZ));

            // Render mirror (via dep, so the movement math is Babylon-free)
            D.mirrorPaddleToMesh(combatant);
        }
    }

    // Try to start a cast in network mode. ctx = { abilities, isResimulating, deps }.
    function tryNetworkCast(combatant, abilityId, ctx) {
        const { abilities, isResimulating, deps: D } = ctx;
        if (!combatant || combatant.freezeTime > 0) return;
        if (combatant.casting) return;  // Already casting

        const ability = abilities[abilityId];
        if (!ability) return;

        if (combatant.mana < ability.manaCost) return;
        if (combatant.cooldowns[abilityId] > 0) return;

        if (abilityId === 'frostbolt') {
            // Instant cast
            combatant.mana -= ability.manaCost;
            combatant.cooldowns.frostbolt = ability.cooldown;
            const side = combatant.side === 'left' ? 'player' : 'ai';
            // Pure paddle position (mirrored to the mesh) for the spawn point.
            const velX = combatant.side === 'left' ? ability.baseSpeed : -ability.baseSpeed;
            const startX = combatant.side === 'left' ? combatant.paddleX + 1 : combatant.paddleX - 1;

            if (!isResimulating) {
                D.playSound('frostboltCast', startX, 0.7);
            }

            const proj = D.spawnFrostbolt(side, startX, combatant.paddleZ, velX, 0);
            if (proj) {
                proj.id = D.allocProjectileId();
            }
        } else if (abilityId === 'fireball') {
            // Start casting
            combatant.casting = 'fireball';
            combatant.castProgress = 0;
            combatant.castTime = ability.castTime;
            combatant.pendingManaCost = ability.manaCost;

            if (!isResimulating) {
                D.castingStart();
            }
        }
    }

    // --- PvP parry (deterministic timing + hit detection) ---
    // ctx adds: pvpParryState, projectiles, consts {parryWindow, parryFailCooldown,
    // parrySuccessCooldown, parryHitboxExtend}. Bubble FX go through ctx.deps.

    function updatePvPParryTimers(dt, ctx) {
        const { pvpParryState, combatants, consts, deps: D } = ctx;
        for (const side of ['left', 'right']) {
            const state = pvpParryState[side];
            if (state.active) {
                state.timer -= dt;
                if (state.timer <= 0) {
                    state.active = false;
                    state.timer = 0;
                    state.cooldown = consts.parryFailCooldown;
                    state.cooldownMax = consts.parryFailCooldown;
                    state.canParry = false;

                    D.dissolveActiveParryBubble(combatants[side]);
                }
            }

            if (!state.canParry) {
                state.cooldown -= dt;
                if (state.cooldown <= 0) {
                    state.cooldown = 0;
                    state.cooldownMax = 0;
                    state.canParry = true;
                }
            }
        }
    }

    function tryActivatePvPParry(side, ctx) {
        const { pvpParryState, combatants, isResimulating, consts, deps: D } = ctx;
        const state = pvpParryState[side];
        const combatant = combatants[side];
        if (!combatant || combatant.freezeTime > 0) return;
        if (!state.canParry || state.active) return;

        state.active = true;
        state.timer = consts.parryWindow;
        state.canParry = false;
        state.cooldown = consts.parryFailCooldown;
        state.cooldownMax = consts.parryFailCooldown;

        if (!isResimulating && combatant.isLocalPlayer) {
            D.onParryActivated(combatant, side);
        }
    }

    function checkPvPParryHitsForSide(side, inputState, ctx) {
        const { pvpParryState, combatants, projectiles, consts, deps: D } = ctx;
        const state = pvpParryState[side];
        if (!state.active) return;

        const combatant = combatants[side];
        if (!combatant || combatant.paddleX === undefined) return;
        const px = combatant.paddleX;   // pure paddle position (mirrored to the mesh)
        const pz = combatant.paddleZ;

        const incomingVelCheck = side === 'left' ? (proj) => proj.velX < 0 : (proj) => proj.velX > 0;
        const ownerKey = side === 'left' ? 'player' : 'ai';

        const paddleHalfDepth = 2.0;
        let bestProj = null;
        let bestDist = Infinity;

        for (const proj of projectiles) {
            if (!incomingVelCheck(proj)) continue;
            if (proj.owner === ownerKey && !proj.isParried) continue;

            const distFromPaddle = proj.x - px;
            if (distFromPaddle > consts.parryHitboxExtend || distFromPaddle < -0.5) continue;

            if (proj.z < pz - paddleHalfDepth || proj.z > pz + paddleHalfDepth) continue;

            if (distFromPaddle < bestDist) {
                bestDist = distFromPaddle;
                bestProj = proj;
            }
        }

        if (bestProj) {
            const parryer = side === 'left' ? 'player' : 'ai';
            const aimDir = inputState ? inputState.moveDir : 0;
            D.parryProjectile(bestProj, parryer, aimDir);

            state.active = false;
            state.timer = 0;
            state.cooldown = consts.parrySuccessCooldown;
            state.cooldownMax = consts.parrySuccessCooldown;
            state.canParry = false;

            D.dissolveActiveParryBubble(combatant);
        }
    }

    // --- Orchestrator: one deterministic frame ---
    // ctx = { projectiles, combatants, abilities, pvpParryState, isResimulating,
    //         consts {parryWindow, parryFailCooldown, parrySuccessCooldown,
    //                 parryHitboxExtend, manaRegenTime}, deps }.
    // Calls the lifted helpers directly (same module scope) and ctx.deps.* for the
    // render/flow callbacks it does not own (syncLocalParryUI, completeCasting,
    // updateChainLightningChannel, getMaxMana, endRound).
    function simulateNetworkFrame(leftInput, rightInput, dt, ctx) {
        const { combatants, consts, deps: D } = ctx;

        // Update freeze timers
        if (combatants.left && combatants.left.freezeTime > 0) {
            combatants.left.freezeTime -= dt;
            if (combatants.left.freezeTime < 0) combatants.left.freezeTime = 0;
        }
        if (combatants.right && combatants.right.freezeTime > 0) {
            combatants.right.freezeTime -= dt;
            if (combatants.right.freezeTime < 0) combatants.right.freezeTime = 0;
        }

        // Update parry system (PvP)
        updatePvPParryTimers(dt, ctx);

        // Process parry inputs
        if (leftInput.parry) tryActivatePvPParry('left', ctx);
        if (rightInput.parry) tryActivatePvPParry('right', ctx);

        // Check parry hits for both sides
        checkPvPParryHitsForSide('left', leftInput, ctx);
        checkPvPParryHitsForSide('right', rightInput, ctx);
        D.syncLocalParryUI();

        // Update cooldowns
        for (const c of [combatants.left, combatants.right]) {
            if (!c) continue;
            if (c.cooldowns.fireball > 0) c.cooldowns.fireball -= dt;
            if (c.cooldowns.frostbolt > 0) c.cooldowns.frostbolt -= dt;
            if (c.cooldowns.gravity > 0) c.cooldowns.gravity -= dt;
            if (c.cooldowns.chain_lightning > 0) c.cooldowns.chain_lightning -= dt;

            // Update Chain Lightning channeling
            if (c.casting === 'chain_lightning') {
                D.updateChainLightningChannel(c, dt);
            }
        }

        // Mana regeneration (stops while frozen) - discrete 0.5 every 2 seconds
        for (const c of [combatants.left, combatants.right]) {
            if (!c) continue;
            if (c.freezeTime > 0) continue;
            const cMaxMana = D.getMaxMana(c.side);
            if (c.mana < cMaxMana) {
                c.manaRegen += dt;
                if (c.manaRegen >= consts.manaRegenTime) {
                    c.manaRegen = 0;
                    c.mana = Math.min(cMaxMana, c.mana + 0.5);
                }
            }
        }

        // Process casting
        for (const c of [combatants.left, combatants.right]) {
            if (!c || !c.casting) continue;
            c.castProgress += dt;
            if (c.castProgress >= c.castTime) {
                // Complete the cast
                const side = c.side === 'left' ? 'player' : 'ai';
                D.completeCasting(side);
            }
        }

        // Apply movement inputs
        if (combatants.left) combatants.left.lastMoveDir = leftInput.moveDir;
        if (combatants.right) combatants.right.lastMoveDir = rightInput.moveDir;
        applyNetworkMovement(combatants.left, leftInput.moveDir, dt, ctx);
        applyNetworkMovement(combatants.right, rightInput.moveDir, dt, ctx);

        // Process ability inputs
        if (leftInput.fireball && combatants.left) tryNetworkCast(combatants.left, 'fireball', ctx);
        if (leftInput.frostbolt && combatants.left) tryNetworkCast(combatants.left, 'frostbolt', ctx);
        if (rightInput.fireball && combatants.right) tryNetworkCast(combatants.right, 'fireball', ctx);
        if (rightInput.frostbolt && combatants.right) tryNetworkCast(combatants.right, 'frostbolt', ctx);

        // Update projectiles
        updateNetworkProjectiles(dt, ctx);

        // Check win conditions
        if (combatants.left && combatants.left.towerHealth <= 0) {
            D.endRound('right');
        } else if (combatants.right && combatants.right.towerHealth <= 0) {
            D.endRound('left');
        }
    }

    // Bridge to the classic inline script (which calls window.VolleyboltSim.*).
    window.VolleyboltSim = window.VolleyboltSim || {};
    window.VolleyboltSim.simulateNetworkFrame = simulateNetworkFrame;
    window.VolleyboltSim.updateNetworkProjectiles = updateNetworkProjectiles;
    window.VolleyboltSim.applyNetworkMovement = applyNetworkMovement;
    window.VolleyboltSim.tryNetworkCast = tryNetworkCast;
    window.VolleyboltSim.updatePvPParryTimers = updatePvPParryTimers;
    window.VolleyboltSim.tryActivatePvPParry = tryActivatePvPParry;
    window.VolleyboltSim.checkPvPParryHitsForSide = checkPvPParryHitsForSide;
})();
