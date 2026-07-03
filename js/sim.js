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
// dbg.determinism golden-hash oracle in index.html (seed 12345 -> 954ea557, seed
// 99999 -> 56c1c1ac, both stable; run from a FRESH SINGLE-PLAYER match — a mid-PvP
// run reads pvp-mode deps and folds differently, that is oracle-environment
// sensitivity, not a sim change).
// (954ea557 unchanged, 2026-07-03: index.html's updateFireballScale (called from this
//  file's onPaddleHit and the shared parryProjectile path) now also grows proj.hitboxRadius
//  proportionally with the ball's visual scale — hitboxRadius was pinned at spawn (0.25)
//  and never grew with volleyCount, so a late-volley fireball (up to scale 1.35) looked
//  ~20% bigger than it actually collided as, most noticeable on angled hits near the
//  shield's edge ("passes right through" reports). Pure function of volleyCount, same on
//  both peers. Verified NON-MOVING on both pinned seeds (12345 and 99999) via an A/B
//  toggle of the one changed line — the oracle's scripted parries/casts never hit a
//  fireball at a volleyCount where the grown hitbox would flip a frame's outcome.)
// (8f6e6da1 -> 954ea557: STALE-PIN CORRECTION, re-measured 2026-07-02. The 8f6e6da1 value
//  was measured mid-way through the b7e492b squashed playtest commit (correct at that
//  moment, right after the arc-collision change below) but the SAME commit then landed
//  sim-affecting balance changes — fireball baseSpeed 12->15 / maxSpeed 20->26, frostbolt
//  hitboxRadius 0.25->0.4, parry return 1.5x-of-current-speed — all exercised by the
//  oracle's scripted casts/parries, and the pin was never re-measured. 954ea557 verified
//  identical on unmodified b7e492b (via git stash) and on the 2026-07-02 netcode-fix tree,
//  three runs. No sim code changed in this correction; the pin just caught up to b7e492b.)
// (2dd677de -> 8f6e6da1: projectile↔player collision moved from the axis-aligned paddle BOX to
//  the curved block ARC — hitsBlockArc, a FILLED convex shield, shape from ctx.consts.arc.
//  Trig-free per frame; Math.sqrt is IEEE-deterministic. NOTE: the oracle's 180-frame script
//  does NOT exercise a fireball PADDLE-BOUNCE, so COLL_HALF tuning and the onPaddleHit
//  bounce-repositioning (index.html: reflect the ball off the VISIBLE shield front face, not the
//  paddle) do NOT move this golden — they are verified by direct projectile injection instead.
//  Self-stable on seeds 12345 & 99999.)
// (60bf20f3 -> e9717f89: balance — fireball mana 1->0.5 & cooldown 4->3, frostbolt mana 2->1.)
// (18bf5599 -> 2dd677de: cast no longer roots the caster; moving while casting CANCELS the cast
//  instead (cancelCastOnMove). decideAI holds still while casting so the AI never self-cancels.)
// Re-baseline history: 14e88256 (pre Phase-0) -> b1df6797 (Phase-0 fireball-id +
// court-depth) -> ad7c0e42 (Phase 2.2-B proj-vs-proj + juice in hash) ->
// 3770e2c7 (Phase 2.2-C juice lifecycle) -> 3b37922a (Phase 2.3-A SP paddle-return:
// momentum + 1.25 divisor + 2.0 hitbox + prevPaddleZ in hash) -> 60bf20f3 (Phase 2.3
// cast-rooting restored + oracle setup now pins paddleX/prevPaddleZ) -> e9717f89
// (balance) -> 2dd677de (cancel-cast-on-move) -> 8f6e6da1 (arc collision; pinned stale,
// see correction note above) -> 954ea557 (b7e492b balance changes, pin caught up).
// NOTE: 3072141a was a contaminated mis-measure of the 2.3-A golden (a test had left
// combatants.paddleX mutated when it was pinned); the real 2.3-A value was 3b37922a.
// The oracle now pins paddleX so this can't recur.
//
// This module is loaded with <script type="module"> and attaches itself to
// window.VolleyboltSim so the classic inline script can call into it. The inline
// script no longer defines these functions, so there is no shadowing.

