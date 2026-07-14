# Online Doubles W3 (Rollback + Resilience) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Online doubles stops feeling like lockstep: prediction + rollback over the 4 input streams, frame pacing, a reliable input mesh (ACKs + stall resends), and guest-drop → AI-swap so the co-op survives a friend dropping.

**Architecture:** Generalize the shipped 1v1 GGPO machinery (predict → snapshot every frame → roll back on mispredict) from two flat input histories to the star's confirmed-set stream. Every seated client speculates past the confirmed `inputSets` frontier using per-slot repeat-last-input prediction; the host's merge remains the ONLY authority; a confirmed `INPUT_SET_D` that differs from the prediction used triggers restore + resim. **Round ends are confirmed-only**: a speculative frame that would end the round restores and stalls instead (`resetRound` is a wall-clock mutation rollback cannot replay — this constraint caused two desync classes in W2 and is non-negotiable). Spectators stay on pure lockstep (no responsiveness need, less surface).

**Tech Stack:** PeerJS DataConnections (unordered), the deterministic sim (`js/sim.js` — UNTOUCHED), inline index.html.

## Global Constraints

- All six pinned goldens byte-identical after every task (header authoritative: singles a90063b5/5e5eca1b, AI e6fdfae9, doubles 47424ad5/6e043c14, aiDoubles 0e029492). `js/sim.js` untouched (no `?v=` bump expected; if a sim edit seems needed, STOP).
- Classic 1v1, local doubles, and singles play identically — new code is new paths gated by `netMode==='doubles'`, or provably-additive plumbing with identity walks. The 1v1 rollback functions (`predictInput`, `checkForRollback`, `performRollback`, `runNetworkFrame`) are NOT edited — doubles gets parallel `…Doubles` functions.
- No `Math.random` in new sim-relevant code. `Date.now()`/`performance.now()` are allowed ONLY for transport-side wall-clock throttles (resend timers, pacing) that never feed the sim.
- NO browser automation by implementers (controller/owner runs live verification). Verification per task = `node --check` on the extracted inline `<script>` + written identity/convergence walks in the report.
- Message `type` strings end in `_D`. New guest-side receive cases are `netMode==='doubles'`-gated. Slot indices canonical: 0=left, 1=leftBack, 2=right, 3=rightBack; -1=spectator; `SLOT_KEYS = ['left','leftBack','right','rightBack']` (index.html:1045).
- The doubles rollback window must stay **< MP_SYNC_LAG (32)** — reuse `MAX_ROLLBACK_FRAMES = 30` (index.html:1078). Hash discipline unchanged: `mpStoreHash(frame)` before increment, `mpMaybeSendHash()` after; resim overwrites via the same represented-frame mechanism (FALSE-DESYNC fix, index.html:19516-19526).
- Required reading for every task: `.superpowers/sdd/explore-w3.md` (line refs verified @ a621d8d; locate by quoted snippet if drifted).

## File Structure

All work in `index.html`: (1) reliability + AI-swap near the existing doubles net functions (~20317-20410 mesh, ~17520 netLobbyOnLeave, ~17646 INPUT_D receive, ~19168 INPUT_SET_D receive); (2) rollback core as new functions beside the 1v1 originals (~20771-20901) + a rewrite of `runOnlineDoublesLockstep` (~20993); (3) pacing inside the same loop; (4) telemetry in `refreshNetStatus` (~6130), `dbg.report`/`dbg.sync` (~19624-19640), `updateMpOverlay`.

---

### Task 1: Input-mesh reliability — ACKs + stall resends

**Files:** Modify `index.html` (sendDoublesInput ~20317, broadcastInputSet ~20400, INPUT_D receive ~17646, INPUT_SET_D receive ~19168, runOnlineDoublesLockstep stalled branch ~21063, new state decls near ~1135).

**Why:** W2's known weak link (explore-w3.md §3a): a stalled frame's input rides < 10 redundancy copies with no ACK and no resend; sustained loss = deadlock. Rollback (Task 3) reduces stalls but confirmation still gates everything.

**Interfaces produced:**
- `let doublesAckedInputFrame = -1;   // GUEST: highest contiguous own-slot frame the host has ACKed`
- `let doublesAckedSetFrame = new Map();  // HOST: peerId -> highest contiguous set frame that guest ACKed`
- `let doublesLastStallSend = 0;      // wall-clock ms of the last stall keepalive`
- New messages: `INPUT_ACK_D {slot, upTo}` (host→guest), `SET_ACK_D {upTo}` (guest→host).
- `const DOUBLES_HISTORY_CAP = 30;   // max frames of un-ACKed history per packet`
- `const STALL_RESEND_MS = 250;`

