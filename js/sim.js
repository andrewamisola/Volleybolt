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

    // Bridge to the classic inline script (which calls window.VolleyboltSim.*).
    window.VolleyboltSim = window.VolleyboltSim || {};
    window.VolleyboltSim.updateNetworkProjectiles = updateNetworkProjectiles;
})();
