# Online Doubles W1+W2 (Lobby + Lockstep Mesh) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Four humans (or fewer + AI) create/join a room, pick sides fighting-game-style, ready up, and play online doubles in deterministic LOCKSTEP (rollback comes in W3) — co-op with friends.

**Architecture:** Host-relay star. Guests keep the existing single-`conn`-to-host shape; only the HOST grows a multi-connection layer (`guestConns` map + broadcast). A host-authoritative 4-slot lobby state machine broadcasts `LOBBY_STATE`. In-match, guests send their slot's input to the host; the host merges all four streams (filling AI slots from the existing deterministic doubles AI as **virtual players**) and broadcasts per-frame `INPUT_SET`s; every client steps the UNCHANGED sim only when it holds the set for its current frame (lockstep + input delay). Star hash-sync from frame 0 proves cross-machine determinism before W3 adds rollback.

**Tech Stack:** PeerJS DataConnections (unordered), the existing deterministic sim (`js/sim.js` — UNTOUCHED), inline index.html.

## Global Constraints

- All six pinned goldens byte-identical after every task (header authoritative: singles a90063b5/5e5eca1b, AI e6fdfae9, doubles 47424ad5/6e043c14, aiDoubles 0e029492). `js/sim.js` untouched (no `?v=` bump expected; if a sim edit seems needed, STOP).
- Classic 1v1, local doubles, and singles play identically — new code is new paths gated by `netMode`, or provably-additive plumbing with identity walks.
- No `Math.random` in new code. NO browser automation by implementers (controller runs owner-delegated verification).
- Line refs verified at commit `8d36938` against the netcode brief (persisted at `.superpowers/sdd/explore-netcode.md` — REQUIRED READING for every task); locate by quoted code if drifted.
- Message `type` strings for doubles end in `_D` (INPUT_D, READY_D…) so the two protocols can never cross-fire in a mixed-version accident.
- Slot indices are canonical everywhere: **0=Blue Front(left), 1=Blue Back(leftBack), 2=Red Front(right), 3=Red Back(rightBack)**; `SLOT_KEYS = ['left','leftBack','right','rightBack']`.

## File Structure

All work in `index.html`: (1) net-core additions near the existing connection code (~17660s), (2) lobby DOM near the existing lobby views (~317-405) + wiring near `wireDOMLobby` (~16892), (3) match-start + frame-loop near `startMultiplayerMatch`/`runPvPGameLoop` (~18734/19454), (4) hash-sync extensions near `mpSync` (~18011).

---

### Task 1: Host multi-connection layer + 1v1 hijack fix

**Files:** Modify `index.html` (connection lifecycle ~17660-17800). Read `.superpowers/sdd/explore-netcode.md` §1, §6, §8 first.