**Steps:**

- [ ] **1.1** Declare the state above next to `lastDoublesInputFrame` (~1135). Reset all three in `startOnlineDoublesMatch`'s netcode-reset block (~18184-18205): `doublesAckedInputFrame = -1; doublesAckedSetFrame = new Map(); doublesLastStallSend = 0;`

- [ ] **1.2** ACK-driven history depth in `sendDoublesInput` (~20320): replace the fixed `INPUT_SET_REDUNDANCY` walk bound with

```js
            // History depth: everything since the host's last contiguous ACK, capped. Falls back
            // to the fixed redundancy window until the first ACK arrives.
            const histFloor = doublesAckedInputFrame >= 0
                ? Math.max(inputFrame - DOUBLES_HISTORY_CAP, doublesAckedInputFrame + 1)
                : Math.max(0, inputFrame - INPUT_SET_REDUNDANCY);
            for (let f = inputFrame - 1; f >= histFloor; f--) {
                if (!localInputHistory[f]) break;   // stop-at-gap, same as today
                history.push({ frame: f, input: localInputHistory[f] });
            }
```

- [ ] **1.3** Host ACKs on INPUT_D receive (~17646, after the stores + merge call): compute the highest contiguous frame present for that slot starting from the guest's last known ACK, and reply on the same conn:

```js
                    // ACK the highest CONTIGUOUS frame we hold for this slot (gaps = still lost).
                    let upTo = Math.max(0, (guestConns.get(peerId)?.ackedUpTo ?? -1));
                    while (slotInputs[data.slot][upTo + 1]) upTo++;
                    const g = guestConns.get(peerId);
                    if (g) { g.ackedUpTo = upTo; try { g.conn.send({ type: 'INPUT_ACK_D', slot: data.slot, upTo }); } catch (e) {} }
```

  Add `ackedUpTo: -1` to the guestConns entry shape at `setupGuestConnection` (~18910).

