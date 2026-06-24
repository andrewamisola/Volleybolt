# Game Lifecycle, Camera & Multiplayer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the boot→menu→match→end lifecycle around one explicit state machine with a single authoritative match-build/teardown path, a fixed shared-world camera, a 2D menu with no 3D camera, an Esc pause menu, and a lean multiplayer host/join lobby — eliminating the off-angle-camera, stale-end-scene, and module-crash bugs.

**Architecture:** Strangler refactor inside the existing inline `index.html`. Introduce one `GameSM` controller (plain inline object) that owns state + transitions; migrate the scattered soft-reset functions into `startMatch()`/`endMatch()` incrementally so the game stays playable after every task. The 3D engine loads assets once at boot and idles behind a 2D DOM menu; each match is a fresh canonical build.

**Tech Stack:** Vanilla JS, Babylon.js (CDN), Babylon GUI + DOM/CSS UI, PeerJS (P2P multiplayer), Tone.js (audio). No bundler, no test framework — verification is via the running game in a browser / Playwright.

## Global Constraints

- All changes go in `C:\Users\andre\Volleybolt\index.html` unless a task says otherwise. It is one inline `<script>` monolith; add new code near related existing code, matching surrounding style.
- The game must remain launchable and playable after every task (strangler order). Never leave it in a non-booting state between commits.
- Serve via `python -m http.server 8000`; the browser caches `index.html` aggressively — **hard-refresh (Ctrl+Shift+R) or append `?cb=<tag>`** when verifying.
- Verification = manual/Playwright in-game checks (no unit tests). Each task ends with a concrete observable check.
- Do NOT touch the pickle character/animation code (`loadPickleWizard`, `models/pickle/`, material treatment) — that work is landed and out of scope.
- Camera model is fixed: one camera, one wide-shot pose, shared world (host/P1 = left, guest/P2 = right). No menu camera, no per-client mirroring.
- Single-player starts at **midfield** (current `currentStage = 2`).
- Commit after each task with a clear message.

---

## Task 1: Remove dead `js/` module scripts (kill the crash + 404)

**Files:**
- Modify: `index.html:409-415` (the `<script type="module">` block)

**Interfaces:**
- Consumes: nothing.
- Produces: a clean console (no ES-module SyntaxError, no `ability-registry.js` 404). No functional change to the game (these modules are diagnostic-only; `main.js` already crashes today yet the game runs).

- [ ] **Step 1: Confirm the modules are unused.** Search the inline script for any reference to the module exports being read from the module scope (there are none — the inline game defines its own `updateGravityUI`, etc.). Confirm `js/main.js` header says "game initialization still runs from index.html".

Run: `grep -n 'type="module"' index.html`
Expected: lines 409–415 listing game-config, ability-registry, audio-system, ui-system, rendering-utils, game-systems, main.

- [ ] **Step 2: Comment out the module block.** Replace lines 409–415 with a single explanatory comment so intent is preserved:

```html
<!-- Removed: half-finished js/ module extraction. main.js is diagnostic-only and the
     game runs entirely from the inline script below. These tags caused a hard ES-module
     crash (ui-system.js has no updateGravityUI export) + a 404 (ability-registry.js missing).
     See docs/superpowers/specs/2026-06-24-game-lifecycle-camera-multiplayer-design.md -->
```

- [ ] **Step 3: Verify in-game.** Serve and hard-refresh `http://localhost:8000/index.html?cb=t1`. Open console.
Expected: NO "does not provide an export named 'updateGravityUI'" error and NO `ability-registry.js` 404. Title screen still loads; Start Battle still works.

- [ ] **Step 4: Commit.**

```bash
git add index.html
git commit -m "fix: remove dead js/ module scripts (kills module crash + 404)"
```

---

## Task 2: Add the `GameSM` state controller (delegating shell)

Introduce the controller that will own all transitions. In this task it only *wraps* existing behavior so nothing changes yet — later tasks move logic into it.

**Files:**
- Modify: `index.html` — add an inline `GameSM` object near the top of the main game `<script>` (after the core globals like `gameOver`/`gameState` are declared; place it just before `function startGame()` ~line 14307 so it can reference existing functions via hoisting/closure).