(function () {
    'use strict';

    // Pure helper — no mesh, no RNG, no wall-clock.
    // juiceConsts = ctx.consts.juice = { MAX, DURATION, CHARGE }
    function simAddJuice(combatant, amount, juiceConsts) {
        if (!combatant || combatant.juiceActive) return;
        combatant.juice = Math.min(juiceConsts.MAX, (combatant.juice || 0) + amount);
    }

    // Pure: same guard + effect as SP activateJuice (index.html ~1720), minus the FX
    // (those go through ctx.deps.onJuiceActivate, gated by !isResimulating).
    // Spend a full bar -> enter the burst. The bar stays full and DRAINS over the burst
    // (it becomes the duration meter). Resets ALL cooldowns once on activation. Returns
    // true if it fired.
    function simActivateJuice(combatant, ctx) {
        const J = ctx.consts.juice;
        if (!combatant) return false;
        if (combatant.juiceActive) return false;
        if ((combatant.juice || 0) < J.MAX) return false;
        combatant.juice      = J.MAX;       // stays full; drains as duration ticks
        combatant.juiceActive = true;
        combatant.juiceTimer  = J.DURATION;
        // Reset all cooldowns ONCE on activation (matches SP).
        if (combatant.cooldowns) { for (const k in combatant.cooldowns) combatant.cooldowns[k] = 0; }
        // Grant FULL mana on activation (Director call 2026-06-29).
        combatant.mana = ctx.deps.getMaxMana(combatant.side);
        if (!ctx.isResimulating) ctx.deps.onJuiceActivate(combatant);
        return true;
    }

    // Pure, deterministic block-ARC hit test (replaces the old axis-aligned paddle box).
    // The shield is a FILLED convex region, not a thin ring: a projectile of radius projRadius
    // is blocked when it is within the shield radius (dist < R + COLL_HALF + projRadius) AND
    // inside the angular sweep (the front face). A thin band let fast/off-centre balls thread
    // straight through the gaps; the filled region catches everything approaching the convex
    // face — which is what a shield should do. dir = +1 (left/player, bows toward +X) or -1
    // (right/AI). arc = ctx.consts.arc (shared BLOCK_ARC). Uses only +-*/, comparisons, and
    // Math.sqrt (IEEE-deterministic) — no per-frame trig — so rollback stays safe.
    function hitsBlockArc(projX, projZ, px, pz, dir, projRadius, arc) {
        // Straight SLAB matched pixel-for-pixel to the VISIBLE ground line (index.html makeBarrier):
        // a band centred in X at paddleX + dir·(FWD+R), thickness BAND_W (X), length BAND_LEN (Z).
        // No curve/sector — the ball blocks exactly where the line is drawn. Uses only +-*/ and
        // comparisons (IEEE-deterministic) → rollback-safe.
        const cx = px + dir * (arc.FWD + arc.R);          // band centre X (== visual shieldX)
        // Isometric parallax: the ball flies ~0.7m up but the line is painted on the floor. The gameplay
        // camera (alpha -90°, beta 60°) sits at -Z looking toward +Z, so a raised ball appears shifted
        // toward +Z (up-screen). Add arc.ZPERSP to the ball's Z so it blocks exactly where it VISUALLY
        // crosses the drawn line — this catches the near/bottom (-Z) balls that were passing through.
        const zEff = projZ + arc.ZPERSP;
        if (Math.abs(zEff - pz) > arc.BAND_LEN * 0.5 + projRadius) return false;   // outside the line's length (Z) — ball radius counts
        const dxf = (projX - cx) * dir;                   // +toward field (front) / -behind (player side)
        // Catch the ball from its edge touching the field-facing face down to COLL_HALF behind the
        // band (tunnel-safety so a fast ball can't skip through in one step).
        return dxf <= (arc.BAND_W * 0.5 + projRadius)
            && dxf >= -(arc.BAND_W * 0.5 + arc.COLL_HALF + projRadius);
    }

    // Deterministic projectile-vs-projectile resolution. Pure number math on
    // proj.x / proj.z (NEVER proj.mesh). Mutates `toDestroy` (owned by the caller,
    // updateNetworkProjectiles) and combatant juice/mana. FX go through ctx.deps.*
    // gated by !isResimulating.
    function resolveNetworkProjVsProj(ctx, toDestroy) {
        const { projectiles, combatants, isResimulating, deps: D, consts } = ctx;
        const juiceConsts = consts.juice;

        // --- Pass 1: Frostbolt cancel ---
        for (const proj of projectiles) {
            if (proj.type !== 'frostbolt') continue;
            if (toDestroy.includes(proj)) continue;
            for (const other of projectiles) {
                if (other === proj) continue;
                if (other.type === 'frostbolt') continue;        // frostbolts pass through each other
                if (toDestroy.includes(other)) continue;
                // Head-on: opposite X velocities
                if ((proj.velX > 0 && other.velX > 0) || (proj.velX < 0 && other.velX < 0)) continue;
                // Moving toward each other (not already past)
                const dx = other.x - proj.x;
                if (proj.velX > 0 && dx < 0) continue;
                if (proj.velX < 0 && dx > 0) continue;
                // Distance check
                const dz = other.z - proj.z;
                const dist = Math.sqrt(dx * dx + dz * dz);
                const collDist = (proj.hitboxRadius || 0.3) + (other.hitboxRadius || 0.3);
                if (dist < collDist) {
                    toDestroy.push(proj);
                    toDestroy.push(other);
                    if (!isResimulating) D.onFrostboltCancel((proj.x + other.x) * 0.5, (proj.z + other.z) * 0.5);
                    break;
                }
            }
        }

        // --- Pass 2: Fireball overpower / mutual cancel ---
        for (const proj of projectiles) {
            if (proj.type === 'frostbolt') continue;
            if (toDestroy.includes(proj)) continue;
            const grace = proj.collisionGraceTime || 0;
            if (grace > 0) continue;
            for (const other of projectiles) {
                if (other === proj) continue;
                if (other.type === 'frostbolt') continue;
                if (toDestroy.includes(other)) continue;
                if ((other.collisionGraceTime || 0) > 0) continue;
                // Head-on: opposite X velocities
                if ((proj.velX > 0 && other.velX > 0) || (proj.velX < 0 && other.velX < 0)) continue;
                // Moving toward each other
                const dx = other.x - proj.x;
                if (proj.velX > 0 && dx < 0) continue;
                if (proj.velX < 0 && dx > 0) continue;
                // Distance check
                const dz = other.z - proj.z;
                const dist = Math.sqrt(dx * dx + dz * dz);
                const collDist = (proj.hitboxRadius || 0.3) + (other.hitboxRadius || 0.3);
                if (dist < collDist) {
                    const midX = (proj.x + other.x) * 0.5;
                    const midZ = (proj.z + other.z) * 0.5;
                    const projDmg  = proj.damage  !== undefined ? proj.damage  : Math.min(2 + (proj.volleyCount  || 0), 6);
                    const otherDmg = other.damage !== undefined ? other.damage : Math.min(2 + (other.volleyCount || 0), 6);

                    if (projDmg > otherDmg) {
                        toDestroy.push(other);
                        proj.volleyCount = Math.min((proj.volleyCount || 0) + 1, 4);
                        const ownerC = proj.owner === 'player' ? combatants.left : combatants.right;
                        simAddJuice(ownerC, juiceConsts.CHARGE.minor, juiceConsts);
                        if (!isResimulating) D.onOverpower(midX, midZ, proj.velX, proj.velZ);
                    } else if (otherDmg > projDmg) {
                        toDestroy.push(proj);
                        other.volleyCount = Math.min((other.volleyCount || 0) + 1, 4);
                        const ownerC = other.owner === 'player' ? combatants.left : combatants.right;
                        simAddJuice(ownerC, juiceConsts.CHARGE.minor, juiceConsts);
                        if (!isResimulating) D.onOverpower(midX, midZ, other.velX, other.velZ);
                    } else {
                        // Mutual cancel
                        toDestroy.push(proj);
                        toDestroy.push(other);
                        // Mana award: +0.5 to each combatant
                        if (combatants.left)  combatants.left.mana  = Math.min(D.getMaxMana('left'),  (combatants.left.mana  || 0) + 0.5);
                        if (combatants.right) combatants.right.mana = Math.min(D.getMaxMana('right'), (combatants.right.mana || 0) + 0.5);
                        simAddJuice(combatants.left,  juiceConsts.CHARGE.minor, juiceConsts);
                        simAddJuice(combatants.right, juiceConsts.CHARGE.minor, juiceConsts);
                        if (!isResimulating) D.onProjCancel(midX, midZ);
                    }
                    break;
                }
            }
        }
    }

    function updateNetworkProjectiles(dt, ctx) {
        const { projectiles, combatants, abilities, isResimulating, deps: D } = ctx;
        // Expose the frame dt on ctx so behavior.onPaddleHit can compute the paddle-momentum
        // term ((paddleZ - prevPaddleZ) / dt). onPaddleHit's signature is (proj, side, ctx).
        ctx.dt = dt;
        const toDestroy = [];
        const tableY = 0.6;
        const gravity = -30;
        // Court depth (Z). Matches single-player: walls at depth/2 - 0.5.
        // (Was previously double-halved here, making the MP court ~half size — a bug.)
        const effectiveFullDepth = D.getEffectiveTableDepth();
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

            // Wall collisions (matches single-player: depth/2 - 0.5)
            const halfDepth = effectiveFullDepth / 2 - 0.5;
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

            // Paddle collisions — now against the curved block ARC (was an axis-aligned box).
            // The arc shape comes from ctx.consts.arc (the shared BLOCK_ARC). The height gate
            // (proj.y < maxHitHeight) is kept "exactly how it was" so ground-level projectiles
            // are still caught even though the VISUAL band floats higher.
            const projRadius = proj.hitboxRadius || 0.25;
            const arc = ctx.consts.arc;
            const maxHitHeight = 1.3;

            // Left paddle (player) collision — arc bows toward +X (dir = +1)
            if (proj.velX < 0 && proj.y < maxHitHeight && combatants.left && combatants.left.paddleX !== undefined) {
                const px = combatants.left.paddleX;   // pure paddle position (mirrored to the mesh)
                const pz = combatants.left.paddleZ;
                if (hitsBlockArc(proj.x, proj.z, px, pz, 1, projRadius, arc)) {

                    // Lightning Shield auto-block check (left/player)
                    if (combatants.left && combatants.left.lightningShield && combatants.left.lightningShield.charges > 0) {
                        D.useShieldCharge(combatants.left);
                        D.parryProjectile(proj, 'player');
                        if (!isResimulating) D.playSound('parry', px, 0.5);
                        continue;
                    }

                    // Juice burst: the juiced combatant auto–perfect-parries every incoming
                    // projectile, ignoring the parry cooldown/timing window (matches SP
                    // updateGameLogic ~12632). parryProjectile REFLECTS (does not destroy) and
                    // plays its own parry sound, so there is no toDestroy/extra-sound here.
                    // aimDir is passed 0 (neutral) for determinism — SP reads keys[]/AI targeting
                    // here, which is not sim-safe.
                    if (combatants.left && combatants.left.juiceActive) {
                        D.parryProjectile(proj, 'player', 0);
                        continue;
                    }

                    const hitAbility = ctx.deps.getAbilityDef(proj.type);
                    if (hitAbility && hitAbility.behavior.onPaddleHit) {
                        if (hitAbility.behavior.onPaddleHit(proj, 'left', ctx)) { toDestroy.push(proj); }
                    }
                }
            }

            // Right paddle (AI/guest) collision — arc bows toward -X (dir = -1)
            if (proj.velX > 0 && proj.y < maxHitHeight && combatants.right && combatants.right.paddleX !== undefined) {
                const px = combatants.right.paddleX;   // pure paddle position (mirrored to the mesh)
                const pz = combatants.right.paddleZ;
                if (hitsBlockArc(proj.x, proj.z, px, pz, -1, projRadius, arc)) {

                    // Lightning Shield auto-block check (right/AI)
                    if (combatants.right && combatants.right.lightningShield && combatants.right.lightningShield.charges > 0) {
                        D.useShieldCharge(combatants.right);
                        D.parryProjectile(proj, 'ai');
                        if (!isResimulating) D.playSound('parry', px, 0.5);
                        continue;
                    }

                    // Juice burst: symmetric auto–perfect-parry while juiceActive (matches SP
                    // updateGameLogic ~12712). Reflect, don't destroy; neutral aimDir for determinism.
                    if (combatants.right && combatants.right.juiceActive) {
                        D.parryProjectile(proj, 'ai', 0);
                        continue;
                    }

                    const hitAbility = ctx.deps.getAbilityDef(proj.type);
                    if (hitAbility && hitAbility.behavior.onPaddleHit) {
                        if (hitAbility.behavior.onPaddleHit(proj, 'right', ctx)) { toDestroy.push(proj); }
                    }
                }
            }

            // Gate collisions
            if (proj.x < -goalX) {
                const hitAbility = ctx.deps.getAbilityDef(proj.type);
                const res = hitAbility && hitAbility.behavior.onGateHit ? hitAbility.behavior.onGateHit(proj, 'left', ctx) : { damage: Math.min(2 + proj.volleyCount, 6) };
                if (res && res.damage) D.dealDamageToTower(proj.owner === 'ai', res.damage, proj.z);
                toDestroy.push(proj);
            } else if (proj.x > goalX) {
                const hitAbility = ctx.deps.getAbilityDef(proj.type);
                const res = hitAbility && hitAbility.behavior.onGateHit ? hitAbility.behavior.onGateHit(proj, 'right', ctx) : { damage: Math.min(2 + proj.volleyCount, 6) };
                if (res && res.damage) D.dealDamageToTower(proj.owner === 'ai', res.damage, proj.z);
                toDestroy.push(proj);
            }

            // Render mirror: copy the authoritative sim position onto the mesh (via dep,
            // so the physics above is pure number math with no direct Babylon touch).
            D.mirrorProjectileToMesh(proj);
        }

        // Projectile-vs-projectile resolution (frostbolt cancel, fireball overpower/cancel).
        // Runs once over all projectiles after movement; mutates `toDestroy` (in scope).
        resolveNetworkProjVsProj(ctx, toDestroy);

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
        // Record the pre-movement paddle Z every (non-frozen) frame so onPaddleHit can derive
        // the lateral paddle-momentum term. When stationary (moveDir 0 or sub-step) prevPaddleZ
        // tracks paddleZ → zero momentum, matching SP feel. Deterministic: both clients run this.
        combatant.prevPaddleZ = combatant.paddleZ;
        if (moveDir === 0) return;
        // NOT rooted while casting: moving during a cast cancels it instead (see cancelCastOnMove,
        // run before this in simulateNetworkFrame), matching single-player feel.

        const STEP_SIZE = 0.3;
        const speed = 20;  // paddleSpeed

        if (!combatant.moveAccum) combatant.moveAccum = 0;
        combatant.moveAccum += moveDir * speed * dt;

        if (Math.abs(combatant.moveAccum) >= STEP_SIZE) {
            const steps = Math.trunc(combatant.moveAccum / STEP_SIZE);
            // Pure-number movement; the mesh is mirrored from it below.
            combatant.paddleZ += steps * STEP_SIZE;
            combatant.moveAccum -= steps * STEP_SIZE;

            // Clamp to boundaries — matches single-player getPaddleBoundary() = depth/2 - 1.5
            // (was hardcoded 2.7, the squished-court counterpart of the wall double-halving bug).
            const boundary = D.getEffectiveTableDepth() / 2 - 1.5;
            combatant.paddleZ = Math.max(-boundary, Math.min(boundary, combatant.paddleZ));

            // Render mirror (via dep, so the movement math is Babylon-free)
            D.mirrorPaddleToMesh(combatant);
        }
    }

    // Moving while casting cancels the cast (single-player feel — you are NOT rooted). The
    // authoritative state clear runs every frame so rollback re-simulation reproduces it; the
    // FX/UI cancel is gated to live frames via the dep. Mana is spent at cast COMPLETION, so an
    // aborted cast costs nothing (pendingManaCost is just discarded). The AI holds still while
    // casting (decideAI zeroes moveDir), so in practice only the human triggers this.
    function cancelCastOnMove(combatant, moveDir, ctx) {
        if (!combatant || !combatant.casting || moveDir === 0 || combatant.freezeTime > 0) return;
        const D = ctx.deps;
        if (!ctx.isResimulating && D.onCastCancelled) D.onCastCancelled(combatant);  // FX reads .casting
        combatant.casting = null;
        combatant.castProgress = 0;
        combatant.pendingManaCost = 0;
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

        const beh = (ctx.deps.getAbilityDef ? ctx.deps.getAbilityDef(abilityId) : null)?.behavior;
        if (beh && (beh.castType === 'instant' || beh.castType === 'channel' || beh.castType === 'targeted')) {
            beh.onCast(ctx, combatant);
            return;
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
    // updateThunderstormChannel, getMaxMana, endRound).
    function simulateNetworkFrame(leftInput, rightInput, dt, ctx) {
        const { combatants, consts, deps: D } = ctx;

        // Juice drain — runs UNCONDITIONALLY every frame, even while frozen (matches SP
        // updateJuice ~1733). The full bar becomes the duration meter: MAX -> 0 over
        // JUICE.DURATION seconds; at expiry the burst clears. FX (aura fade) go through
        // onJuiceEnd, gated by !isResimulating.
        for (const c of [combatants.left, combatants.right]) {
            if (!c || !c.juiceActive) continue;
            c.juiceTimer -= dt;
            const frac = Math.max(0, c.juiceTimer / consts.juice.DURATION);
            c.juice = consts.juice.MAX * frac;   // bar drains = time remaining
            if (c.juiceTimer <= 0) {
                c.juiceActive = false; c.juiceTimer = 0; c.juice = 0;
                if (!ctx.isResimulating) D.onJuiceEnd(c);
            }
        }

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

        // Process juice activation inputs (full bar -> burst). Input-gated, deterministic.
        if (leftInput.juice  && combatants.left)  simActivateJuice(combatants.left,  ctx);
        if (rightInput.juice && combatants.right) simActivateJuice(combatants.right, ctx);

        // Update cooldowns
        for (const c of [combatants.left, combatants.right]) {
            if (!c) continue;
            if (c.cooldowns.fireball > 0) c.cooldowns.fireball -= dt;
            if (c.cooldowns.frostbolt > 0) c.cooldowns.frostbolt -= dt;
            if (c.cooldowns.gravity > 0) c.cooldowns.gravity -= dt;
            if (c.cooldowns.thunderstorm > 0) c.cooldowns.thunderstorm -= dt;

            // Update Chain Lightning channeling
            if (c.casting === 'thunderstorm') {
                D.updateThunderstormChannel(c, dt);
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

        // Moving while casting cancels the cast (runs AFTER the cast-progress loop above, so a cast
        // that completes this very frame still fires; otherwise directional input aborts it).
        cancelCastOnMove(combatants.left, leftInput.moveDir, ctx);
        cancelCastOnMove(combatants.right, rightInput.moveDir, ctx);

        // Apply movement inputs
        if (combatants.left) combatants.left.lastMoveDir = leftInput.moveDir;
        if (combatants.right) combatants.right.lastMoveDir = rightInput.moveDir;
        applyNetworkMovement(combatants.left, leftInput.moveDir, dt, ctx);
        applyNetworkMovement(combatants.right, rightInput.moveDir, dt, ctx);

        // Process ability inputs
        if (leftInput.fireball && combatants.left) tryNetworkCast(combatants.left, 'fireball', ctx);
        if (leftInput.frostbolt && combatants.left) tryNetworkCast(combatants.left, 'frostbolt', ctx);
        if (leftInput.thunderstorm && combatants.left) tryNetworkCast(combatants.left, 'thunderstorm', ctx);
        if (rightInput.fireball && combatants.right) tryNetworkCast(combatants.right, 'fireball', ctx);
        if (rightInput.frostbolt && combatants.right) tryNetworkCast(combatants.right, 'frostbolt', ctx);
        if (rightInput.thunderstorm && combatants.right) tryNetworkCast(combatants.right, 'thunderstorm', ctx);

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