- [ ] **1.4** Guest consumes `INPUT_ACK_D` (new case in the guest's `handleNetworkMessage`, netMode-gated, beside INPUT_SET_D ~19168): `if (data.slot === mySlot) doublesAckedInputFrame = Math.max(doublesAckedInputFrame, data.upTo);`

- [ ] **1.5** Guest ACKs sets: in the INPUT_SET_D receive (~19168), after storing, compute highest contiguous `inputSets` frame from the last sent ACK and `conn.send({ type: 'SET_ACK_D', upTo })` (track `let doublesSetAckSent = -1;` alongside 1.1's decls, only send when `upTo` advanced). Host consumes `SET_ACK_D` (new host-router case beside DESYNC_REPORT_D ~17664): `doublesAckedSetFrame.set(peerId, Math.max(doublesAckedSetFrame.get(peerId) ?? -1, data.upTo));`

- [ ] **1.6** ACK-driven set-history depth in `broadcastInputSet` (~20400): history floor = `min` over connected guests of `(doublesAckedSetFrame.get(pid) ?? -1) + 1`, capped at `frame - DOUBLES_HISTORY_CAP`; fall back to `INPUT_SET_REDUNDANCY` when no ACKs yet. Same stop-at-gap walk shape.

- [ ] **1.7** Stall keepalive in the lockstep loop's stalled branch (`if (!set) { … }` ~21063) — BEFORE zeroing the accumulator:

```js
                    // Stall keepalive: while frozen, inputFrame doesn't advance so nothing re-sends
                    // (the W2 weak link). Re-send the newest packet at a wall-clock throttle —
                    // transport-side only, never feeds the sim.
                    const now = performance.now();
                    if (now - doublesLastStallSend > STALL_RESEND_MS) {
                        doublesLastStallSend = now;
                        if (isHost) { if (inputSets[doublesMergeFrame - 1]) broadcastInputSet(doublesMergeFrame - 1); }
                        else if (mySlot >= 0 && localInputHistory[lastDoublesInputFrame]) {
                            sendDoublesInput(lastDoublesInputFrame, localInputHistory[lastDoublesInputFrame]);
                        }
                    }
```

  Note `sendDoublesInput`/`broadcastInputSet` must be idempotent for receivers — they are (first-write-wins stores, ~20337/20410); state that in the report. Guard `sendDoublesInput` re-entry: it must not re-push to history (it reads `localInputHistory`, doesn't write — verify and state).

- [ ] **1.8** Verify + commit: `node --check` extracted script; identity walks (1v1 sendLocalInput/receiveRemoteInput untouched; guest INPUT_ACK_D case netMode-gated; history-walk fallback identical to W2 until first ACK). Commit: `Online doubles W3: input-mesh reliability — INPUT_ACK_D/SET_ACK_D, ACK-driven history depth, stall keepalive resends`

---

### Task 2: Guest-drop → AI-swap (the co-op survives)

**Files:** Modify `index.html` (netLobbyOnLeave ~17520-17556, guest handleNetworkMessage new case beside MATCH_OVER_D ~19225, doublesSlotLabel/name-tag refresh, combat log helper).

**Interfaces produced:**
- New message: `SLOT_TO_AI_D {slot, name}` (host→all).
- Existing `MATCH_OVER_D` type + guest handler KEPT (still used by nothing on this path after this task, but the DESYNC/abort machinery is untouched and the handler is harmless — do not delete).

**Steps:**

- [ ] **2.1** In `netLobbyOnLeave`'s live-match seated-human branch (~17544, the C1 block `if (doublesMatchLive && !gameOver && i >= 0 && doublesSlotKinds[i] === 'human')`): REPLACE the `MATCH_OVER_D` broadcast + `handleDisconnect` with the swap:

```js
                // W3: the co-op survives a friend dropping — the vacated seat becomes a host-driven
                // virtual player. Flipping the kind is sufficient to unblock the merge: the gate
                // only waits on 'human' slots (hostTryMergeDoubles), and AI fill is computed at
                // merge time on the host and broadcast like any other input. Inputs the departed
                // guest already delivered for future frames stay valid (first-write-wins store) —
                // the AI takes over exactly at the first frame with no stored human input.
                doublesSlotKinds[i] = 'ai';
                const vacatedName = netSlots[i].name || ('P' + (i + 1));
                hostBroadcast({ type: 'SLOT_TO_AI_D', slot: i, name: vacatedName });
                applySlotToAI(i, vacatedName);   // host applies the same presentation locally (2.3)
```

  The existing post-branch bookkeeping (seat → AI in `netSlots`, ~17550) already runs after this block — verify order so the lobby view is consistent if the match later returns to it.

- [ ] **2.2** Guest receive case (netMode-gated, beside MATCH_OVER_D ~19225):

```js
                case 'SLOT_TO_AI_D': {
                    if (netMode !== 'doubles') break;
                    if (doublesSlotKinds) doublesSlotKinds[data.slot] = 'ai';
                    applySlotToAI(data.slot, data.name);
                    break;
                }
```

- [ ] **2.3** `applySlotToAI(slot, name)` — shared presentation helper (host + guests):

```js
        function applySlotToAI(slot, name) {
            // Wire-name override drives tags + STATUS labels (doublesSlotLabel reads netSlotNames).
            if (netSlotNames) netSlotNames[slot] = name + ' (CPU)';
            if (window.refreshDoublesNameTags) refreshDoublesNameTags();       // or the existing tag-text update path — reuse, don't rebuild meshes
            if (window.addCombatLogEntry) addCombatLogEntry(name + ' disconnected — CPU takes over', 'neutral');
        }
```

  Find the actual tag-text refresh mechanism (the M1 name-tag work refreshes label text live — reuse it; if only full rebuild exists, update the tag's text control directly). Find the actual combat-log append function name (search "combat log" / the parry/fireball log lines from the M1 LOG wave) and use it with a neutral/system styling that exists.

- [ ] **2.4** Edge walks (in report, each traced in code): (a) departed guest was mid-cast — inputs simply stop, sim state unaffected (no special handling); (b) drop while STALLED on that guest's input: kind flip → next `hostTryMergeDoubles` call (unconditional per-tick since a621d8d) AI-fills the gap frames → mesh unstalls; (c) drop during the between-round window: kind flips, merge still `!roundActive`-gated, drains on resume; (d) SPECTATOR drop path unchanged (splice branch); (e) post-`gameOver` drop unchanged (silent bookkeeping — the `!gameOver` guard); (f) 2-humans-same-team case: partner sees the CPU label, plays on.

- [ ] **2.5** Verify + commit: `node --check`; walks above. Commit: `Online doubles W3: guest drop mid-match becomes AI takeover — SLOT_TO_AI_D, merge unblocks via kind flip, combat-log announce`

---

### Task 3: Prediction + rollback core (the big one)

**Files:** Modify `index.html`: new state (~1135), new functions beside the 1v1 rollback block (after ~20901), rewrite the stepping section of `runOnlineDoublesLockstep` (~21036-21088), phantom-round-end gate in the driver `endRound` (~23759), history clear in the online-doubles `startRound` path.

**Interfaces produced:**
- `let predictedSets = {};        // frame -> [4 inputs] actually used for a SPECULATIVE step`
- `let doublesConfirmedFrontier = -1;  // highest contiguous inputSets frame (all clients)`
- `let doublesSpeculativeStep = false; // true while stepping a frame without a confirmed set`
- `let doublesPhantomRoundEnd = false; // endRound fired during a speculative step`
- `function buildPredictedSetDoubles(frame)` → `[4 inputs]`
- `function checkForRollbackDoubles()` → earliest mispredicted confirmed frame or -1
- `function performRollbackDoubles(toFrame)`
- Spectators (`mySlot < 0`) keep W2 pure lockstep — all new machinery is behind `mySlot >= 0`.

**Steps:**

- [ ] **3.1** Declarations near `lastDoublesInputFrame` (~1135); reset ALL in `startOnlineDoublesMatch` (~18184-18205): `predictedSets = {}; doublesConfirmedFrontier = -1; doublesSpeculativeStep = false; doublesPhantomRoundEnd = false; gameStateHistory = [];` (gameStateHistory reset already exists at ~18220 — verify, don't duplicate).

- [ ] **3.2** Frontier maintenance: in `storeInputSet` (~20410) and in the host's merge loop (`hostTryMergeDoubles` after `inputSets[f]` is stored, ~20388): `while (inputSets[doublesConfirmedFrontier + 1]) doublesConfirmedFrontier++;`

- [ ] **3.3** `buildPredictedSetDoubles(frame)` — per-slot best-known input, repeat-last-move zero-actions:

```js
        // Best-known input for every slot at `frame`, for a SPECULATIVE step. Authority note:
        // the merge remains the only authority — these values are throwaway guesses that a
        // confirmed INPUT_SET_D corrects via rollback. Per-slot sources, best first:
        //   own slot        -> localInputHistory (exact — input delay means we always know it)
        //   host+guest slot -> slotInputs[s][frame] if the INPUT_D already arrived (exact)
        //   anything else   -> repeat-last-move from the newest confirmed set ≤ frame-1
        //                      (NEVER run computeDoublesAIInput here — it mutates the host's
        //                      aiSlotState rings; speculative calls would poison real AI fills)
        function buildPredictedSetDoubles(frame) {
            const set = [null, null, null, null];
            for (let s = 0; s < 4; s++) {
                if (s === mySlot && localInputHistory[frame]) { set[s] = localInputHistory[frame]; continue; }
                if (isHost && slotInputs[s][frame]) { set[s] = slotInputs[s][frame]; continue; }
                let last = null;
                for (let f = Math.min(frame - 1, doublesConfirmedFrontier); f >= Math.max(0, frame - 10); f--) {
                    if (inputSets[f]) { last = inputSets[f][s]; break; }
                }
                set[s] = last
                    ? { moveDir: last.moveDir, parry: false, fireball: false, frostbolt: false, thunderstorm: false, juice: false }
                    : defaultInput();
            }
            return set;
        }
```

- [ ] **3.4** `checkForRollbackDoubles()` — mirror of the 1v1 scan (index.html:20790) against sets:

```js
        function checkForRollbackDoubles() {
            const scanFrom = gameStateHistory.length ? gameStateHistory[0].frame : 0;
            for (let f = scanFrom; f < currentFrame; f++) {
                const conf = inputSets[f], pred = predictedSets[f];
                if (!conf || !pred) continue;
                for (let s = 0; s < 4; s++) {
                    const a = conf[s], b = pred[s];
                    if (a.moveDir !== b.moveDir || a.parry !== b.parry || a.fireball !== b.fireball ||
                        a.frostbolt !== b.frostbolt || a.thunderstorm !== b.thunderstorm || a.juice !== b.juice) {
                        return f;
                    }
                }
            }
            return -1;
        }
```

- [ ] **3.5** `performRollbackDoubles(toFrame)` — mirror of `performRollback` (index.html:20817-20901; read it first, keep every commented invariant: snapshot-before-frame convention, slice-then-recapture, represented-frame hash overwrite, `isResimulating` mute):

```js
        function performRollbackDoubles(toFrame) {
            const stateIndex = gameStateHistory.findIndex(s => s.frame === toFrame);
            if (stateIndex < 0) { console.warn('Cannot rollback to frame', toFrame, '- no saved state'); return; }
            if (window.MP_LOG_ROLLBACKS) console.log('Rolling back from frame', currentFrame, 'to frame', toFrame);
            mpSync.rollbacks++; mpSync.lastRollback = currentFrame - toFrame;
            isResimulating = true;
            restoreGameState(gameStateHistory[stateIndex]);
            gameStateHistory = gameStateHistory.slice(stateIndex);
            for (let f = toFrame; f < currentFrame; f++) {
                let set = inputSets[f];
                if (set) {
                    delete predictedSets[f];              // reconciled — confirmed input applied
                } else {
                    set = buildPredictedSetDoubles(f);    // still speculative — re-predict with newest knowledge
                    predictedSets[f] = set;
                    doublesSpeculativeStep = true;
                }
                const ctx = buildSimCtx();
                ctx.backInputs = { left: set[1], right: set[3] };
                window.VolleyboltSim.simulateNetworkFrame(set[0], set[2], 1 / TICK_RATE, ctx);
                doublesSpeculativeStep = false;
                if (doublesPhantomRoundEnd) {
                    // A speculative resim frame tried to end the round. Round ends are CONFIRMED-ONLY
                    // (resetRound is a wall-clock mutation rollback can't replay). Truncate the
                    // speculative tail: pull currentFrame back to f and stall until sets confirm.
                    doublesPhantomRoundEnd = false;
                    restoreGameState(gameStateHistory[gameStateHistory.length - 1].frame === f
                        ? gameStateHistory[gameStateHistory.length - 1]
                        : gameStateHistory.find(s => s.frame === f));
                    gameStateHistory = gameStateHistory.filter(s => s.frame <= f);
                    for (const k in predictedSets) if ((k | 0) >= f) delete predictedSets[k];
                    currentFrame = f;
                    isResimulating = false;
                    return;
                }
                mpStoreHash(f);
                const nextFrame = f + 1;
                if (nextFrame < currentFrame) {
                    const snap = captureGameState();
                    snap.frame = nextFrame;
                    const idx = gameStateHistory.findIndex(s => s.frame === nextFrame);
                    if (idx >= 0) gameStateHistory[idx] = snap; else gameStateHistory.push(snap);
                }
            }
            isResimulating = false;
        }
```

- [ ] **3.6** Phantom-round-end gate in the driver `endRound` (~23759, the function the sim deps call — verify by the `D.endRound` wiring in `buildSimCtx`). VERY TOP, before any state write or timer:

```js
            // W3 CONFIRMED-ONLY ROUND ENDS (online doubles): a round end reached on a PREDICTED
            // input must not fire — its wall-clock cascade (transition timers, resetRound) is not
            // rollback-replayable, and W2 shipped two desync classes on exactly this seam. The
            // stepping code sees the flag, restores the pre-step state, and stalls until the frame
            // confirms; the round then ends identically on every client, on a confirmed step.
            if (netMode === 'doubles' && doublesSpeculativeStep) { doublesPhantomRoundEnd = true; return; }
```

  Identity walk required: this is the ONLY edit to a shared function in this task; the added branch is dead unless `netMode==='doubles' && doublesSpeculativeStep`, and `doublesSpeculativeStep` is only ever true inside the doubles speculative step/resim — 1v1, local doubles, singles byte-identical behavior.

- [ ] **3.7** Rewrite the stepping section of `runOnlineDoublesLockstep` (~21036-21088). Keep: intro gate, `!roundActive` pin, unconditional host merge, capture-once block, hash discipline, pruning, UI tail. Replace the stall-only gate with speculate-or-step:

```js
                // Rollback trigger first (mirror runNetworkFrame order): a confirmed set that
                // contradicts a prediction rewinds before we step further.
                if (mySlot >= 0) {
                    const rb = checkForRollbackDoubles();
                    if (rb >= 0) performRollbackDoubles(rb);
                }

                let set = inputSets[currentFrame];
                let speculative = false;
                if (!set) {
                    // Spectators stay pure lockstep; seated clients speculate within the window.
                    const specDepth = currentFrame - (doublesConfirmedFrontier + 1);
                    if (mySlot < 0 || specDepth >= MAX_ROLLBACK_FRAMES - INPUT_DELAY_DOUBLES) {
                        /* Task 1's stall keepalive lives here */
                        netAccumulator = 0; break;
                    }
                    set = buildPredictedSetDoubles(currentFrame);
                    predictedSets[currentFrame] = set;
                    speculative = true;
                }

                // Snapshot BEFORE simulating (1v1 convention: snapshot{f} = state before frame f).
                if (mySlot >= 0) {
                    if (gameStateHistory.length >= MAX_ROLLBACK_FRAMES) gameStateHistory.shift();
                    gameStateHistory.push(captureGameState());
                }

                const ctx = buildSimCtx();
                ctx.backInputs = { left: set[1], right: set[3] };
                doublesSpeculativeStep = speculative;
                window.VolleyboltSim.simulateNetworkFrame(set[0], set[2], 1 / TICK_RATE, ctx);
                doublesSpeculativeStep = false;

                if (doublesPhantomRoundEnd) {
                    // Speculative round end: un-step this frame and hard-stall until it confirms.
                    doublesPhantomRoundEnd = false;
                    restoreGameState(gameStateHistory[gameStateHistory.length - 1]);
                    gameStateHistory.pop();
                    delete predictedSets[currentFrame];
                    netAccumulator = 0; break;
                }

                if (!speculative) delete predictedSets[currentFrame];   // confirmed step needs no record
                mpStoreHash(currentFrame);
                currentFrame++;
                mpMaybeSendHash();
```

  (`inputSets[currentFrame]` present but `predictedSets[currentFrame]` also present = the frame was stepped speculatively earlier and the set arrived since — that is exactly what `checkForRollbackDoubles` catches at the top; when the prediction matched, reconcile by deleting the record in a matched-scan pass OR simply let the scan compare-equal and leave it — the scan must then delete matched records to stay O(window): after the compare loop in 3.4, when all 6×4 fields match, `delete predictedSets[f]`. Add that.)

- [ ] **3.8** Round-boundary history clear: in the online-doubles path of `startRound` (the GO-callback call and every between-round `startRound` — find the single point `startRound` runs with `netMode==='doubles'`; gate inside `startRound` is acceptable as an additive `if (netMode === 'doubles') { ... }` block):

```js
            // W3: no rollback may cross a round boundary (resetRound is wall-clock, not replayable).
            // Everyone is pinned at the same stop frame (the !roundActive pin) and round ends are
            // confirmed-only, so all stepped frames are settled — drop the old round's snapshots
            // and prediction records; the new round starts a fresh window.
            if (netMode === 'doubles') { gameStateHistory = []; predictedSets = {}; }
```

- [ ] **3.9** Report walks (all mandatory): (a) determinism — speculative steps touch only local state and are always corrected to the confirmed timeline by resim before their hashes can be compared (window 30 < MP_SYNC_LAG 32; hash frames are settled); (b) the phantom gate makes it impossible for ANY client to advance past a round-ending frame on prediction → the `!roundActive` pin + confirmed-only round ends → every client stops at the identical F+1 with identical state, resetRound applies uniformly (the W2 invariant is PRESERVED, now with prediction); (c) spectator path byte-identical to W2 (every new branch behind `mySlot >= 0`); (d) 1v1 byte-identical (parallel functions; single shared edit = 3.6's dead branch); (e) intro/warmup unchanged; (f) memory — predictedSets bounded by the spec-depth cap + round clears + the 300-frame prune (extend the ~21081 prune to `predictedSets`).

- [ ] **3.10** `node --check` + commit: `Online doubles W3: prediction + rollback over the 4-stream mesh — per-slot repeat-last prediction, snapshot/resim via the 1v1 machinery, confirmed-only round ends`

---

### Task 4: Frame pacing

**Files:** Modify `index.html` (runOnlineDoublesLockstep top-of-iteration ~21022 region, sendDoublesInput ~20317, broadcastInputSet ~20400, INPUT_D receive ~17646, INPUT_SET_D receive ~19168, new decls ~1135).

**Interfaces produced:**
- `let doublesRemoteFrame = -1;         // GUEST: host's currentFrame (senderFrame piggyback); HOST: min over seated guests`
- INPUT_D gains `senderFrame: currentFrame`; INPUT_SET_D already carries it (~20406, "W3 uses it").

**Steps:**

- [ ] **4.1** Piggyback: add `senderFrame: currentFrame` to the INPUT_D payload in `sendDoublesInput`; on host INPUT_D receive, track per-guest `g.remoteFrame = Math.max(g.remoteFrame ?? -1, data.senderFrame)`; host recomputes `doublesRemoteFrame` = min over guests whose slot kind is 'human' (AI-swapped and spectator conns must NOT pace the host — walk this in the report). Guest: on INPUT_SET_D receive, `doublesRemoteFrame = Math.max(doublesRemoteFrame, data.senderFrame)`.

- [ ] **4.2** Advantage stall, top of the while-iteration after the `!roundActive` pin (mirror 1v1 L20957-20958):

```js
                // Frame-advantage pacing (mirror 1v1): if we're far ahead of the slowest peer we
                // depend on, idle a beat instead of speculating deeper — keeps rollbacks short.
                if (mySlot >= 0 && doublesRemoteFrame >= 0 &&
                    currentFrame - doublesRemoteFrame > MAX_FRAME_ADVANTAGE) {
                    netAccumulator = 0; break;
                }
```

- [ ] **4.3** Report walks: start-of-match (`doublesRemoteFrame` -1 → gate inert until first packet, mirrors the 1v1 start barrier which the frame-0 warmup covers); solo host + 3 AI (no guests → -1 forever → never paces — correct, nothing to wait for); guest-drop mid-match (dropped guest leaves the min via the kind check in 4.1); spectator never paces anyone.

- [ ] **4.4** `node --check` + commit: `Online doubles W3: frame pacing — senderFrame piggyback, min-peer advantage stall (host paces on slowest seated human)`

---

### Task 5: Telemetry + status UI

**Files:** Modify `index.html` (refreshNetStatus ~6130, dbg.report/dbg.sync ~19624-19640, updateMpOverlay).

**Steps:**

- [ ] **5.1** Host ping display: `refreshNetStatus` currently reads only global `netPing` (never set on the doubles host). Additive branch: when `isHost && netMode==='doubles'`, display `max(g.ping)` over `guestConns` (worst link governs the feel); guests keep the existing `netPing` path.
- [ ] **5.2** `dbg.report()` sync block additions (host+guest): `{ rollbacks: mpSync.rollbacks, lastRollback: mpSync.lastRollback, frontier: doublesConfirmedFrontier, specDepth: currentFrame - (doublesConfirmedFrontier + 1), ackedInput: doublesAckedInputFrame }`. `dbg.sync()` prints the same one-liner.
- [ ] **5.3** `updateMpOverlay` shows `rollbacks N (last M)` in doubles as it does for 1v1 (verify — mpSync fields are shared, likely free; state what you found).
- [ ] **5.4** `node --check` + commit: `Online doubles W3: telemetry — host worst-guest ping, rollback/frontier fields in dbg.report + overlay`

---

### Task 6: Verification (CONTROLLER/OWNER runs this; no implementer)

- [ ] **6.1** Static gate re-run (controller): six goldens' Node candidates where extractable; `js/sim.js` diff empty across the whole W3 range.
- [ ] **6.2** Live multi-tab (browser-authorized session or Andrew): 4-tab match on localhost:8080 — throttle one tab (devtools CPU/network) and verify: no input-delay feel on the LOCAL character, `dbg.report()` shows rollbacks firing and specDepth > 0 under jitter, `in sync` throughout, round transitions clean over 3+ rounds.
- [ ] **6.3** Resilience: guest tab-close mid-match → CPU-takeover combat-log line on every remaining client within ~5s, match continues, no stall; the swapped slot visibly plays (AI moves).
- [ ] **6.4** Host tab-close mid-match → all guests exit via the disconnect overlay (unchanged W2 behavior).
- [ ] **6.5** `dbg.forceDesync()` on a seated guest → DESYNC_REPORT_D → all exit; on a spectator → only the spectator exits.
- [ ] **6.6** Regression: classic 1v1 two-tab match incl. rematch; local doubles; singles. Ledger the results.

## Post-plan notes

- The shipped-1v1 between-round latent desync (explore-w3.md §3e) is explicitly OUT of this plan (owner deferred, 2026-07-14).
- Host migration and TURN relay remain out of scope (spec).
- W4 (polish + ship) follows: lobby UX polish, itch zip, goldens ceremony.
