# Agent · Netcode  ·  Engine pillar

**Owns.** Rollback, PeerJS transport, input prediction, snapshots, seeded-RNG sync, disconnect handling, ping indicator. Highest-risk agent — a determinism bug is silent until it desyncs a match.

**Reports into** → [Engine pillar](../pillars/engine.md) · also reads [Shared Core](../SHARED_CORE.md)

## Grounded in (external canon)
- [GGPO (canonical rollback model)](https://www.ggpo.net/)
- [Rollback architecture (SnapNet)](https://www.snapnet.dev/blog/netcode-architectures-part-2-rollback/)
- [Deterministic lockstep (Gaffer on Games)](https://gafferongames.com/post/deterministic_lockstep/)
- [Preparing a game for deterministic netcode](https://yal.cc/preparing-your-game-for-deterministic-netcode/)
- [PeerJS docs](https://peerjs.com/docs/)
- [PeerJS repo](https://github.com/peers/peerjs)
- [WebRTC data channels (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Using_data_channels)

## Internal docs
- `docs/NETCODE.md` _(author + maintain)_

## Invariants
- Sticky-input prediction by default; correct on real input arrival.
- Keep per-frame sim cost low — N rollback frames re-simulate N times inside one 16.6ms frame (the 'spiral of death').
- Seed the RNG as a synced input. Never branch sim logic on un-synced data.

## Working log
_Append-only. Newest at top. Each entry: date · decision/change · open issues._

- 2026-07-05 · Fixed the two coupled launch-blocker bugs (unbounded frame drift + dead rollback)
  causing one-directional input propagation (ahead-peer sees behind-peer's paddle frozen). index.html
  only, no js/sim.js change, no ?v= bump. **BUG A (time-sync):** added module-level
  `highestRemoteInputFrame` (index.html:888) tracked in `receiveRemoteInput` (:15822) + reset in
  `startMultiplayerMatch` (:15734); added `MAX_FRAME_ADVANTAGE=2` (:892); added a frame-advantage
  STALL in `runPvPGameLoop`'s fixed-step loop (:16254-16269) that holds local pacing (netAccumulator=0
  + break, guarded on highestRemoteInputFrame>=0) when currentFrame runs > MAX_FRAME_ADVANTAGE ahead of
  the remote's estimated frame (highestRemoteInputFrame - INPUT_DELAY), keeping the gap inside
  MAX_ROLLBACK_FRAMES=8. Pure local pacing — never changes which frames/inputs simulateNetworkFrame
  sees. **BUG B (dead rollback):** `checkForRollback` (:16154) lower bound changed from the wrong var
  `lastConfirmedRemoteFrame+1` (set only by INPUT_ACK ~= currentFrame+INPUT_DELAY, so the scan range was
  always empty) to `gameStateHistory[0].frame` (oldest re-simulable snapshot); still returns the earliest
  mismatch. Added reconciliation in `performRollback`'s re-sim loop (:16205-16221): snap
  predicted*=actual for CONFIRMED previously-predicted frames after re-sim so a corrected frame triggers
  exactly ONE rollback then goes silent (still-predicted frames keep wasPredicted/predicted* so their
  later arrival can still roll back). Determinism-safe: dbg.determinism(180,12345)=954ea557 and
  dbg.aiDeterminism(50,42)=5afbc1a6 cannot move — every edit is in netcode-driver funcs the oracles
  bypass (they call simulateNetworkFrame directly); sim + AI paths untouched. node --check on extracted
  inline: PASS. Report: .superpowers/sdd/netcode-fix-report.md. Changes staged, NOT committed. · Open:
  (1) MAX_FRAME_ADVANTAGE=2 is untuned — needs live 2-peer tuning (stutter vs safety margin). (2) A
  prolonged stall on total input loss reads as a freeze until the existing disconnect path fires
  (disconnect handling out of scope, unchanged). (3) NOT live-verified — 2-peer sync confirmation is the
  human's; this is code-made + reasoned-correct only, NOT a sync-fixed claim.

- 2026-07-02 (golden re-pin) · Golden-hash stale-pin correction (owner-authorized; closes the
  re-baseline open issue from the two entries below). **Root cause found via `git log -S 8f6e6da1`:**
  the `8f6e6da1` pin was added IN `b7e492b` itself — that big squashed playtest commit measured the
  golden mid-way (correctly, right after the arc-collision change) but then bundled further
  sim-affecting balance changes in the SAME commit — fireball `baseSpeed 12->15` / `maxSpeed 20->26`
  (ABILITY_REGISTRY), frostbolt `hitboxRadius 0.25->0.4` (spawn site ~10808), parry return
  1.5x-of-current-speed — all exercised by the oracle's scripted casts (f%37 fireball, f%71
  frostbolt, f%53 parry), and never re-measured. So the pin was stale the moment it landed; the
  drift was inside the squash, not a post-commit change. The balance changes are deliberate (named
  in b7e492b's own commit message), so re-pinning is the correct resolution. **Fix:** re-pinned the
  js/sim.js header to `954ea557` with a full correction note + extended the re-baseline history
  chain (…60bf20f3 -> e9717f89 -> 2dd677de -> 8f6e6da1 [stale] -> 954ea557); bumped the cache-bust
  to `js/sim.js?v=29-golden-repin` in index.html per convention (comment-only sim.js change, but
  the ?v= discipline exists precisely so no client ever runs a stale cached sim). No sim behavior
  changed. Also documented in the header that the oracle must run from a FRESH SINGLE-PLAYER match —
  a mid-PvP run folded differently (`98e316e5` observed once mid-PvP earlier today vs `954ea557` in
  SP), which is oracle-environment sensitivity (pvp-mode deps), not nondeterminism. **Verification:**
  `node --check` sim.js + extracted inline PASS; live browser with the new ?v=: `VolleyboltSim`
  loads, fresh SP match `dbg.determinism(180,12345)` = `954ea557` twice (matches new pin), and
  self-stability spot-check `dbg.determinism(180,99999)` = `56c1c1ac` twice. Server killed, tab
  closed. NOTE: measurement taken with the moveAccum fix (entry below) already in the tree — the
  oracle pins `moveAccum` itself, so that fix cannot affect the fold, and the pre-fix stash
  measurement (entry two below) got the identical `954ea557`. · Open: the mid-PvP fold variance
  (`98e316e5`) means the oracle is not fully mode-independent — worth a future pass to pin whatever
  pvp-mode dep leaks into the run (suspects: gameMode-branched deps like completeCasting/
  syncLocalParryUI paths) so the oracle gives one answer everywhere; until then, fresh-SP is the
  documented measurement condition.
- 2026-07-02 · Frame-10 desync root cause identified and fixed (follow-up to the entry below, which could not reproduce it on fresh tabs): `combatant.moveAccum` — mutated by every movement input (`js/sim.js:385`, add-only), hashed by `hashGameState` (`index.html:14572`), but never reset by `resetGame()`'s paddle-reset block, unlike `paddleZ`/`prevPaddleZ`. Any client with prior paddle movement in the same page session (e.g., played singles, then hosted) carries a residual sub-step accumulator (0–0.3) into the match; the opponent's fresh load carries 0; with no movement input the divergence is permanent from the first compared frame (`MP_SYNC_LAG` = 10), heals never, and triggers zero rollbacks since inputs match predictions — exactly the audit's live signature, and why fresh-tab repro attempts stayed in sync. Fix: added `moveAccum = 0` for both combatants in `resetGame()`'s paddle-reset block (`index.html:16056-16057`), which runs on both clients at MP match start (`startMultiplayerMatch` → `resetGame`) and every round. Sim-safe: symmetric, deterministic, no `js/sim.js` change, no ?v= bump; `dbg.determinism` unaffected (the oracle pins `moveAccum` itself). Extract-inline + `node --check` PASS. The broadened `hashStartState` (entry below) now also covers `moveAccum`, so any recurrence fails loudly at match start. · Open: golden pin at `js/sim.js:22` (`8f6e6da1`) is stale — current unmodified code folds to `954ea557` (verified via git stash by the fix session below); lead should re-baseline the pin after confirming the drift commit was intentional. Repro-confirm for the fix: play singles briefly, quit to menu, host + join from a fresh second client, no input — F2 should stay `sync ✅` (pre-fix this desyncs at frame 10).

- 2026-07-02 · Fixed the two bugs from the same-day netcode pillar audit
  (`docs/superpowers/audits/2026-07-02-pillar-netcode.md`), scope-limited to those two bugs plus
  the diagnostic hardening the audit recommended. No js/sim.js change, no ?v= bump, no gameplay/
  balance touched. **Bug 1 (code-certain, fixed directly) — Juice input never crossed the wire.**
  `sendLocalInput` (index.html, was :14923-14934) sent `moveDir/parry/fireball/frostbolt/
  thunderstorm` but omitted `juice`; `receiveRemoteInput`'s two write sites (the fresh-record
  branch and the update-existing-record branch) likewise never read a `juice` field. Fixed all
  three: added `juice: input.juice || false` to `sendLocalInput`'s payload, and
  `juice: data.juice || false` to both `receiveRemoteInput` branches. Also brought the
  *predicted*-input shape into parity with confirmed inputs so a misprediction on `juice`
  actually triggers a rollback like the other one-shot actions do: `predictInput()` now returns
  `juice: false` (matching how it never predicts other actions as continuing true),
  `getRemoteInput()`'s stored prediction record now sets `predictedJuice: predicted.juice`, and
  `checkForRollback()` now compares `remote.predictedJuice !== remote.juice` alongside the other
  four action fields. Without this, a predicted-vs-confirmed juice mismatch would silently never
  roll back. **Bug 2 (frame-10 PvP desync) — could NOT reproduce live this session; no fix
  applied, static findings only (see below).** Read the audit's full checklist (cooldowns seeding
  asymmetry, seed exchange timing, nextProjectileId, juice/moveAccum/prevPaddleZ init,
  pvpParryState, stage/gate arrays) and traced `startMultiplayerMatch` → `resetGame` →
  `startRound` end to end on both the host and joiner code paths: `combatants.left`/`.right` are
  assigned once at scene init (`createCombatant('left'/'right')`, index.html ~1960-1966),
  independent of `isHost`; host-vs-joiner branching in `startMultiplayerMatch` (~14818-14841) only
  sets presentation flags (`inputSource`, `isLocalPlayer`, camera/label text) — the code comment
  confirms the joiner is explicitly NOT mirrored ("No flip: the joiner sees the SAME canonical
  view as the host"), so `flipCameraForClient` (defined index.html:4017) is never actually called
  in the current multiplayer-start path, ruling out the mirrored-view hypothesis; cooldown seeding
  (`{fireball:0,frostbolt:0,thunderstorm:0}` for left, `{fireball:2,frostbolt:3,thunderstorm:0}`
  for right, startRound ~15731-15736) runs identically on both clients since `combatants.left`/
  `.right` mean the same thing on both; the RNG seed is host-generated (`Date.now() % 2147483647`)
  and sent once in the same `START_MATCH` payload the joiner uses to call
  `startMultiplayerMatch(data.seed, ...)`, so no exchange-timing race was found. Found one real,
  separate completeness gap while auditing this (flagging, NOT fixing — out of scope since I
  couldn't confirm it's the live cause): `combatant.moveAccum` is set to 0 only once at
  `createCombatant()` (page load) and is never reset by `resetGame()`/`resetRound()`/
  `startRound()` at match start, unlike every other hashed per-combatant field — a leftover
  fractional `moveAccum` from movement before the match started (e.g. a prior single-player
  session) could seed an asymmetry a fresh two-tab test wouldn't catch. **Live verification
  attempted twice, per the audit's own checklist** (`python3 -m http.server 8094`, two Playwright
  tabs, full DOM lobby flow: host → join → ready → start, zero scripted input): first attempt
  reached frame ~590 (host) / ~570 (joiner) with `dbg.sync()` reporting `in sync`, 0 mismatches,
  `desync: null` on both peers before I stopped it; second attempt (fresh reload, same flow) ran
  to frame 5078 (host) / 4211+ (joiner), still 0 mismatches, 0 rollbacks, `desync: null` on both —
  the frame-10 desync the audit reported (twice, cross-validated) did not reproduce in either
  attempt. Per the task's explicit instruction not to apply a speculative fix without live
  confirmation, bug 2 is left as this static-analysis + candidate-lead (`moveAccum`) writeup for
  the owner, not a code change. **Diagnostic hardening (applied regardless, as requested):**
  broadened `hashStartState()` (index.html ~14497) from 6 fields (towerHealth/mana/score/paddle
  mesh x,z/projectile count/currentFrame) to also cover everything `hashGameState()` hashes every
  frame — `prevPaddleZ`, `moveAccum`, `manaRegen`, `freezeTime`, `castProgress`, `castTime`, all
  three cooldowns, `juice`/`juiceActive`/`juiceTimer` (both sides), `netRngSeed`,
  `nextProjectileId` — PLUS fields `hashGameState()` itself does *not* cover but a start-of-match
  asymmetry could still hide in: `pvpParryState.left`/`.right` (canParry/active/timer/cooldown/
  cooldownMax) and the full stage/gate-health contract (`currentStage`,
  `playerGateHealthByStage[]`, `aiGateHealthByStage[]`, `stageResults[]`, `totalRoundsPlayed`,
  `lastRoundAtStage[]`). Same FNV-1a fold, same call site, same existing "Sync warning: starting
  state mismatch" `showMessage()` + `console.warn` behavior on mismatch — purely additive field
  coverage, no behavior change when both peers agree (confirmed no false-positive warning fired in
  either live PvP session this round). **Verification:** `node --check` on the extracted inline
  script (sed 620,17957p → temp .js) and on `js/sim.js` (untouched, diff-clean) both pass. Golden
  oracle `dbg.determinism(180, 12345)` returns `954ea557` on this session's code — this does
  **not** match the pinned golden `8f6e6da1` (js/sim.js:22), but confirmed via `git stash` that
  the *unmodified* pre-session codebase (commit `b7e492b`, before any of this session's edits)
  already returns the identical `954ea557` — so the golden mismatch is pre-existing repo drift,
  not something this session introduced; my index.html changes provably cannot affect
  `dbg.determinism` since it calls `window.VolleyboltSim.simulateNetworkFrame` directly with its
  own scripted inputs, bypassing `sendLocalInput`/`receiveRemoteInput`/`predictInput`/
  `checkForRollback` entirely. Two-tab PvP re-verification after the bug-1 fix: no-input sync held
  past the required 600-frame/10s bar on both peers (host lastOkFrame 610 @ frame 629; joiner
  lastOkFrame 1290 @ frame 1302); `pendingNetInput.juice=true` fired on BOTH sides plus movement
  input on both — sync held with 0 mismatches through frame 3000/2990 (host) and 3656/3630
  (joiner), later re-checked at frame 5078/5050 (host) and 4211/4190 (joiner), all `desync: null`
  throughout. Full telemetry text saved to
  `docs/superpowers/audits/netcode-fix-shots/2026-07-02-final-telemetry.txt` (no screenshots this
  session — kept the live-browser window open only as long as needed per owner request; server
  killed and both tabs closed at the end). · **Open issues:** (1) Bug 2's frame-10 desync is
  UNRESOLVED — could not reproduce live, so no fix is in the tree; next session should try to
  repro under conditions closer to the audit's (their session flagged the Playwright harness
  itself as flaky/tab-reloading, so a repro attempt with a different automation setup, or a real
  two-human manual test, is the next step) and, if reproduced, diff `captureGameState()` on both
  peers at the same frame number to find the exact field before trusting any fix. (2) The
  `moveAccum` reset gap is real (not covered by `resetGame`/`resetRound`/`startRound`) and now
  caught going forward by the broadened `hashStartState()`, but was not fixed — a one-line
  `c.moveAccum = 0` in `startRound`'s per-combatant loop would close it if a lead wants it. (3) The
  pre-existing golden-hash mismatch (`954ea557` vs the `8f6e6da1` pinned at js/sim.js:22) predates
  this session and is unrelated to these two bugs — flagging for whoever owns golden re-baselining
  next, since the pin in the file is currently stale relative to `b7e492b`.
- 2026-06-29 · Step 2.3 Task C code edits (C.1–C.8, CODE only — lead owns SP-feel playtest C.9 / oracle C.10 / AI-oracle C.11 / commit C.12; no js/sim.js change, so NO ?v= bump). THE BIG SWAP: singles now runs one `window.VolleyboltSim.simulateNetworkFrame(buildPlayerInput(), decideAI(...), FIXED_DT, buildSimCtx())` per tick; doubles still on `updateGameLogic` (branched in the accumulator loop ~13051-13061 by `isDoublesMode()`). index.html edits: (1) C.4 — `buildAISingleView` (~11949) mesh→sim reads: `p.mesh.position.x/z`→`p.x/p.z`, `aiPaddle.position.x/z`→`cr.paddleX/cr.paddleZ`, `playerPaddle.position.z`→`combatants.left.paddleZ`; zero `.mesh` reads remain (awk-grep confirmed); stale "Mesh-reading boundary" comment updated. (2) C.3/C.5 — new `buildPlayerInput()` (movement keys `KeyW`/`ArrowUp`=+1, `KeyS`/`ArrowDown`=-1 — the SAME keys old SP loop read at 12304; one-shot parry/fireball/frostbolt/thunderstorm/juice from pendingNetInput, cleared after read) + new `runSinglePlayerFrame(dt)` (spFrameCounter++ → buildPlayerInput → `decideAI(buildAISingleView(), spFrameCounter, makeAIRng(spFrameCounter ^ AI_RNG_SEED), DEFAULT_AI_PARAMS)` → simulateNetworkFrame; NO extra mirroring — sim mirrors paddle+proj to mesh INTERNALLY via SIM_DEPS.mirrorPaddleToMesh/mirrorProjectileToMesh, exactly as runNetworkFrame does), placed in the game-setup closure after buildAISingleView. (3) C.5 — `updateGameLogic`'s unconditional `spFrameCounter++` (12124) guarded to `if (isDoublesMode())` (singles increments in runSinglePlayerFrame; mutually exclusive per frame via the branch). (4) C.6 — keydown Digit1/2/3 `castFromLoadoutSlot(N,'player')`→resolve loadout slot to spell.id and set `pendingNetInput[sp.id]=true` (loadout is fixed to [fireball,frostbolt,thunderstorm] so order == MP's hardcoding; kept pointCmdSlot for pointer feel); KeyQ removed direct `activateJuice('player')`, kept `pendingNetInput.juice=true`; `parryCallback` (11249) GUTTED from old local-parry activation (parryActive/parryTimer/canParry/bubble/GUI) to just `pendingNetInput.parry=true` — this single change covers all 3 parry sites (Space 3504, parry-button click 3573, Babylon GUI parry button 6323) since all call parryCallback; sim's SIM_DEPS.onParryActivated handles bubble+sound. (5) C.7 — accumulator loop branched. MP path (~3454-3476 keydown early-return) untouched. Extract-inline + `node --check` PASS. · Plan assumptions that did NOT hold / deviations: (a) SP casts route through `castFromLoadoutSlot(slot,'player')`, NOT direct `startCasting('player',...)`/`castFrostbolt('player')`/`executeThunderstorm('player')` as plan C.6 wrote — resolved each Digit→slot→spell.id (loadout fixed to DEFAULT, so == MP). (b) Plan C.3 pseudocode used ArrowRight/ArrowLeft/a/d (X-axis) — WRONG; Volleybolt paddles move on Z, real SP keys are KeyW/KeyS/ArrowUp/ArrowDown; used those. (c) Plan C.5 used `spRng`/`AI_PARAMS` — those do NOT exist; used `makeAIRng(spFrameCounter ^ AI_RNG_SEED)`/`DEFAULT_AI_PARAMS` per correction #1 (matches existing call at 12382). (d) Plan C.5 hand-rolled paddle/proj mesh mirroring after the sim call — REDUNDANT; the sim already mirrors internally (sim.js 314/360), so runSinglePlayerFrame does NOTHING extra, matching runNetworkFrame (which also does no post-sim mirror). (e) SCOPE ADDITION beyond literal C.6: the Babylon GUI cast buttons (fireball/frostbolt, ~6309-6318) called `castFireball()`/`castFrostbolt()` directly — a player-input path that would BYPASS the sim; routed them to `pendingNetInput.fireball/frostbolt=true` too (also fixes the same latent bypass in MP). Confirmed `combatants.left.paddle=playerPaddle` / `combatants.right.paddle=aiPaddle` set at init (7637-7638), so sim's mirrorPaddleToMesh drives the SP meshes. · Open / flagged to lead: (1) `syncLocalParryUI` early-returns unless `gameMode==='pvp'`, so in SINGLES the parry-button HUD (cooldown sweep / ready-active state) no longer updates — the in-world parry bubble (onParryActivated) still shows, so parry feedback exists, but the HUD button looks static; cosmetic, flag for C.9. (2) `canParry` global now never set false (only setter was the gutted parryCallback) → stays initial `true`, so the Space/click guards `&& canParry` always pass; sim enforces real parry readiness. (3) thunderstorm keyup channel-end (3546-3548) still calls `endThunderstormChannel(combatants.left)` DIRECTLY (mutates sim state outside simulateNetworkFrame) — pre-existing SP behavior, untouched; MP has no release input so MP thunderstorm is duration-based — asymmetry, not introduced by this task, flag for playtest. (4) sim movement is quantized (STEP_SIZE 0.3, speed 20) vs old SP continuous playerSpeed — a feel difference inherent to the unification, confirm in C.9. (5) old singles body in updateGameLogic now unreachable for singles but still present (deletion = Task D).
- 2026-06-29 · Step 2.3 Task A code edits (A.1–A.10, CODE only — lead owns browser validation / G_2.3 pin / sim.js ?v= bump / commit). Ported SP paddle-return into the sim's fireball `behavior.onPaddleHit` + added deterministic `prevPaddleZ` to the rollback contract. js/sim.js: collision hitbox `paddleHalfDepth` 0.8→1.25 (effective 1.25+0.75=2.0); `ctx.dt = dt` set at top of `updateNetworkProjectiles` so onPaddleHit can read dt (signature unchanged — threaded via ctx, NOT a new param); `applyNetworkMovement` records `combatant.prevPaddleZ = combatant.paddleZ` after the defensive paddleZ/paddleX init and BEFORE the `moveDir===0` early-return (so stationary frames zero the momentum, matching SP feel). index.html fireball onPaddleHit: hitOffset divisor 0.8→1.25; speed-floor `Math.max(.,10)` now LEFT-side only (AI/right uses raw speed); momentum `proj.velZ += ((paddleZ-prevPaddleZ)/ctx.dt)*0.4`; block-mana unconditional (removed `!proj.isParried` guard); cast-pushback `if(c.casting!==null) ctx.deps.applyCastPushback(c)`; opponent-parry reset `if(proj.isParried && proj.parriedBy===opp) ctx.deps.resetProjParryState(proj)` (opp = 'ai' for left, 'player' for right). Two new SIM_DEPS: `applyCastPushback` (translates combatant→'player'/'ai' side string for getCombatantLegacy) and `resetProjParryState` (resets proj.isParried/parriedBy directly). Rollback contract: `prevPaddleZ` added to hashGameState (`mix(q(c.prevPaddleZ))` after paddleZ — DELIBERATE golden change → G_2.3), captureGameState (both sides), restoreGameState (both sides, `||0`), combatant init (7627-7630) and round-reset (16655). node-check sim.js + extracted inline pass; purity grep clean (only comment hits, lines 21/61). · Plan assumptions that did NOT hold: (1) dt was NOT in onPaddleHit scope — signature is (proj,side,ctx); threaded via `ctx.dt` (set in updateNetworkProjectiles) rather than adding a 4th param, to avoid touching the frostbolt onPaddleHit at 2170. (2) Parry fields are `proj.isParried`/`proj.parriedBy` (NOT `proj.parryState`/`ownerSide` as plan 5g/A.5 wrote) — used SP's exact guard from 12665/12744. (3) `window.resetProjParryState` does NOT exist — SP's resetProjParryState (index.html ~11349) is a LOCAL closure, so the dep replicates its two field assignments inline (window fallback kept but never hit). (4) `applyCastPushback` is NOT on window and takes a 'player'/'ai' STRING (not a combatant object as plan A.6's wrapper implied) — dep converts via combatant.side. (5) createCombatant has NO `paddleZ:0` literal (plan A.3 assumed one) — paddleZ is first assigned at 7627-7630; added prevPaddleZ there + at round-reset 16655. · Open / flagged to lead: momentum is CURRENT-frame delta ((paddleZ-prevPaddleZ)/dt after movement), whereas SP's window.playerPaddleVelZ is ONE-FRAME LAGGED (recorded at top of updateGameLogic before movement) — deliberate per plan A.4, accepted as part of G_2.3; minor feel/numeric difference vs SP, confirm in A.13 playtest. During an active freeze prevPaddleZ does not update (applyNetworkMovement returns at the freeze guard before recording) — a frozen paddle hit mid-move retains one stale step of momentum; rare edge, flagged.
- 2026-06-29 · Step 2.2 Task C code edits (C.1–C.9, CODE only — lead owns browser validation / G3 pin / version bump / commit). js/sim.js: added pure `simActivateJuice(combatant, ctx)` (guard juiceActive/juice<MAX → false; set juice=MAX, juiceActive, juiceTimer=DURATION, reset ALL cooldowns once, FX via deps.onJuiceActivate gated by !isResimulating); juice drain loop at top of `simulateNetworkFrame` (drains unconditionally even while frozen, clears + deps.onJuiceEnd at ≤0); juice activation from input after parry processing; auto-parry burst in BOTH paddle blocks (after Lightning-Shield, before onPaddleHit) — REFLECT only (`D.parryProjectile(proj, side, 0); continue;`), no toDestroy/no extra sound. index.html: frostbolt+thunderstorm cast-charge via `window.addJuice(combatant, JUICE.CHARGE.cast)` in their registry onCast; SIM_DEPS onJuiceActivate/onJuiceEnd → window.onJuiceStart/onJuiceEnd + logJuice/logCombat. node-check (sim.js + extracted inline) pass; purity grep clean (only comment hits). · Open / plan deviations flagged to lead: (1) C.4 — did NOT add the blanket charge hook in tryNetworkCast: fireball already charges once via the shared completeCasting→fireFireball (line 17771, already in G2), so a tryNetworkCast charge would DOUBLE fireball. Matched SP per-ability instead (fireball=unchanged, frostbolt/thunderstorm charge in onCast). Oracle casts frostbolt (f%71) so G2→G3 still changes legitimately via frostbolt charge, not via a double-charge bug. (2) C.6 — fireball burst NOT added to behavior.onCast: fireball is castType 'channel' (onCast only starts the channel, no proj exists there); the 6-tier burst already lives in the shared `spawnFireball` (index.html ~10490-10502, reached by the sim via completeCasting→fireFireball→spawnFireball), so no edit needed/possible. (3) C.5/C.7 — SP code does NOT push parried projectiles to toDestroy nor add an extra playSound (parryProjectile reflects + sounds itself), and onJuiceStart already does tint+'juiceUp'+drone, so the plan's toDestroy/playSound/_juiceTint/playSample('juiceUp') extras were dropped to match SP exactly. (4) auto-parry aimDir forced to 0 (neutral) for determinism — SP reads keys[]/AI findOpenTarget there, which is not sim-safe. (5) sim drain loop does state only; SP's per-frame aura wobble/tint-reassert (updateJuice ~1739-1771) is cosmetic and still driven by SP's untouched updateJuice — MP lacks the wobble until a future onJuiceTick dep (no determinism/behavior impact).
- 2026-06-29 · Step 2.2 Task B code edits (B.1–B.7): added pure `simAddJuice` + `resolveNetworkProjVsProj(ctx, toDestroy)` to js/sim.js (frostbolt cancel + fireball overpower/mutual-cancel, proj.x/z only, FX via deps gated by !isResimulating); called it once after the per-projectile loop in updateNetworkProjectiles; added 3 FX deps (onFrostboltCancel/onOverpower/onProjCancel) to SIM_DEPS; added juice/juiceActive/juiceTimer to hashGameState (deliberate golden change → lead re-baselines G2). node-check (sim.js + extracted inline) pass; purity grep clean (only comment hits). · Open: gate-collision is INSIDE the per-proj loop, so resolve runs after gate hits this frame, not before (plan/handoff assumed gate was a separate later pass) — flagged to lead, no observed correctness impact (collisions are mid-court, gate at x=14). FX wrappers wrap into BABYLON.Vector3 because createImpactFlash(copyFrom)/showCombatTextAt(clone) require it; plan's plain {x,y,z} would have thrown. Browser validation / golden pin / commit owned by lead (B.8–B.16).
- _(start here)_

---
_[Engine pillar](../pillars/engine.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_

- 2026-06-29 · Phase 2.2 COMPLETE (Tasks A–D). Juice/ultimate + projectile-vs-projectile now in the deterministic sim; MP gained both. Golden re-baselined twice (b1df6797 → ad7c0e42 → 3770e2c7), each gated on correctness scenarios (overpower/cancel/frostbolt-cancel/pass-through/grace; juice activate/drain/auto-parry/6-tier). AI oracle 2666491c unchanged. Found+fixed a latent cache bug: js/sim.js had no ?v= cache-bust (now versioned). SP duplicate untouched — removal is Step 2.3. · Open: MP juice aura wobble cosmetic-only (SP-driven; needs onJuiceTick dep someday); auto-parry aimDir forced 0 (deterministic; minor aim divergence vs SP when a key is held — revisit in 2.3 when inputs thread through).