**Interfaces:**
- Produces:
  - `GameSM.state` — one of `'boot' | 'menu' | 'match' | 'pause' | 'gameover' | 'lobby'`.
  - `GameSM.to(next, opts)` — transition entrypoint; logs `[SM] <from> -> <next>` and dispatches to the matching `enter*` handler.
  - `GameSM.enterMenu()`, `GameSM.startMatch(opts)`, `GameSM.endMatch()`, `GameSM.enterPause()`, `GameSM.resumeMatch()`, `GameSM.enterGameOver(result)`, `GameSM.enterLobby()` — in this task each simply calls the existing function it will eventually replace (see mapping), so behavior is unchanged.
- Consumes: existing `showTalentScreen`, `startGame`, `returnToMenuTransition`, `showVictoryScreen`, `showMultiplayerLobby`.

- [ ] **Step 1: Add the controller (delegating).** Insert:

```js
// === GAME STATE MACHINE (strangler: delegates to legacy fns; logic migrates in over later tasks) ===
const GameSM = {
    state: 'boot',
    to(next, opts) {
        console.log(`[SM] ${this.state} -> ${next}`);
        this.state = next;
        switch (next) {
            case 'menu':     return this.enterMenu(opts);
            case 'match':    return this.startMatch(opts);
            case 'pause':    return this.enterPause(opts);
            case 'gameover': return this.enterGameOver(opts);
            case 'lobby':    return this.enterLobby(opts);
        }
    },
    enterMenu()        { showTalentScreen(true); },          // legacy menu setup
    startMatch(opts)   { startGame(); },                      // legacy match start
    endMatch()         { returnToMenuTransition(); },         // legacy end->menu
    enterPause()       { /* implemented in Task 7 */ },
    resumeMatch()      { /* implemented in Task 7 */ },
    enterGameOver(r)   { showVictoryScreen(r === 'victory'); },
    enterLobby()       { if (window.showMultiplayerLobby) showMultiplayerLobby(); },
};
window.GameSM = GameSM;
```

- [ ] **Step 2: Verify it loads.** Hard-refresh `?cb=t2`, console: type `GameSM.state` → `"boot"`. No errors. Game still works exactly as before (nothing routes through GameSM yet).

- [ ] **Step 3: Commit.**

```bash
git add index.html
git commit -m "feat: add GameSM state controller (delegating shell)"
```

---

## Task 3: Make the MENU pure 2D (no 3D camera behind it)

Root-fix for the off-angle camera: while in menu, the 3D scene/canvas is hidden and the render loop skips 3D, so there is no menu camera to drift. The existing DOM menu backdrop becomes the only thing shown.

**Files:**
- Modify: `index.html` — the render loop (`engine.runRenderLoop`, ~line 4253 area) and `showTalentScreen` (~14172) / the menu-show path.
- Read first: how the Babylon `<canvas>` and the DOM menu (`#domMenu`/`setDOMMenuVisible`) are layered (search `setDOMMenuVisible`, the canvas element id).

**Interfaces:**
- Consumes: `GameSM.state`, the Babylon canvas element, `setDOMMenuVisible`.
- Produces: `GameSM.show3D(visible)` — toggles canvas visibility; while `state==='menu'` the render loop early-returns (or renders a cleared frame) so no 3D shows.

- [ ] **Step 1: Add a 3D visibility helper.** In `GameSM`:

```js
show3D(visible) {
    const c = engine.getRenderingCanvas();
    if (c) c.style.visibility = visible ? 'visible' : 'hidden';
},
```

- [ ] **Step 2: Gate the render loop.** In the `runRenderLoop` callback, skip scene rendering while in menu (keep the loop alive for timing):

```js
engine.runRenderLoop(() => {
    if (GameSM.state === 'menu' || GameSM.state === 'boot') { return; }  // 2D menu owns the screen
    // ... existing scene.render() and per-frame game logic ...
});
```

- [ ] **Step 3: Hide 3D + show DOM menu on menu entry.** In `enterMenu()` (currently delegating to `showTalentScreen(true)`), after the legacy call add `this.show3D(false);`. Ensure `setDOMMenuVisible(true)` runs (it already does inside `showTalentScreen`).

- [ ] **Step 4: Verify.** Hard-refresh `?cb=t3`. At the title/menu, the 3D arena must NOT be visible behind the menu (no off-angle scene). Click Start Battle → 3D arena appears. Win/lose → Continue → back to menu → 3D hidden again.
Expected: menu shows only the 2D backdrop; no 3D camera angle visible at any menu.

- [ ] **Step 5: Commit.**

```bash
git add index.html
git commit -m "feat: menu is 2D-only; hide 3D + skip render in menu (fixes off-angle camera)"
```

---