**Interfaces produced (later tasks rely on these exact names):**
- `let netMode = 'none';   // 'none' | 'duel' (classic 1v1) | 'doubles'` — set by the lobby entry points (Task 2 sets 'doubles'; existing 1v1 host/join paths set 'duel'; cleanupPeer resets 'none').
- `const guestConns = new Map();  // peerId -> { conn, slot, name, ready, lastPongTime, ping }` (host-only, doubles-only).
- `function hostBroadcast(msg, exceptPeerId)` — sends to every OPEN guest conn except the named one.
- `function guestConnFor(peerId)` / `function forEachGuest(fn)` — accessors.
- `function dropGuest(peerId, reason)` — closes + deletes + notifies the lobby state machine (Task 2's `netLobbyOnLeave(peerId)`, called only if defined).

**Steps:**

- [ ] **1.1** Add the declarations (`netMode`, `guestConns`, helpers above) next to `let conn = null;` (~L927). `hostBroadcast`:
```js
        function hostBroadcast(msg, exceptPeerId) {
            for (const [pid, g] of guestConns) {
                if (pid === exceptPeerId) continue;
                if (g.conn && g.conn.open) { try { g.conn.send(msg); } catch (e) {} }
            }
        }
```
- [ ] **1.2** Rework `peer.on('connection')` (L17706-17712) by `netMode`:
```js
            peer.on('connection', (connection) => {
                if (!isHost) { try { connection.close(); } catch (e) {} return; }
                if (netMode === 'doubles') {
                    if (guestConns.size >= 3) {           // room full — reject the 4th guest
                        connection.on('open', () => {
                            try { connection.send({ type: 'ROOM_FULL_D' }); } catch (e) {}
                            setTimeout(() => { try { connection.close(); } catch (e) {} }, 250);
                        });
                        return;
                    }
                    setupGuestConnection(connection);      // Task 1.3
                    return;
                }
                // Classic 1v1 ('duel'): FIX the pre-existing hijack — a second joiner used to
                // silently overwrite `conn`, orphaning the real opponent. Reject extras.
                if (conn && conn.open) {
                    connection.on('open', () => {
                        try { connection.send({ type: 'ROOM_FULL_D' }); } catch (e) {}
                        setTimeout(() => { try { connection.close(); } catch (e) {} }, 250);
                    });
                    return;
                }
                conn = connection; setupConnection();
            });
```
- [ ] **1.3** `setupGuestConnection(connection)` (host side, doubles): registers into `guestConns` keyed by `connection.peer` on `open` (slot assigned by Task 2's `netLobbyOnJoin`), wires `data` → `handleDoublesNetMessage(connection.peer, data)` (Task 2 defines it; guard `if (window.handleDoublesNetMessage)`), `close`/`error` → `dropGuest(peerId, 'left')`. Include per-guest ping bookkeeping fields (`lastPongTime: performance.now(), ping: 0`).
- [ ] **1.4** Per-guest heartbeat: `startDoublesPingLoop()` / `stopDoublesPingLoop()` — every 1000ms host sends `{type:'PING_D', time}` to each guest and checks each `g.lastPongTime` against the existing `PONG_TIMEOUT_MS` (5000, L17829) → `dropGuest(pid, 'Connection lost')`. Guests answer `PING_D` with `{type:'PONG_D', time}` over their single `conn`, and track the host's liveness with the EXISTING 1v1 heartbeat machinery unchanged (guest→host uses `startPingMeasurement` as-is — verify it only needs `conn`, which for a guest IS the host link; gate any 1v1-specific UI writes by element existence, which is how they're already guarded).
- [ ] **1.5** `cleanupPeer()` (L17780-17793): before the existing single-conn close, add `for (const [pid, g] of guestConns) { try { g.conn.close(); } catch (e) {} } guestConns.clear(); stopDoublesPingLoop(); netMode = 'none';`. Existing behavior for 1v1 unchanged (guestConns is empty there).
- [ ] **1.6** Set `netMode = 'duel'` in the two classic entry points (`btnHost` handler ~L16900s and `connectJoinHandler` ~L16916), before `initializePeer`. Static walk: classic 1v1 flow byte-identical except a 2nd joiner is now rejected instead of hijacking (deliberate bug fix — note it for the reviewer; it cannot affect goldens: connection handling only).
- [ ] **1.7** Parse check; `git diff` scope index.html only; commit: `Online doubles net-core: host multi-connection layer (guestConns/broadcast/per-guest heartbeat) + fix 1v1 second-joiner hijack`

---

### Task 2: Doubles lobby — DOM, slot state machine, side pick/swap/ready

**Files:** Modify `index.html` (lobby DOM ~317-405; wiring near `wireDOMLobby` ~16892). Read brief §2 + M1's lobby decisions (spec table).

**Interfaces produced:**
- `let netSlots = null; // host-authoritative: [ {kind:'ai'|'human', peerId:null|string, name:string, ready:bool} x4 ]` (index = canonical slot). On guests, `netSlots` mirrors the last LOBBY_STATE.
- `let mySlot = -1;` (every client; host too).
- `function netLobbyOnJoin(peerId, name)` → assigns first open slot (index order 0..3), broadcasts. `function netLobbyOnLeave(peerId)` → frees slot to `{kind:'ai'}`, broadcasts.
- `function broadcastLobbyState()` (host) → `{type:'LOBBY_STATE_D', slots: netSlots, hostSlot: mySlot}` via `hostBroadcast` + local render.
- `function renderDoublesLobby()` — renders the 4 slot cards from `netSlots` (both roles).
- `window.handleDoublesNetMessage(peerId, data)` (host) and doubles cases added to guest-side `handleNetworkMessage`.
- Messages: `JOIN_HELLO_D {name}`, `LOBBY_STATE_D {slots, hostSlot}`, `PICK_SIDE_D {side:'blue'|'red'}`, `SWAP_D {}`, `READY_D {ready}`, `ROOM_FULL_D`, `LEAVE_D`.

**Steps:**

- [ ] **2.1** DOM: add `#lobbyDoublesView` as a sibling `.lobby-view` (markup follows the existing lobby idiom — reuse `.lobby-status`/`.game-btn` classes): room code line (reuse the host-code + copy pattern), a 2×2 slot-card grid (`#dslot0..#dslot3`, each showing team-colored border [blue 0/1, red 2/3 — source colors the way the STATUS rows do], position label FRONT/BACK, name text, ready check `✓`), buttons `#btnPickBlue`, `#btnPickRed`, `#btnSwapPos`, `#btnReadyD`, host-only `#btnStartD` (disabled until all humans ready), `#btnLeaveD`. Register the view in `showLobbyView`'s id list (L16843-16861) — verify whether the list is an array to extend or per-id calls.
- [ ] **2.2** Menu entry: in the multiplayer mode view add `#btnHostDoubles` ("Host Doubles (2v2)") beside the existing host/join buttons; join stays the SAME join flow (one Join button — the room type is discovered on connect: a doubles host answers `JOIN_HELLO_D` with `LOBBY_STATE_D`; a duel host answers with the classic flow; the guest switches to `#lobbyDoublesView` on first `LOBBY_STATE_D`). `#btnHostDoubles` → `netMode='doubles'; isHost=true; netSlots = fresh 4×AI; mySlot=0; netSlots[0]={kind:'human',peerId:'HOST',name:getPlayerName(),ready:false}; initializePeer(code)` + show `#lobbyDoublesView` with the room code.
- [ ] **2.3** Guest join handshake: on `conn.on('open')` (guest, any join), send `{type:'JOIN_HELLO_D', name:getPlayerName()}` ONLY when... a guest can't know the room type pre-connect — send `JOIN_HELLO_D` always; a DUEL host ignores unknown types (verify `handleNetworkMessage`'s default case is a silent no-op — brief §7 registry; if it warns, add `_D` types to the ignore set). A DOUBLES host (`handleDoublesNetMessage`) on `JOIN_HELLO_D` → `netLobbyOnJoin(peerId, name)`. The classic 1v1 host flow is meanwhile UNCHANGED for duel rooms (its `conn`-based lobby continues; the hello is inert).
- [ ] **2.4** Host state machine: `netLobbyOnJoin` assigns the first index with `kind==='ai'` (join order = slot order = P-number), stores name (fallback `'P'+(i+1)` when empty), `ready:false`, broadcasts. `PICK_SIDE_D`: move the sender to the requested side's open slot, FRONT first (indices blue [0,1], red [2,3]); if that side is full for humans, ignore. `SWAP_D`: swap the sender with their same-side teammate slot **contents** (works whether teammate is human or AI). `READY_D`: set flag. All mutations → `broadcastLobbyState()`. Host's own picks call the same functions directly.
- [ ] **2.5** `renderDoublesLobby()`: paint the 4 cards (name or "AI", ready ✓, highlight your own slot — reuse the name-tag/STATUS color constants), enable `#btnStartD` only when `isHost && netSlots.every(s => s.kind==='ai' || s.ready)` AND at least one human besides checks (host counts; host must also ready up — host's Ready button sets its own slot). Guests see `#btnStartD` hidden, "waiting for host" line (existing idiom).
- [ ] **2.6** Leave/disconnect: `#btnLeaveD` → guest sends `LEAVE_D` + `cleanupPeer()` + back to mode view; host receiving `LEAVE_D`/`dropGuest` → `netLobbyOnLeave`. HOST leaving → `hostBroadcast({type:'LEAVE_D'})` then cleanup; guests receiving `LEAVE_D` from host → cleanup + "Host closed the room" status on the mode view.
- [ ] **2.7** Static verification: classic 1v1 lobby walk unchanged (new view hidden; hello ignored by duel hosts); doubles walk (host creates → 2 guests join slots 1,2 → guest 2 picks red → lands slot 2? [already there] → picks blue → moves to slot 1 if open... trace the interesting transitions incl. swap with AI). Parse check. Commit: `Online doubles lobby: 4-slot room, side pick (front-first) + swap + ready, host-authoritative LOBBY_STATE broadcast`

---

### Task 3: Online match start — slots → combatants, names over the wire

**Files:** Modify `index.html` (near `startMultiplayerMatch` L18734 and `startDoublesMatch` ~17040s). Brief §2 START_MATCH flow + M1 startDoublesMatch internals.

**Interfaces produced:**
- `function startOnlineDoublesMatch(seed, slots)` — every client (host builds `slots` from netSlots; guests receive it).
- Message: `START_MATCH_D {seed, slots: [{kind,name}x4], hash}` (peerIds stripped — clients only need kind+name).
- `let netSlotNames = null; // [name x4] for doublesSlotLabel's online override` and `doublesSlotLabel` extended: online (netSlotNames non-null) → `netSlotNames[slotIndex-1] || 'P'+slotIndex` for humans/AI alike; the local player's own settings-name already lives in their slot name (set at JOIN_HELLO). Cleared in `exitDoublesState`.
- `combatant.inputSource` values online: own slot `'local'`; all other slots `'network'` on guests; on the HOST, AI slots `'ai'` (host computes them) and human slots `'network'`.

**Steps:**

- [ ] **3.1** Host `#btnStartD` → build `slots`, pick `sharedSeed` the way 1v1 does (find how startMultiplayerMatch's caller makes `sharedSeed` ~L17001-17011 — same construction), `hostBroadcast({type:'START_MATCH_D', seed, slots, hash:null})`, then `startOnlineDoublesMatch(seed, slots)` locally. Guests: `case 'START_MATCH_D'` → same call. (Start-hash validation comes with W2's hash task — `hash:null` placeholder field reserved.)
- [ ] **3.2** `startOnlineDoublesMatch(seed, slots)`: mirrors `startDoublesMatch()`'s doubles setup (teamSize=2, ensureDoublesPaddles, back-combatant creation + rails + models via beginBackModels, arena resize, STATUS 4-row config, name tags) — FACTOR the shared body out of `startDoublesMatch` into `setupDoublesMatchCommon()` called by both (local keeps its AI driver; online continues below) rather than duplicating. Then online-specific: `gameMode='pvp'`, `netRngSeed = seed` (find the 1v1 seed application site in startMultiplayerMatch L18734+ and mirror), frame/history resets (same list as 1v1: currentFrame=0 etc. — brief §2), `netSlotNames` from slots, per-slot combatant assignment:
```js
            SLOT_KEYS.forEach((key, i) => {
                const c = combatants[key];
                if (!c) return;
                c.isLocalPlayer = (i === mySlot);
                c.inputSource = (i === mySlot) ? 'local'
                              : (isHost && slots[i].kind === 'ai') ? 'ai' : 'network';
            });
```
  Name tags + STATUS labels pick up `netSlotNames` via the doublesSlotLabel extension; the LOCAL player highlight (tag alpha 1.0) keys off `isLocalPlayer`, which now varies by slot — verify the tag-creation call passes the right combatant (it reads combatants[key].isLocalPlayer? check M1's createDoublesNameTags: it hardcoded left as local — extend it to key on `combatant.isLocalPlayer` with the M1 behavior as fallback).
- [ ] **3.3** The human's input capture must map to their SLOT, not always `left`: the W2 loop consumes `localInputHistory` for `mySlot`'s stream — nothing to change in capture (pendingNetInput/captureLocalInput are slot-agnostic); note it for Task 4.
- [ ] **3.4** W1 acceptance stub: after `startOnlineDoublesMatch`, the match scene loads but the frame loop DOESN'T run yet (Task 4) — gate: `if (netMode === 'doubles') return;` at the top of `runPvPGameLoop` with a comment "W2 wires runOnlineDoublesLockstep here", and show a small "ONLINE DOUBLES — W2 pending" dev text so a W1 multi-tab test can verify lobby→match-scene loading on all clients without sim movement.
- [ ] **3.5** Static verification: local doubles unchanged (factor-out identity walk — same calls, same order); 1v1 unchanged. Parse; commit: `Online doubles match start: shared doubles setup factored, slot→combatant assignment, names over the wire (W1 complete — lobby to loaded match scene)`

---

### Task 4: W2 — INPUT_D / INPUT_SET lockstep mesh + virtual players

**Files:** Modify `index.html` (input pipeline ~18860-18960; frame loop ~19454-19624; the doubles AI driver ~13595+). Brief §3, §4, §8.

**Interfaces produced:**
- `const INPUT_DELAY_DOUBLES = 4;` `const INPUT_SET_REDUNDANCY = 10;`
- Guest→host: `INPUT_D {frame, slot, input:{6 fields}, history:[{frame, input}×≤10]}` (own slot only).
- Host→all: `INPUT_SET_D {frame, inputs:[4×{6 fields}], history:[{frame, inputs}×≤10], senderFrame}`.
- Shared store: `let inputSets = [];  // frame -> [4 inputs] (confirmed only — lockstep has no prediction)`
- Host-only: `let guestInputQueues = [null, [], [], []]-shaped `slotInputs = [ [] x4 ]` (frame-indexed per-slot arrays for human slots; own slot filled locally; AI slots computed at merge).
- `function computeDoublesAIInput(slotKey)` — the existing local-doubles `mkInput` logic factored out of `runSinglePlayerFrame`'s doubles branch into a named function used by BOTH the local driver and the host's online merge (identical brains local and online — the local driver's behavior must stay byte-identical: same call order right, leftBack, rightBack).
- `function runOnlineDoublesLockstep(renderDt)` — the W2 frame loop.

**Steps:**

- [ ] **4.1** Factor `computeDoublesAIInput(slotKey, roleKey)` out of the doubles branch (index.html ~13601-13615 `mkInput`) — module-scope function closing over the same state (aiSlotState, DOUBLES_AI, skillToProfile, buildAIViewForSlot, spFrameCounter…). The local driver calls it in the exact same order as today; identity walk required (same expressions, same order — golden-sensitive for LOCAL doubles feel, though not pinned per-frame: the doubles goldens script inputs directly, so decideAI reorganization is oracle-visible only via aiDeterminismDoubles which folds decideAI directly — a pure factor-out with identical bodies moves NO fold; verify by Node extraction).
- [ ] **4.2** Guest send path: each lockstep tick, guest captures `captureLocalInput()`, stores into `localInputHistory[inputFrame]` (inputFrame = currentFrame + INPUT_DELAY_DOUBLES), sends `INPUT_D {frame: inputFrame, slot: mySlot, input, history}` (history from localInputHistory, last ≤10, stop-at-gap — mirror sendLocalInput's walk L18926-18960).
- [ ] **4.3** Host merge: on `INPUT_D` store into `slotInputs[slot][frame]` (idempotent, mirror storeRemoteInput's shape L18864-18885 without prediction fields). Host's own input → `slotInputs[mySlot][inputFrame]` each tick. Each tick, for the OLDEST unmerged frame f where every HUMAN slot has input: fill AI slots via `computeDoublesAIInput` (called at merge time, in slot-index order for determinism), assemble `inputSets[f] = [4]`, broadcast `INPUT_SET_D {frame:f, inputs, history: last ≤10 sets, senderFrame: currentFrame}`, advance. (Host consumes `inputSets` like everyone.)
- [ ] **4.4** Guest receive: `INPUT_SET_D` → store `inputSets[data.frame] = data.inputs` (+ history replay, idempotent). No ACK in W2 (redundancy covers loss; ACK/pacing comes with W3 rollback).
- [ ] **4.5** `runOnlineDoublesLockstep(renderDt)`: replace Task 3.4's gate with dispatch to this loop when `netMode==='doubles'`. Fixed-timestep accumulator like runPvPGameLoop (L19454-19524); per tick: capture+send/store local input for `currentFrame + INPUT_DELAY_DOUBLES`; if `inputSets[currentFrame]` missing → stall (`netAccumulator = 0; break;` — lockstep waits, W3 replaces with prediction); else `const set = inputSets[currentFrame]; const ctx = buildSimCtx(); ctx.backInputs = { left: set[1], right: set[3] }; window.VolleyboltSim.simulateNetworkFrame(set[0], set[2], 1/TICK_RATE, ctx); currentFrame++;` + `updateMatchPresentation(dt)` + hash bookkeeping (Task 5) + prune old sets (keep last 300).
- [ ] **4.6** First-frames barrier: don't step until `inputSets[0]` exists (host can't merge frame 0 until all humans' frame-0..DELAY inputs arrive — mirror the 1v1 start barrier's shape L19464-19483: capture+send while waiting).
- [ ] **4.7** Static verification incl. the factor-out identity (Node: aiDeterminismDoubles fold unchanged), 1v1/local-doubles untouched walks, packet-shape consistency INPUT_D↔merge↔INPUT_SET_D↔consume. Parse; commit: `Online doubles W2: lockstep input mesh — INPUT_D→host merge (virtual-player AI fill)→INPUT_SET_D broadcast, all four clients step the unchanged sim`

---

### Task 5: W2 — star hash-sync, desync abort fan-out, dbg.report

**Files:** Modify `index.html` (hash sync ~18011-18215; dbg.report ~17400s). Brief §5.

**Interfaces produced:**
- Host: broadcasts `SYNC_HASH_D {frame, hash}` every MP_SYNC_INTERVAL frames (reuse the constant); guests compare via the EXISTING `mpCompareHash` machinery (mpSync/badStreak/DESYNC_ABORT_STREAK reused — they're transport-agnostic; only the send sites fork by netMode).
- On sustained divergence: a GUEST sends `DESYNC_REPORT_D {frame}` to the host; the HOST broadcasts `DESYNC_ABORT_D {frame}` and everyone exits via `handleDisconnect('Match lost sync — please rematch')` (mpDesyncAborted guard reused).
- `dbg.report()`'s sync block gains `{ netMode, mySlot, guests: host-only [{slot, ping, lastPongAge}] }`.

**Steps:**

- [ ] **5.1** In the lockstep loop (Task 4.5) call `mpStoreHash(currentFrame)` exactly as 1v1's loop does (find its call site in runNetworkFrame ~L19547-19594 and mirror the represented-frame semantics — the FALSE-DESYNC fix comment there matters; in lockstep the represented frame is unambiguous but keep the same snap/frame discipline). Host: `mpMaybeSendHash` forked — `if (netMode==='doubles') hostBroadcast({type:'SYNC_HASH_D', frame, hash}) else conn.send(...)`. Guests do NOT broadcast hashes in W2 (star: compare against host only).
- [ ] **5.2** Guest: `case 'SYNC_HASH_D'` → `mpCompareHash(data.frame, data.hash)`. Rework `abortOnDesync` additively: `if (netMode==='doubles') { if (isHost) hostBroadcast({type:'DESYNC_ABORT_D', frame}) else conn.send({type:'DESYNC_REPORT_D', frame}); } else { existing conn.send DESYNC_ABORT; }` then the existing handleDisconnect. Host `case 'DESYNC_REPORT_D'` → `abortOnDesync(frame)` (guarded — becomes the broadcast). All: `case 'DESYNC_ABORT_D'` → guarded handleDisconnect (mirror the 1v1 case L17866-71).
- [ ] **5.3** SYNC_DETAIL diagnostics: doubles W2 keeps it host↔one-guest — `mpSendDetail` forks: guests send `SYNC_DETAIL_D` to host; host, on first divergence with a given guest, sends its groups to THAT guest only (unicast via guestConnFor). Same detailSent guards.
- [ ] **5.4** `dbg.report()` sync block extension (netMode/mySlot/guests array). Parse; static walks (1v1 hash path byte-identical — fork adds an else-branch only); commit: `Online doubles W2: star hash-sync (guests compare vs host), desync report→abort fan-out, dbg.report 4-peer sync state`

---

### Task 6: W2 verification — owner-delegated multi-tab determinism proof (CONTROLLER runs this; no implementer)

- [ ] **6.1** Controller (browser-authorized): 4 tabs on localhost:8080 — host doubles room, 3 guests join; verify lobby renders on all 4 (slots/names/ready); side pick + swap + ready flow; Start.
- [ ] **6.2** In-match: let it run 60s idle + 60s with host inputs (keyboard on host tab); on every tab read `dbg.sync()` — expect `in sync`, `lastOkFrame` advancing, zero console errors; `dbg.report()` shows the guests array on the host.
- [ ] **6.3** Mixed-fill runs: 1 human + 3 AI (host solo-starts), 2 humans same team (co-op vs 2 AI). Same sync expectations.
- [ ] **6.4** Negative: `dbg.forceDesync()` on a guest → all four exit with the sync-lost overlay within ~2s. Guest tab closed mid-match → W2 behavior is host `dropGuest` → match ends for all via LEAVE_D/disconnect flow (the AI-swap resilience is W3 — verify the exit is CLEAN, not hung).
- [ ] **6.5** Regression sweep: classic 1v1 two-tab match (unchanged flow incl. hash sync + a rematch); local doubles match; singles match; all six goldens re-run (must be byte-identical — nothing in W1/W2 touches sim or pinned paths).
- [ ] **6.6** Ledger the results; Andrew gets the co-op feel pass (his verification: play a real 2-human co-op match with a friend or second machine).

## Owner acceptance (after Task 6)

- Host a room from one machine, friend joins with the code, both pick BLUE (front/back), ready, start — AI fills red. Play the match: inputs feel synchronous (lockstep + 4-frame delay ≈ 67ms input latency — W3's rollback removes the stall-feel under jitter), P-names/tags correct on both screens, Battle Report at the end, both return to a clean menu.
