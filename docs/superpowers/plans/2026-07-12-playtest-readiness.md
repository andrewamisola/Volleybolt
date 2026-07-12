# Playtest Readiness (Audit Recommendations) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the still-open items from the 2026-07-02 full audit's recommendation list — desync gets a player-facing consequence (#3), one-click bug reports + version tag (#6), a join-attempt timeout message (#7), and the parry-HUD static-in-singles fix (#9).

**Architecture:** All changes are presentation/telemetry/lobby-layer edits inside `index.html`. **`js/sim.js` is never touched**, so the deterministic sim and its golden hash are unaffected. Each task reuses an existing mechanism (the sim's `syncLocalParryUI` dep, the disconnect overlay, the `dbg` console object, the lobby status labels) rather than adding new systems.

**Tech Stack:** Vanilla JS inside `index.html` (the inline script is authoritative — `const`/`let`, not `window.*`), PeerJS DataChannel messages, Babylon GUI overlay (existing), DOM pause overlay (existing).

## Global Constraints

- **Never edit `js/sim.js`.** None of these tasks touch sim logic. If a change seems to need a sim edit, stop — it's out of scope.
- **No gameplay/feel changes.** These are UI, telemetry, and connection-flow changes only (per the standing "SP must equal MP feel" directive; balance items #8/#10 were explicitly excluded from this plan).
- Verify the sim is untouched after all tasks: in a **fresh single-player match** with `?dev` in the URL, `dbg.determinism(180, 12345)` must return the golden hash pinned in the `js/sim.js` header comment (read the pin from the file at verification time — do not trust this document).
- The game is static HTML. Run it with `./play.command` or `python3 -m http.server 8000` from the repo root, then open `http://localhost:8000/?dev` (the `?dev` opt-in enables the `dbg` console object and F2 overlay).
- Line numbers below were verified on 2026-07-12 at commit `e97793b`. If they've drifted, locate by the quoted code, not the number.
- Commit after each task. No commits touch files outside `index.html` except this plan's checkboxes.

---

### Task 1: Parry-button HUD refreshes in singles (audit #9)

The sim calls the `syncLocalParryUI` dep every frame in BOTH singles and PvP (singles runs exclusively through the sim; see the comment at `index.html:12449` — "Singles parry now routes through the deterministic sim (pvpParryState)"). But the function's first line early-returns unless `gameMode === 'pvp'`, so in singles the parry button never leaves its initial state. The in-world parry bubble still works (driven by a different sim dep), so this is purely cosmetic — a stale-looking button.

The legacy singles parry UI path (`checkParryHits` at `index.html:12457`, `updateParryTimer` at `index.html:12510`) is superseded and does not drive the button in singles (that is exactly the bug), so extending `syncLocalParryUI` to singles cannot double-drive it.

**Files:**
- Modify: `index.html:18414-18416` (function `syncLocalParryUI`)

**Interfaces:**
- Consumes: `pvpParryState` (sim-owned parry state for both sides, `index.html:946`), `getPvPParryState(side)` (`index.html:18398`), `getLocalSide()` (`index.html:928` — PvP only: `isHost ? 'left' : 'right'`; in singles `isHost` is stale, so singles must hard-code `'left'`).
- Produces: nothing new — same function, now live in singles.

- [ ] **Step 1: Reproduce the bug (verify it exists before touching code)**

Run: `./play.command` (or `python3 -m http.server 8000` and open `http://localhost:8000/?dev`). Start a single-player match. Press Space to parry, let the window expire, wait out the cooldown.

Expected: the Parry slot in the ability bar stays visually static through the whole cycle (never shows active/cooldown/ready transitions), while the in-world parry bubble VFX still appears. That's the bug.

- [ ] **Step 2: Apply the fix**

At `index.html:18414`, the function currently reads:

```js
        function syncLocalParryUI() {
            if (gameMode !== 'pvp' || isResimulating) return;
            const localSide = getLocalSide();
            const state = getPvPParryState(localSide);
```

Replace those four lines with:

```js
        function syncLocalParryUI() {
            // Runs for BOTH sim-driven modes. PvP: host=left, guest=right. Singles: the human
            // is always the LEFT combatant (isHost is stale outside PvP — do not use it here).
            if (isResimulating) return;
            if (gameMode !== 'pvp' && gameMode !== 'single') return;
            const localSide = (gameMode === 'pvp') ? getLocalSide() : 'left';
            const state = getPvPParryState(localSide);
```

Everything after (the `state.active` / cooldown / ready branches) stays byte-identical.

- [ ] **Step 3: Verify the fix**

Reload, start a fresh single-player match, run a full parry cycle (press Space → let it expire → wait out cooldown → parry again and connect one).

Expected: the Parry slot now animates — active state during the window, cooldown sweep after, back to ready. Confirm PvP is unregressed: host+join two tabs (`http://localhost:8000/?dev` twice), start a match, parry on each side — each client's button reflects its OWN parry only.

- [ ] **Step 4: Confirm sim untouched**

In a fresh single-player match console: `dbg.determinism(180, 12345)`.
Expected: the golden hash pinned in the `js/sim.js` header comment. (This change is HUD-read-only; any other result means something else is wrong — stop and investigate.)

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "Fix parry-button HUD static in singles: syncLocalParryUI now runs for gameMode 'single' (audit #9)"
```

---

### Task 2: Desync gets a player-facing consequence (audit #3)

Today a confirmed hash desync produces a `console.warn` and a ❌ in the dev-only F2 overlay — a public playtester sees nothing and plays out a divergent, meaningless match. Minimum viable consequence per the audit: a player-facing signal plus a clean abort. We reuse the existing disconnect overlay + teardown (`handleDisconnect`, `index.html:16902` — shows the acknowledge overlay, resets to menu), and tell the peer to do the same so both clients abort together.

Detection nuance: `mpSync.mismatches` only increments when an *earlier* divergent frame is found (`mpCompareHash`, `index.html:17219` keeps the EARLIEST divergence), so it is NOT a usable "still desynced" counter. We add a `badStreak` counter: +1 on every mismatched compare, reset to 0 on every matching compare. Hash compares happen every `MP_SYNC_INTERVAL` frames, and a real desync never re-syncs (audit: `lastOkFrame` stayed `-1` for thousands of frames), so a streak of 3 ≈ one second of confirmed divergence — enough to never fire on a transient while feeling immediate to the player.

**Files:**
- Modify: `index.html:17111` (the `mpSync` literal — add `badStreak`)
- Modify: `index.html:17219-17235` (function `mpCompareHash` — maintain streak, trigger abort)
- Modify: `index.html:17654-17655` (the per-match `mpSync` reset block — reset new fields)
- Modify: `index.html:16967` (the `handleNetworkMessage` switch — add `DESYNC_ABORT` case)

**Interfaces:**
- Consumes: `handleDisconnect(reason)` (`index.html:16902`), `conn` (PeerJS DataConnection), `gameMode`.
- Produces: network message `{ type: 'DESYNC_ABORT', frame: <number> }`; function `abortOnDesync(frame)`; state `mpSync.badStreak` (number), `mpDesyncAborted` (boolean, module-scope `let`).

- [ ] **Step 1: Verify current behavior (detector fires, nothing happens)**

Two tabs at `http://localhost:8000/?dev`, host + join, start a match. In one tab's console: `dbg.forceDesync()` (nudges the local RNG seed — the detector must flip to ❌ within ~20 frames; this is the sanity path the audit used).

Expected today: `[MP DESYNC]` warning in console, F2 overlay shows ❌, **match keeps playing on both clients**. That's the gap.

- [ ] **Step 2: Add the streak field to the mpSync literal**

At `index.html:17111`:

```js
        const mpSync = { local: {}, remote: {}, localGroups: {}, detailSent: {}, lastOkFrame: -1, desync: null, mismatches: 0, rollbacks: 0, lastRollback: 0 };
```

becomes:

```js
        const mpSync = { local: {}, remote: {}, localGroups: {}, detailSent: {}, lastOkFrame: -1, desync: null, mismatches: 0, badStreak: 0, rollbacks: 0, lastRollback: 0 };
```

- [ ] **Step 3: Maintain the streak and trigger the abort in mpCompareHash**

At `index.html:17219`, the function currently reads:

```js
        function mpCompareHash(frame, remoteHash) {
            const local = mpSync.local[frame];
            if (local === undefined) { mpSync.remote[frame] = remoteHash; return; }  // we're behind; compare later
            if (local === remoteHash) {
                if (frame > mpSync.lastOkFrame) mpSync.lastOkFrame = frame;
            } else if (!mpSync.desync || frame < mpSync.desync.frame) {
```

Replace with (note: the streak updates on EVERY compare, outside the earliest-divergence bookkeeping):

```js
        // A real desync never heals (the peers' states have genuinely diverged), so N consecutive
        // mismatched hash exchanges ≈ N * MP_SYNC_INTERVAL frames of confirmed divergence. 3 keeps
        // it transient-proof while still aborting within ~a second of real divergence.
        const DESYNC_ABORT_STREAK = 3;

        function mpCompareHash(frame, remoteHash) {
            const local = mpSync.local[frame];
            if (local === undefined) { mpSync.remote[frame] = remoteHash; return; }  // we're behind; compare later
            if (local === remoteHash) {
                if (frame > mpSync.lastOkFrame) mpSync.lastOkFrame = frame;
                mpSync.badStreak = 0;
            } else if (++mpSync.badStreak >= DESYNC_ABORT_STREAK) {
                abortOnDesync(frame);
            }
            if (local !== remoteHash && (!mpSync.desync || frame < mpSync.desync.frame)) {
```

The body of that final branch (mismatches++, record earliest desync, console.warn, `mpSendDetail`) stays byte-identical; only the branch condition line changed from `} else if (!mpSync.desync || frame < mpSync.desync.frame) {` to the `if (local !== remoteHash && ...)` form above (it is no longer an `else` — the streak `else if` consumed that position).

Then add, directly after the closing brace of `mpCompareHash`:

```js
        // Desync consequence (audit #3): a confirmed, sustained hash divergence ends the match
        // cleanly on BOTH peers instead of silently playing out two different games. Reuses the
        // disconnect overlay + teardown; the DESYNC_ABORT message makes the peer abort too
        // (their own streak would also fire, but the message makes it immediate and symmetric).
        let mpDesyncAborted = false;
        function abortOnDesync(frame) {
            if (mpDesyncAborted || gameMode !== 'pvp') return;
            mpDesyncAborted = true;
            console.warn('[MP DESYNC] aborting match: sustained divergence since frame ' +
                         (mpSync.desync ? mpSync.desync.frame : frame));
            if (conn && conn.open) {
                try { conn.send({ type: 'DESYNC_ABORT', frame: frame }); } catch (e) {}
            }
            handleDisconnect('Match lost sync — please rematch');
        }
```

- [ ] **Step 4: Reset the new state at match start**

At `index.html:17654-17655` (the existing per-match reset block):

```js
            mpSync.local = {}; mpSync.remote = {}; mpSync.localGroups = {}; mpSync.detailSent = {}; mpSync.lastOkFrame = -1;
            mpSync.desync = null; mpSync.mismatches = 0; mpSync.rollbacks = 0; mpSync.lastRollback = 0;
```

becomes:

```js
            mpSync.local = {}; mpSync.remote = {}; mpSync.localGroups = {}; mpSync.detailSent = {}; mpSync.lastOkFrame = -1;
            mpSync.desync = null; mpSync.mismatches = 0; mpSync.badStreak = 0; mpSync.rollbacks = 0; mpSync.lastRollback = 0;
            mpDesyncAborted = false;
```

- [ ] **Step 5: Handle the peer's abort message**

In `handleNetworkMessage` (`index.html:16967`), add a case alongside the existing ones (e.g., directly after the `'PING'` case):

```js
                case 'DESYNC_ABORT':
                    console.warn('[MP DESYNC] peer aborted (their frame ' + data.frame + ')');
                    mpDesyncAborted = true;   // don't echo an abort back
                    handleDisconnect('Match lost sync — please rematch');
                    break;
```

- [ ] **Step 6: Verify live**

Two tabs, `?dev`, host + join, start a match, let it run ~2s clean (overlay ✅). Then in one tab: `dbg.forceDesync()`.

Expected: within ~1-2 seconds BOTH tabs show the disconnect overlay reading "Match lost sync — please rematch"; clicking the overlay button returns each to the main menu cleanly (no stuck state, no console errors). Then host + join AGAIN from the same two tabs and confirm a fresh match starts clean (✅ in overlay — proves the reset in Step 4 works).

Also verify no false positives: run one full untouched match (no forceDesync) to a round win — no abort should ever fire.

- [ ] **Step 7: Commit**

```bash
git add index.html
git commit -m "Desync consequence: sustained hash divergence cleanly aborts the match on both peers (audit #3)"
```

---

### Task 3: GAME_VERSION + one-click bug report (audit #6)

A Discord bug report from a stranger is only actionable if it carries version + state. This task adds: a `GAME_VERSION` constant (boot console log + pause-overlay tag), a `window.lastError` recorder on the existing global error hook, `dbg.report()` bundling everything into one JSON blob, and a "Copy Bug Report" button in the pause overlay (available to players without `?dev`).

**Files:**
- Modify: `index.html:656-663` (existing `window.onerror` — record `window.lastError`, add `unhandledrejection`)
- Modify: `index.html:~665` (add `GAME_VERSION` const + boot log, right after the error hook)
- Modify: `index.html:~17340` (the `dbg` object — add `report()`; `copyBugReport` helper next to it)
- Modify: `index.html:15714-15731` (function `ensurePauseOverlay` — button + version tag)

**Interfaces:**
- Consumes: `captureGameState()` (`index.html:17798` area), `mpSync`, `window.perfLog` (`index.html:12613`), `gameMode`, `isHost`, `currentFrame`, `netPing`.
- Produces: `const GAME_VERSION` (string, module scope — visible to all inline code), `window.lastError` (object or undefined), `dbg.report()` → JSON string, `window.copyBugReport()` → Promise<boolean> (true = clipboard, false = console fallback).

- [ ] **Step 1: Verify the gap**

Console on a running game: `typeof GAME_VERSION` → `"undefined"`, `window.lastError` → `undefined`, `dbg.report` → `undefined` (with `?dev`). Pause menu (Esc) has three buttons and no version tag.

- [ ] **Step 2: Version constant + error recorder**

At `index.html:656`, the block currently reads:

```js
        // Global error handler to debug doubles crash
        window.onerror = function(msg, url, lineNo, columnNo, error) {
            console.error('=== CRASH DEBUG ===');
            console.error('Message:', msg);
            console.error('Line:', lineNo, 'Column:', columnNo);
            console.error('Stack:', error && error.stack);
            console.error('===================');
            return false;
        };
```

Replace with:

```js
        // Build identifier for bug reports (audit #6). Date-based: bump on every player-facing
        // release (itch upload). Logged at boot, shown in the pause menu, embedded in dbg.report().
        const GAME_VERSION = '2026.07.12';
        console.log('%cVolleybolt ' + GAME_VERSION, 'color:#f0c050;font-weight:bold');

        // Global error handler to debug doubles crash + last-error capture for bug reports
        window.onerror = function(msg, url, lineNo, columnNo, error) {
            window.lastError = { msg: String(msg), line: lineNo, col: columnNo,
                                 stack: error && error.stack, time: new Date().toISOString() };
            console.error('=== CRASH DEBUG ===');
            console.error('Message:', msg);
            console.error('Line:', lineNo, 'Column:', columnNo);
            console.error('Stack:', error && error.stack);
            console.error('===================');
            return false;
        };
        window.addEventListener('unhandledrejection', (e) => {
            window.lastError = { msg: 'unhandledrejection: ' + (e.reason && e.reason.message || e.reason),
                                 stack: e.reason && e.reason.stack, time: new Date().toISOString() };
        });
```

- [ ] **Step 3: dbg.report() + copyBugReport()**

In the `dbg` object (`index.html:~17330`, alongside `state()` / `sync()`), add:

```js
            // One-paste bug report: everything needed to act on a stranger's Discord report.
            // Babylon objects (mesh/particles/paddle) are stripped — they're circular and huge.
            report() {
                const r = {
                    version: GAME_VERSION,
                    time: new Date().toISOString(),
                    ua: navigator.userAgent,
                    mode: gameMode, isHost, frame: currentFrame, ping: netPing,
                    sync: { lastOkFrame: mpSync.lastOkFrame, mismatches: mpSync.mismatches,
                            desync: mpSync.desync, rollbacks: mpSync.rollbacks },
                    lastError: window.lastError || null,
                    perfTail: (window.perfLog || []).slice(-20),
                    state: (typeof captureGameState === 'function') ? captureGameState() : null,
                };
                const seen = new WeakSet();
                return JSON.stringify(r, (k, v) => {
                    if (k === 'mesh' || k === 'particles' || k === 'paddle' || typeof v === 'function') return undefined;
                    if (v && typeof v === 'object') { if (seen.has(v)) return undefined; seen.add(v); }
                    return v;
                });
            },
```

Directly after the `dbg` object's closing statement, add:

```js
        // Player-facing (no ?dev needed): pause-menu "Copy Bug Report" lands here.
        // window.dbg is defined unconditionally (the ?dev flag only gates the debug UI),
        // so report() is always available.
        // Resolves true if the blob reached the clipboard, false if it fell back to the console.
        window.copyBugReport = () => {
            let blob;
            try { blob = window.dbg.report(); }
            catch (e) { blob = JSON.stringify({ version: GAME_VERSION, reportError: String(e), lastError: window.lastError || null }); }
            if (navigator.clipboard && navigator.clipboard.writeText) {
                return navigator.clipboard.writeText(blob).then(() => true, () => { console.log('[bug report]', blob); return false; });
            }
            console.log('[bug report]', blob);
            return Promise.resolve(false);
        };
```

(Verified 2026-07-12: `window.dbg = {` at `index.html:17319` is unconditional — no `?dev` gate on the object itself.)

- [ ] **Step 4: Pause overlay button + version tag**

In `ensurePauseOverlay` (`index.html:15714`), the `ov.innerHTML` string currently ends:

```js
                '<button id="pauseQuitBtn" class="game-btn menu-btn" style="display:block;width:240px;margin:10px auto">Quit to Menu</button>' +
                '</div>';
```

Replace with:

```js
                '<button id="pauseQuitBtn" class="game-btn menu-btn" style="display:block;width:240px;margin:10px auto">Quit to Menu</button>' +
                '<button id="pauseBugBtn" class="game-btn menu-btn" style="display:block;width:240px;margin:10px auto">Copy Bug Report</button>' +
                '<div style="color:#8a93a6;font-size:12px;margin-top:14px">v' + GAME_VERSION + '</div>' +
                '</div>';
```

And after the existing `pauseQuitBtn` listener, add:

```js
            ov.querySelector('#pauseBugBtn').addEventListener('click', () => {
                const btn = ov.querySelector('#pauseBugBtn');
                window.copyBugReport().then((toClipboard) => {
                    btn.textContent = toClipboard ? 'Copied!' : 'Printed to console';
                    setTimeout(() => { btn.textContent = 'Copy Bug Report'; }, 1500);
                });
            });
```

- [ ] **Step 5: Verify**

1. Reload (NO `?dev`): console shows the gold `Volleybolt 2026.07.12` boot line.
2. Start a singles match, press Esc: pause menu shows the new button + `v2026.07.12` tag.
3. Click "Copy Bug Report" → button flips to "Copied!" → paste into a text editor → valid JSON containing `version`, `ua`, `mode`, `state` (with combatants/projectiles, no `mesh` keys).
4. In console: `JSON.parse(window.lastError === undefined ? 'null' : '0') // no-op sanity` — then force an error: `setTimeout(() => { throw new Error('probe'); })`, wait a tick, check `window.lastError.msg` contains `'probe'`, and a fresh copied report contains it too.
5. With `?dev`: `dbg.report()` returns the same JSON string.
6. PvP smoke: host+join, mid-match Esc → copy → blob's `sync` block present, `mode: "pvp"`.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "GAME_VERSION + one-click bug report: dbg.report(), lastError capture, pause-menu copy button (audit #6)"
```

---

### Task 4: Join-attempt timeout message (audit #7 residual)

"Room not found" and disconnects are already handled (`peer.on('error')`, `index.html:16824`). The remaining hole: a join where WebRTC/NAT traversal silently hangs — no error fires, the joiner stares at "Connecting..." forever and can't distinguish it from a slow host. Fix: a 15-second timer on the join attempt; if the DataConnection hasn't opened, show an actionable message and clean up.

**Files:**
- Modify: `index.html:16316-16325` (the `connectJoinHandler` in the lobby wiring)
- Modify: `index.html:16842` area (`setupConnection`'s `conn.on('open')` — clear the timer)
- Modify: `index.html:16824-16836` (`peer.on('error')` — clear the timer so "Room not found" isn't later overwritten)
- Modify: `index.html:16889` area (`cleanupPeer` — clear the timer)

**Interfaces:**
- Consumes: `initializePeer(id, code)`, `cleanupPeer()` (`index.html:16889`), `conn`, the `joinStatus` DOM label.
- Produces: module-scope `let joinAttemptTimer = null;` and `function clearJoinAttemptTimer()` — called from the three sites above.

- [ ] **Step 1: Reproduce the hang**

Open `http://localhost:8000/`, Join Game, enter a well-formed code for a room that was hosted and then closed mid-handshake — or simpler: host in tab A, kill tab A entirely, then join its code from tab B *after* the PeerJS broker has dropped it... if that yields `peer-unavailable` ("Room not found"), the true repro is network-level: join a code hosted from a device on a network that blocks WebRTC. If no easy repro is available, verify the gap statically: nothing in `connectJoinHandler` or `initializePeer` bounds the wait — "Connecting..." can persist forever.

- [ ] **Step 2: Add the timer**

Directly above `const connectJoinHandler = () => {` (`index.html:16316`), add:

```js
            // Join-attempt watchdog (audit #7): WebRTC NAT-traversal failure often fires NO error —
            // the connection just never opens. Bound the wait so the player gets an actionable
            // message instead of an eternal "Connecting...".
            let joinAttemptTimer = null;
            const JOIN_TIMEOUT_MS = 15000;
            window.clearJoinAttemptTimer = () => {
                if (joinAttemptTimer) { clearTimeout(joinAttemptTimer); joinAttemptTimer = null; }
            };
```

And inside `connectJoinHandler`, the success branch currently reads:

```js
                if (code.length >= 4) {
                    isHost = false;
                    if (joinStatus) joinStatus.textContent = 'Connecting...';
                    initializePeer(null, code.toLowerCase());
                } else {
```

becomes:

```js
                if (code.length >= 4) {
                    isHost = false;
                    if (joinStatus) joinStatus.textContent = 'Connecting...';
                    initializePeer(null, code.toLowerCase());
                    // Arm AFTER initializePeer: its first act is cleanupPeer(), which clears this
                    // timer — arming first would self-cancel the watchdog in the same tick.
                    window.clearJoinAttemptTimer();
                    joinAttemptTimer = setTimeout(() => {
                        joinAttemptTimer = null;
                        if (conn && conn.open) return;   // opened after all — never overwrite a live lobby
                        cleanupPeer();
                        if (joinStatus) joinStatus.textContent =
                            "Couldn't reach the host — a firewall or network may be blocking peer-to-peer. " +
                            "Both players trying a different network (a phone hotspot often works) usually fixes it.";
                    }, JOIN_TIMEOUT_MS);
                } else {
```

- [ ] **Step 3: Clear the timer on every resolution path**

`window.clearJoinAttemptTimer` is exposed on `window` because the three call sites live in a different closure scope than the lobby wiring. Guard each call with existence (`if (window.clearJoinAttemptTimer) window.clearJoinAttemptTimer();`):

1. `setupConnection`'s `conn.on('open', ...)` (`index.html:16842`) — first line of the handler (success path).
2. `peer.on('error', ...)` (`index.html:16824`) — first line of the handler (so "Room not found. Check the code." stands and isn't replaced 15s later by the timeout text).
3. `cleanupPeer()` (`index.html:16889`) — first line (leaving the lobby cancels the watchdog).

- [ ] **Step 4: Verify**

1. Happy path: host tab A, join from tab B → connects normally; wait 20s in the lobby → status does NOT get overwritten by the timeout message (timer was cleared on open).
2. Room not found: join a garbage code (e.g. `ZZZZ9`) → "Room not found. Check the code." appears and STAYS (wait 20s to confirm no overwrite).
3. Timeout path: in DevTools on the join tab, set network to Offline AFTER the page loads, then join a well-formed code. Expected within ~15s (broker errors may surface a different message first — `network` type errors route to handleDisconnect; if so, throttle to a blocked-WebRTC profile instead or accept the static check from Step 1): the timeout message appears and the lobby returns to a re-attemptable state (entering a code and pressing Connect again works).
4. Back out of the join view mid-attempt (Back button → `cleanupPeer`) → no message appears later.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "Join-attempt watchdog: 15s timeout with actionable NAT/firewall message instead of eternal 'Connecting...' (audit #7)"
```

---

## Final verification (after all tasks)

- [ ] Fresh single-player match with `?dev`: `dbg.determinism(180, 12345)` equals the golden pinned in the `js/sim.js` header (sim untouched by this whole plan).
- [ ] `git diff master --stat` shows only `index.html` (plus this plan file) changed.
- [ ] Full manual smoke: singles match start→round win, PvP host+join+play+quit, pause menu in both modes.