## Task 4: Implement authoritative `startMatch(opts)`

Consolidate the fresh-build into one function. Reuse the proven pieces from `startGame` (14308) + `resetGame` (16645) + the match-relevant parts of `resetRound` (16692), plus an explicit camera set.

**Files:**
- Modify: `index.html` — replace `GameSM.startMatch` body; read `startGame` (14308–~14400), `resetGame` (16645), `resetRound` (16692) to harvest the exact reset lines.

**Interfaces:**
- Consumes: `resetGame()` internals (scores, `currentStage=2`, gate arrays), `resetRound()` (combatant reset, gate rebuild via `resetBricks`), `startRound()`, `doReadyGoTransition`, the gameplay-UI-show block from `startGame`.
- Produces: `GameSM.startMatch(opts)` with `opts = { mode:'single'|'pvp', role?, seed?, upgrade? }`. Sets `GameSM.state='match'`, `gameState='playing'`, builds fresh state, shows 3D + gameplay UI, sets the fixed camera (camera pose finalized in Task 6 — for now reuse the gameplay camera pose `startGame` already lands on).

- [ ] **Step 1: Write `startMatch`.** Move the body of `startGame()` into `GameSM.startMatch(opts)`, parameterizing mode. Key sequence (harvest exact lines from `startGame`): guard → black transition overlay on → `this.show3D(true)` → `resetGame()` (fresh scores/stage/gates/talents + `resetRound`) → `doReadyGoTransition(() => { gameState='playing'; GameSM.state='match'; startRound(); /* show gameplay UI block from startGame 14352-14366 */ })`. For `opts.mode==='pvp'`, seed RNG and set role before `startRound` (mirror existing `startMultiplayerMatch`).

- [ ] **Step 2: Route Start Battle through it.** Find the `#domBtnStartBattle` click handler (search `domBtnStartBattle`, ~14827) and change it to call `GameSM.to('match', { mode:'single' })` instead of `startGame()`.

- [ ] **Step 3: Keep `startGame` as a thin alias** (so other callers don't break yet): `function startGame(){ GameSM.to('match', { mode:'single' }); }` — or leave the original and have `startMatch` call into the harvested code. Pick one; ensure no double-execution.

- [ ] **Step 4: Verify.** Hard-refresh `?cb=t4`. Start Battle → match starts at **midfield**, gates full, scores 0-0, idle pickles, gameplay UI shown. Play a point.
Expected: identical to before, but now via `GameSM.startMatch`. Console shows `[SM] menu -> match`.

- [ ] **Step 5: Commit.**

```bash
git add index.html
git commit -m "feat: authoritative GameSM.startMatch() (single fresh-build path)"
```

---

## Task 5: Implement authoritative `endMatch()` + route Continue through it

**Files:**
- Modify: `index.html` — `GameSM.endMatch`, the `continueBtn.onPointerClickObservable` (4933), the gate-victory path that calls `showVictoryScreen` (18424/18457).

**Interfaces:**
- Consumes: `hideVictoryScreen()`, `enterMenu()` (which now hides 3D), the cast-UI force-hide block from `returnToMenuTransition` (14522-14536).
- Produces: `GameSM.endMatch()` — stops the match, hides gameplay UI + victory overlay + 3D, returns to MENU. Idempotent.

- [ ] **Step 1: Write `endMatch`.** Body: stop round/sim flags (`roundActive=false; gameOver=false; gameState='menu'`), `hideVictoryScreen()`, force-hide cast bars (harvest 14522-14536), `clearAllProjectiles?.()`, then `this.to('menu')` (which runs `enterMenu` → legacy menu setup + `show3D(false)`). Wrap the camera/scene visibility swap so it happens under the existing black transition overlay (reuse `returnToMenuTransition`'s fade if present).

- [ ] **Step 2: Route Continue.** Change `continueBtn.onPointerClickObservable` (4933) from `returnToMenuTransition()` to `GameSM.endMatch()`.

- [ ] **Step 3: Route gate-victory.** At 18424 & 18457, after `showVictoryScreen(localWon)`, ensure `GameSM.state='gameover'` (so render loop still renders the frozen scene — it does, since gameover ≠ menu). No teardown here; teardown happens on Continue.

- [ ] **Step 4: Verify the original bug is fixed.** Hard-refresh `?cb=t5`. Play to victory or defeat → Continue → land on the **2D menu (no 3D, no off-angle camera, no stale end-scene)** → Start Battle again → **fresh match at midfield** (not the end scene).
Expected: the reported bug is gone; repeat 2–3 times to confirm no drift.

- [ ] **Step 5: Commit.**

```bash
git add index.html
git commit -m "feat: authoritative GameSM.endMatch(); fix stale end-scene on Continue"
```

---

## Task 6: Lock the camera to one fixed wide-shot pose

Remove the menu-camera animation entirely; the camera only ever sits at the gameplay wide-shot pose, set explicitly in `startMatch`.

**Files:**
- Modify: `index.html` — `showTalentScreen` camera block (14216-14244), `startMatch` (camera set), search `MENU_CAMERA`, `setOrthoForMenu`, `window.gameCamera`.

**Interfaces:**
- Consumes: `window.gameCamera`, the existing gameplay camera pose constants.
- Produces: `GameSM.setGameplayCamera()` — sets `gameCamera` alpha/beta/radius/target to the fixed wide-shot gameplay pose (capture the current in-match values). Called at the end of `startMatch`.

- [ ] **Step 1: Capture the gameplay pose.** In the running in-match game, read `gameCamera.alpha/beta/radius/target` and record them as constants `GAMEPLAY_CAMERA = {alpha, beta, radius, target:{x,y,z}}`.

- [ ] **Step 2: Add `setGameplayCamera()`** to `GameSM` that snaps `gameCamera` to `GAMEPLAY_CAMERA` (instant; no animation). Call it inside `startMatch` after `show3D(true)`.

- [ ] **Step 3: Delete the menu-camera path.** In `showTalentScreen`, remove the camera animation block (14216-14244) and any `setOrthoForMenu`/`MENU_CAMERA` menu-move calls — the menu no longer shows 3D, so no menu camera is needed.

- [ ] **Step 4: Verify.** Hard-refresh `?cb=t6`. Every match starts at the identical fixed wide shot; menu shows no 3D; no off-angle pose ever appears. Win → Continue → Start again → same exact framing.

- [ ] **Step 5: Commit.**

```bash
git add index.html
git commit -m "feat: single fixed gameplay camera; remove menu-camera path"
```

---

## Task 7: Esc pause / in-game menu

**Files:**
- Modify: `index.html` — `GameSM.enterPause`/`resumeMatch`, add an Esc keydown handler, add a pause overlay (reuse the victory-overlay GUI pattern at 4850 or a DOM overlay).

**Interfaces:**
- Consumes: `GameSM.state`, `GameSM.endMatch()`, the round/sim pause flags (`roundTransitioning` or a new `paused` flag), `gameMode`.
- Produces: `GameSM.enterPause()` (overlay on; single-player sets `paused=true` to freeze sim), `GameSM.resumeMatch()` (overlay off; `paused=false`). Pause overlay buttons: **Resume** → `resumeMatch()`; **Quit/Leave** → `endMatch()`.

- [ ] **Step 1: Add a `paused` flag** and gate the per-frame match logic on it in the render loop (only when `state==='match'` and `!paused`). Multiplayer must NOT set `paused` (can't pause a peer).

- [ ] **Step 2: Build the pause overlay.** Add a GUI/DOM overlay (clone the victory-overlay structure) with title "Paused", a Resume button, and a Quit-to-Menu (SP) / Leave-Match (MP) button.

- [ ] **Step 3: Wire Esc.** In the global keydown handler, if `GameSM.state==='match'` → `GameSM.to('pause')`; if `state==='pause'` → `GameSM.resumeMatch()`.

- [ ] **Step 4: Implement handlers.** `enterPause()`: show overlay; `if (gameMode!=='pvp') paused=true;`. `resumeMatch()`: hide overlay; `paused=false; GameSM.state='match';`. Quit button → `GameSM.endMatch()`. MP Leave → send `LEAVE` (existing) then `endMatch()`.

- [ ] **Step 5: Verify.** Hard-refresh `?cb=t7`. In a single-player match press Esc → sim freezes, overlay shows; Resume → continues; Esc → Quit → clean 2D menu (fresh match on restart). (MP path verified in Task 8.)

- [ ] **Step 6: Commit.**

```bash
git add index.html
git commit -m "feat: Esc pause/in-game menu (Resume / Quit) via endMatch"
```

---

## Task 8: Multiplayer through the state machine + remove mirroring

**Files:**
- Modify: `index.html` — `showMultiplayerLobby`/lobby start, `handleDisconnect` (15096), `START_MATCH` handler (15190), `startMultiplayerMatch`, search/remove `applyClientPerspective`.

**Interfaces:**
- Consumes: existing PeerJS host/join, `START_MATCH` message, `GameSM.startMatch({mode:'pvp', role, seed})`, `GameSM.endMatch()`.
- Produces: host start → `GameSM.startMatch({mode:'pvp', role:'host', seed})` + send `START_MATCH`; guest `START_MATCH` → `GameSM.startMatch({mode:'pvp', role:'guest', seed})`. Disconnect → `GameSM.endMatch()`. No perspective flip (shared world: host left, guest right).

- [ ] **Step 1: Route lobby start.** Where the host currently begins the match (search `startMultiplayerMatch` / the host's start button), call `GameSM.startMatch({mode:'pvp', role:'host', seed})` and emit the existing `START_MATCH` with that seed. In the `START_MATCH` handler (15190), the guest calls `GameSM.startMatch({mode:'pvp', role:'guest', seed:data.seed})`.

- [ ] **Step 2: Remove mirroring.** Delete `applyClientPerspective` calls and the function; ensure both clients use the same `GAMEPLAY_CAMERA` (host left, guest right). Verify input maps to the correct paddle without a flip.

- [ ] **Step 3: Route disconnect.** In `handleDisconnect` (15096), replace the ad-hoc reset (`resetGame`+`showTalentScreen`/overlay) with `GameSM.endMatch()` (after showing the disconnect reason if desired).

- [ ] **Step 4: Verify (two browsers/tabs).** Host creates code; guest joins; both land in the SAME shared-world match (host left, guest right, identical camera). Each controls their own paddle. Esc → Leave → both return cleanly to menu; the remaining peer sees disconnect → menu.

- [ ] **Step 5: Commit.**

```bash
git add index.html
git commit -m "feat: multiplayer via GameSM; shared-world camera; remove mirroring"
```

---

## Task 9: Retire dead soft-reset helpers

**Files:**
- Modify: `index.html` — remove/inline `returnToMenuTransition`, the duplicate `checkWin` legacy path (16525), and any `showTalentScreen` bits no longer used; collapse `startGame` alias if kept.

**Interfaces:**
- Consumes: nothing new.
- Produces: a single lifecycle path through `GameSM`; no orphaned reset functions.

- [ ] **Step 1: Find dead callers.** `grep -n 'returnToMenuTransition\|checkWin\|applyClientPerspective\|MENU_CAMERA\|setOrthoForMenu' index.html` — confirm each remaining reference is unused, then remove the definition + dead references.

- [ ] **Step 2: Keep `showTalentScreen` only if still the menu-setup body** that `enterMenu` calls; otherwise inline its still-needed parts into `enterMenu` and delete the rest.

- [ ] **Step 3: Verify full loop.** Hard-refresh `?cb=t9`. Full regression: boot → menu (2D) → Start → play → Esc/Quit → menu → Start → play → win → Continue → menu → Multiplayer → host/join → match → Leave → menu. No console errors, no off-angle camera, no stale scene.

- [ ] **Step 4: Commit.**

```bash
git add index.html
git commit -m "refactor: remove dead soft-reset helpers; single GameSM lifecycle"
```

---

## Self-review (spec coverage)

- State machine → Tasks 2,4,5,7,8,9. Boot/2D menu → Tasks 3,6. Match lifecycle (startMatch/endMatch) → Tasks 4,5. Camera (fixed, shared world) → Tasks 6,8. Multiplayer (host/join/start, disconnect) → Task 8. Pause menu → Task 7. Module-crash cleanup → Task 1. Mirroring removal + dead-helper retirement → Tasks 8,9. SP starts midfield → Task 4. ✓ All spec sections covered.
- No `pytest` tasks — this codebase has no test framework; each task's verification is an explicit in-game observation (documented per task), consistent with the Global Constraints.
- Type/name consistency: `GameSM.startMatch(opts)`, `endMatch()`, `enterMenu()`, `enterPause()`, `resumeMatch()`, `show3D()`, `setGameplayCamera()`, `GAMEPLAY_CAMERA`, `paused` used consistently across tasks.
- Known read-required spots (harvest exact lines during implementation): `startGame` 14308, `resetGame` 16645, `resetRound` 16692, `returnToMenuTransition` 14479, victory paths 18424/18457, lobby/`handleDisconnect` 15096, render loop ~4253, camera block 14216. These are anchors, not placeholders — the transformation per task is specified.
