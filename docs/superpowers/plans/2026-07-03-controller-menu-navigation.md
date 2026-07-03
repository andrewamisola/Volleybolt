# Controller Menu Navigation + Prompt Bar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every menu screen in Volleybolt becomes fully navigable with a gamepad (D-pad/stick to move focus, a face button to confirm, another to go back), a persistent bottom-right prompt bar shows what's currently doable and swaps between keyboard and controller glyphs live, and the existing in-game ability-bar glyph swap gets verified and fixed if broken.

**Architecture:** One generic navigator (`pollGamepadMenuNav`) polls every frame a menu is open, finds the active screen's focusable elements, and drives a `.gp-focused` class + native `.focus()`/`.click()` — reusing every existing button/slider/checkbox handler unchanged. A second small module (`setGamepadPrompts` + a bottom-right DOM bar) renders whatever the current screen declares as its available actions. Both share one global "last input device" flag with the existing in-game ability bar.

**Tech Stack:** Vanilla JS in `index.html` (no framework, no bundler), `styles.css`, no JS unit-test framework in this repo — verification is `node --check` (syntax) plus live browser testing via Playwright (behavior), matching how every other feature in this codebase has been verified.

## Global Constraints

- All logic lives in `index.html`'s existing inline `<script>` (this codebase is an intentional monolith — see `docs/superpowers/specs/2026-06-27-main-menu-settings-design.md`). Do not split into new files.
- Follow the spec exactly: `docs/superpowers/specs/2026-07-03-controller-menu-navigation-design.md`.
- Button mapping is **index-based** (bottom face button = confirm, right face button = back, Start = index 9), matching the existing `GP` object's philosophy — never branch on vendor for behavior, only for the printed/colored glyph.
- Text inputs (`#setName`, `#joinInput`) are never focusable by the navigator.
- The prompt bar never appears during live gameplay (`gameState === "playing"`) — the ability bar owns that role there.
- After every task: run `node --check` against the extracted inline script (see Task 1's verification command — reuse it verbatim in every task) before moving on.

---

### Task 1: Verify the existing in-game ability-bar glyph swap

**Files:**
- Modify (only if broken): `index.html` — the `pollGamepadInput`/`updateHudInputHints` region (~line 3620–3745)
- Test: manual, via local server + Playwright/real controller

**Interfaces:**
- Consumes: nothing new
- Produces: confirms (or fixes) `updateHudInputHints()` — every later task assumes this already works correctly, since Task 8/9 reuse its `padGlyphHTML` helper

This mechanism already exists and looks correctly wired on paper — verify it actually works in a live match before assuming it's broken.

- [ ] **Step 1: Start the local server and open a fresh single-player match**

```bash
cd ~/Projects/Volleybolt && python3 -m http.server 8000
```

Navigate to `http://localhost:8000`, click through the loading screen, Start Battle.

- [ ] **Step 2: Simulate a gamepad button press without a physical controller**

Real browser automation tools (Playwright/Chrome DevTools) cannot synthesize `Gamepad` API state — the `navigator.getGamepads()` array is read-only and browser-controlled. Verify by directly invoking the code path instead, in the page console:

```js
// Force the HUD into "pad" mode as if button index 0 (bottom face button) was just pressed,
// exactly what pollGamepadInput() does internally on a real press.
_hudInputMode = 'pad';
updateHudInputHints();
document.querySelector('#fireballSlot .ability-key').innerHTML
```

Expected: a `<span class="pgl xb xb-x">X</span>`-style HTML string (or the equivalent for whatever `detectPadType()` currently resolves to with no real pad connected — check `document.querySelector('#fireballSlot .ability-key').textContent` isn't still `"1"`).

- [ ] **Step 3: If Step 2 shows the glyph correctly, confirm the trigger path with a real controller**

Connect a real Xbox controller, get into a match, press any mapped button (X/A/B/Y or move the stick/D-pad). Watch `#fireballSlot .ability-key`, `#frostboltSlot .ability-key`, `#thunderstormSlot .ability-key`, `#parryButton .ability-key` — all four should flip from `1`/`2`/`3`/`Space` to colored button chips within one frame of the press.

- [ ] **Step 4: If Step 3 fails despite Step 2 succeeding, the bug is in `pollGamepadInput`'s detection, not `updateHudInputHints`**

Check in the console during a match with the controller connected:

```js
navigator.getGamepads()[0]  // should be a real Gamepad object, not null, once any button has been touched
```

Browsers only populate `navigator.getGamepads()` after the page has received at least one input event from the pad (a known Gamepad API quirk — connecting a controller alone doesn't populate it; you must press a button first while the tab is focused). If `navigator.getGamepads()[0]` stays `null` after pressing buttons, the issue is browser/OS-level pad detection, not this codebase — note it in the commit message and move on; this task's job is to confirm the code path, not fix OS-level gamepad drivers.

- [ ] **Step 5: If genuinely broken in this codebase's code (Step 2 itself fails), fix and re-verify**

There is no known bug in the current wiring as of this plan's writing — if Step 2 fails, read `pollGamepadInput` (line 3646) and `updateHudInputHints` (line 3724) fully before changing anything, per `superpowers:systematic-debugging`. Do not guess-patch.

- [ ] **Step 6: Run the syntax check**

```bash
cd ~/Projects/Volleybolt && python3 - <<'EOF'
import re, subprocess, tempfile, os
s = re.findall(r'<script(?![^>]*src)[^>]*>(.*?)</script>', open('index.html').read(), re.S)[0]
with tempfile.NamedTemporaryFile('w', suffix='.js', delete=False) as f: f.write(s); p=f.name
r = subprocess.run(['node','--check',p], capture_output=True, text=True)
print('OK' if r.returncode==0 else r.stderr[:1500]); os.unlink(p)
EOF
```

Expected: `OK`. Reuse this exact command after every subsequent task in this plan.

- [ ] **Step 7: Commit (only if Step 5 required a code change; otherwise skip — nothing to commit)**

```bash
git add index.html
git commit -m "Fix in-game ability-bar gamepad glyph swap"
```

---

### Task 2: Extract shared menu/pause handler; add Start button routing

**Files:**
- Modify: `index.html:13620` (the Escape `keydown` listener) and `index.html:3646` (`pollGamepadInput`)

**Interfaces:**
- Consumes: existing `MENU_SCREENS`, `closeMenuScreen()`, `GameSM.state`, `GameSM.enterPause()`, `GameSM.resumeMatch()` — all unchanged
- Produces: `handleMenuOrPauseToggle()` — a new global function; later tasks (Task 4's navigator) do not call this directly, but it establishes the pattern of "one shared function, multiple triggers" this plan reuses for confirm/back too

The existing Escape handler already does exactly what the Start/Menu button (Standard Gamepad index 9) should do. Extract its body into a named function so both triggers share one implementation.

- [ ] **Step 1: Extract the handler body**

Find this exact block (`index.html:13620`):

```js
        document.addEventListener('keydown', (e) => {
            if (e.code !== 'Escape') return;
            // If a menu screen (Settings/How to Play/Career/Credits) is open, Esc closes it
            // (routes back to its origin — main menu or pause) instead of toggling pause/resume.
            if (typeof MENU_SCREENS !== 'undefined' &&
                MENU_SCREENS.some(id => document.getElementById(id)?.classList.contains('visible'))) {
                if (window.ToneSFX) ToneSFX.uiBack();
                closeMenuScreen(); e.preventDefault(); return;
            }
            if (GameSM.state === 'match') { if (window.ToneSFX) ToneSFX.uiConfirm(); GameSM.enterPause(); e.preventDefault(); }
            else if (GameSM.state === 'pause') { if (window.ToneSFX) ToneSFX.uiBack(); GameSM.resumeMatch(); e.preventDefault(); }
        });
```

Replace it with:

```js
        // Shared by the Escape key AND the gamepad Start/Menu button (index 9) — same "close
        // whatever's open, or toggle pause" behavior regardless of which input triggered it.
        function handleMenuOrPauseToggle() {
            if (typeof MENU_SCREENS !== 'undefined' &&
                MENU_SCREENS.some(id => document.getElementById(id)?.classList.contains('visible'))) {
                if (window.ToneSFX) ToneSFX.uiBack();
                closeMenuScreen();
                return;
            }
            if (GameSM.state === 'match') { if (window.ToneSFX) ToneSFX.uiConfirm(); GameSM.enterPause(); }
            else if (GameSM.state === 'pause') { if (window.ToneSFX) ToneSFX.uiBack(); GameSM.resumeMatch(); }
        }
        window.handleMenuOrPauseToggle = handleMenuOrPauseToggle;
        document.addEventListener('keydown', (e) => {
            if (e.code !== 'Escape') return;
            handleMenuOrPauseToggle();
            e.preventDefault();
        });
```

- [ ] **Step 2: Add Start-button edge detection to the existing gameplay poller**

Find this exact block (`index.html:3646`, inside `pollGamepadInput`):

```js
        function pollGamepadInput() {
            if (!navigator.getGamepads) return;
            const pads = navigator.getGamepads();
            let gp = null;
            for (let i = 0; i < pads.length; i++) { if (pads[i]) { gp = pads[i]; break; } }
            if (!gp) { window._padMoveDir = 0; return; }

            const pressed = (i) => !!(gp.buttons[i] && gp.buttons[i].pressed);
```

Add a Start-button check right after the `pressed` helper is defined (still inside `pollGamepadInput`, before the movement logic):

```js
            const pressed = (i) => !!(gp.buttons[i] && gp.buttons[i].pressed);

            // Start/Menu button (Standard Gamepad index 9) — same as Escape, works mid-match.
            if (pressed(9) && !_padPrev[9]) handleMenuOrPauseToggle();
            _padPrev[9] = pressed(9);
```

- [ ] **Step 3: Test — Start button pauses/unpauses exactly like Escape**

Start a match with a real controller connected, press Start (or the equivalent "Menu"/"Options" button) — the pause overlay should appear, identical to pressing Escape. Press it again — resumes. This only needs to work during gameplay for this task; Task 4 wires the menu-open case once the navigator polls in menu contexts too.

- [ ] **Step 4: Run the syntax check** (command from Task 1, Step 6). Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "Extract shared menu/pause toggle; add gamepad Start button"
```

---

### Task 3: Shared last-input-device flag + `isAnyMenuOpen()` helper

**Files:**
- Modify: `index.html:3623` (broaden `_hudInputMode`), `index.html:3662`, `index.html:3724`, `index.html:3744` (rename call sites)
- Create (in the same script): `isAnyMenuOpen()` near the `MENU_SCREENS` declaration (`index.html:14393`)

**Interfaces:**
- Consumes: `MENU_SCREENS`, `#domMenu`, `#multiplayerLobby`, `#pauseOverlay` — all existing DOM
- Produces: `window._lastInputMode` (`'keyboard' | 'pad'`, replaces `_hudInputMode`), `isAnyMenuOpen()` → returns the currently-active screen's **root element** for querying (see return value table below), or `null` if nothing is open. Task 4's navigator and Task 8's prompt bar both depend on this exact return contract.

`isAnyMenuOpen()` return values, checked in this priority order (pause takes precedence over an open menu screen, matching how `showMenuScreen`'s `from: 'pause'` already models pause as the "parent" state):

| Condition | Returns |
|---|---|
| `#pauseOverlay` has `style.display === 'flex'` | the `#pauseOverlay` element |
| Any `MENU_SCREENS` id has class `visible` | that screen's element |
| `#multiplayerLobby` has class `visible` | the currently active `.lobby-view` child (found via `style.display !== 'none'` among its four children) |
| `#domMenu` has class `visible` | the `#domMenu` element |
| none of the above | `null` |

- [ ] **Step 1: Broaden `_hudInputMode` into `window._lastInputMode`**

Find (`index.html:3623`):

```js
        let _hudInputMode = 'keyboard';   // 'keyboard' | 'pad' — drives the in-game HUD ability-key labels
```

Replace with:

```js
        // 'keyboard' | 'pad' — last input device used, ANYWHERE (menus and gameplay). Drives the
        // in-game HUD ability-key labels AND the menu prompt bar (Task 8) off one shared flag.
        window._lastInputMode = 'keyboard';
```

- [ ] **Step 2: Update the three remaining `_hudInputMode` references to `window._lastInputMode`**

Find (`index.html:3662`):

```js
            if ((anyPadBtn || window._padMoveDir !== 0) && _hudInputMode !== 'pad') { _hudInputMode = 'pad'; updateHudInputHints(); }
```

Replace with:

```js
            if ((anyPadBtn || window._padMoveDir !== 0) && window._lastInputMode !== 'pad') { window._lastInputMode = 'pad'; updateHudInputHints(); }
```

Find (`index.html:3724`, inside `updateHudInputHints`):

```js
            const usePad = forced ? true : (_hudInputMode === 'pad');
```

Replace with:

```js
            const usePad = forced ? true : (window._lastInputMode === 'pad');
```

Find (`index.html:3744`):

```js
        document.addEventListener('keydown', () => {
            if (window._hudForceType) return;   // preview override stays put
            if (_hudInputMode !== 'keyboard') { _hudInputMode = 'keyboard'; updateHudInputHints(); }
        }, true);
```

Replace with:

```js
        document.addEventListener('keydown', () => {
            if (window._hudForceType) return;   // preview override stays put
            if (window._lastInputMode !== 'keyboard') { window._lastInputMode = 'keyboard'; updateHudInputHints(); }
        }, true);
        // A mouse click also means "back to keyboard/mouse" — swaps the prompt bar (Task 8) and
        // ability-bar glyphs back to keyboard hints if the player picks the mouse back up.
        document.addEventListener('click', () => {
            if (window._hudForceType) return;
            if (window._lastInputMode !== 'keyboard') { window._lastInputMode = 'keyboard'; updateHudInputHints(); }
        }, true);
```

(The one remaining `if (f && ['xbox', 'playstation', 'nintendo', 'generic'].includes(f)) { window._hudForceType = f; _hudInputMode = 'pad'; ...` block further down — find it and change that `_hudInputMode = 'pad'` to `window._lastInputMode = 'pad'` too.)

- [ ] **Step 3: Add `isAnyMenuOpen()`**

Find (`index.html:14393`):

```js
        const MENU_SCREENS = ['settingsScreen', 'howToPlayScreen', 'careerScreen', 'creditsScreen'];
        let _menuScreenReturn = 'menu';   // where Back goes: 'menu' or 'pause'
```

Insert immediately after (before `function hideAllMenuScreens()`):

```js
        // Returns the root element of whichever menu/overlay is currently the "active" screen for
        // gamepad navigation purposes (Tasks 4+), or null if none is open. Checked in priority
        // order: pause > an open MENU_SCREENS entry > the multiplayer lobby's active sub-view >
        // the main menu. Live gameplay with nothing open returns null.
        function isAnyMenuOpen() {
            const pause = document.getElementById('pauseOverlay');
            if (pause && pause.style.display === 'flex') return pause;

            for (const id of MENU_SCREENS) {
                const el = document.getElementById(id);
                if (el && el.classList.contains('visible')) return el;
            }

            const lobby = document.getElementById('multiplayerLobby');
            if (lobby && lobby.classList.contains('visible')) {
                const views = ['lobbyModeView', 'lobbyHostView', 'lobbyJoinView', 'lobbyConnectedView'];
                for (const vid of views) {
                    const vel = document.getElementById(vid);
                    if (vel && vel.style.display !== 'none') return vel;
                }
                return lobby;   // fallback: lobby visible but no sub-view matched (shouldn't happen)
            }

            const menu = document.getElementById('domMenu');
            if (menu && menu.classList.contains('visible')) return menu;

            return null;
        }
        window.isAnyMenuOpen = isAnyMenuOpen;
```

- [ ] **Step 4: Test in the console**

With the game loaded on the main menu:

```js
isAnyMenuOpen().id   // "domMenu"
```

Click Start Battle to enter a match:

```js
isAnyMenuOpen()   // null
```

Open Settings from the main menu:

```js
isAnyMenuOpen().id   // "settingsScreen"
```

Open the multiplayer lobby, click Host Game:

```js
isAnyMenuOpen().id   // "lobbyHostView"
```

- [ ] **Step 5: Run the syntax check** (command from Task 1, Step 6). Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "Add shared input-mode flag and isAnyMenuOpen() helper"
```

---

### Task 4: Generic navigator — focus movement only

**Files:**
- Modify: `index.html` — new code near `pollGamepadInput` (~line 3688), plus one line in the always-running render-loop block at `index.html:13077`
- Modify: `styles.css` — new `.gp-focused` rule near `.game-btn:hover:not(:disabled)` (`styles.css:1749`)

**Interfaces:**
- Consumes: `isAnyMenuOpen()` (Task 3), `GP` object (existing, for button indices), `window._lastInputMode` (Task 3)
- Produces: `pollGamepadMenuNav()` — global function, polled every frame; `window._navFocusedIndex` / `window._navRoot` (internal state, read by Task 5's confirm/back and Task 6's adjust); `.gp-focused` CSS class

This task delivers **only** up/down focus movement with wraparound and a visible highlight — confirm/back/adjust come in Tasks 5–6. Tested on the main menu (six plain buttons, no sliders — the simplest screen).

- [ ] **Step 1: Add the `.gp-focused` CSS rule**

Find (`styles.css:1749`):

```css
.game-btn:hover:not(:disabled) {
    border-color: #ffffff;
    color: #fff4c2;                          /* warm cream highlight (FF9 selected) */
    transform: translateY(-2px);
}
```

Insert immediately after:

```css
/* Gamepad/keyboard focus — mirrors the mouse-hover look (same border/color/lift) plus the same
   ▶ arrow used to mark the selected spell in the in-game command menu, so menu selection and
   battle-command selection read as one visual language. Applies to BOTH .gp-focused (set by the
   gamepad navigator, Task 4) and native :focus-visible (Tab/keyboard users get the same look for
   free — native <button>/<input> elements are already keyboard-focusable with no extra JS). */
.game-btn.gp-focused:not(:disabled),
.game-btn:focus-visible:not(:disabled) {
    border-color: #ffffff;
    color: #fff4c2;
    transform: translateY(-2px);
    outline: none;
}
.game-btn.gp-focused:not(:disabled)::before,
.game-btn:focus-visible:not(:disabled)::before {
    content: '\25B6';
    color: #f0c050;
    position: absolute;
    left: -22px;
    top: 50%;
    transform: translateY(-50%);
}
.settings-slider.gp-focused,
.settings-slider:focus-visible,
.settings-toggle.gp-focused,
.settings-toggle:focus-visible,
.fps-cycler.gp-focused,
.fps-cycler:focus-visible {
    outline: 2px solid #fff4c2;
    outline-offset: 2px;
}
```

- [ ] **Step 2: Add `position: relative` to `.menu-btn` so the `::before` arrow positions correctly**

Find (`styles.css:2079`):

```css
.menu-btn {
```

Check the next few lines for an existing `position` declaration. If none exists, add `position: relative;` as the first declaration inside the rule. (If `.menu-btn` already has `position: relative` or `position: absolute` from an ancestor rule, skip this — verify visually in Step 6 either way.)

- [ ] **Step 3: Add the navigator function**

Insert after `window.pollGamepadInput = pollGamepadInput;` (`index.html:3688`):

```js
        // ============================================================
        // GAMEPAD MENU NAVIGATION (generic, drives every menu screen)
        // ============================================================
        window._navRoot = null;          // the screen root isAnyMenuOpen() last returned
        window._navFocusedIndex = 0;
        const _navPadPrev = {};

        // Hold-to-repeat for the four directions (old console menu feel): fires immediately on
        // first press, then again after NAV_REPEAT_DELAY, then every NAV_REPEAT_RATE while held.
        // Confirm/back stay one-shot (_navPadPrev above) — a held A/B shouldn't machine-gun.
        const NAV_REPEAT_DELAY = 400;
        const NAV_REPEAT_RATE = 120;
        const _navHoldState = {};   // { up: {since, lastFire}, down: {...}, left: {...}, right: {...} }
        function navDirEdge(name, isDown) {
            const now = performance.now();
            const st = _navHoldState[name] || (_navHoldState[name] = { since: 0, lastFire: 0 });
            if (!isDown) { st.since = 0; return false; }
            if (st.since === 0) { st.since = now; st.lastFire = now; return true; }   // fresh press
            const held = now - st.since;
            if (held >= NAV_REPEAT_DELAY && (now - st.lastFire) >= NAV_REPEAT_RATE) { st.lastFire = now; return true; }
            return false;
        }

        // Elements the navigator will move focus between, in DOM order. Text inputs are
        // deliberately excluded — no on-screen keyboard in this pass.
        function getNavFocusables(root) {
            if (!root) return [];
            return Array.from(root.querySelectorAll(
                '.menu-btn:not([disabled]), input[type="range"], input[type="checkbox"], .fps-cycler'
            )).filter(el => el.offsetParent !== null);   // skip anything display:none-hidden
        }

        function setNavFocus(list, index) {
            const prev = list[window._navFocusedIndex];
            if (prev) prev.classList.remove('gp-focused');
            window._navFocusedIndex = index;
            const el = list[index];
            if (el) { el.classList.add('gp-focused'); el.focus(); }
        }

        function pollGamepadMenuNav() {
            const root = isAnyMenuOpen();
            if (!root) { window._navRoot = null; return; }

            if (!navigator.getGamepads) return;
            const pads = navigator.getGamepads();
            let gp = null;
            for (let i = 0; i < pads.length; i++) { if (pads[i]) { gp = pads[i]; break; } }
            if (!gp) return;

            const list = getNavFocusables(root);
            if (list.length === 0) { window._navRoot = root; return; }

            // Root changed since last poll (a new screen just opened, or a lobby sub-view
            // switched) — reset focus to the first element.
            if (root !== window._navRoot) {
                window._navRoot = root;
                window._navFocusedIndex = 0;
                setNavFocus(list, 0);
            }

            const pressed = (i) => !!(gp.buttons[i] && gp.buttons[i].pressed);
            const ax = gp.axes[GP.stickY] || 0;
            const upNow   = pressed(GP.dpadUp)   || ax < -0.5;
            const downNow = pressed(GP.dpadDown) || ax >  0.5;
            const upEdge   = navDirEdge('up', upNow);
            const downEdge = navDirEdge('down', downNow);
            // Note: switching window._lastInputMode to 'pad' on first input is handled once, at
            // the very end of this function (added in Task 8) — not here. All four directions
            // plus confirm/back/start need to have been computed first; checking this early would
            // reference leftEdge/rightEdge (Task 6) before their `const` declarations run later in
            // this same function body (a ReferenceError — the temporal dead zone).

            if (upEdge) {
                const next = (window._navFocusedIndex - 1 + list.length) % list.length;
                setNavFocus(list, next);
                if (window.ToneSFX) ToneSFX.uiHover();
            } else if (downEdge) {
                const next = (window._navFocusedIndex + 1) % list.length;
                setNavFocus(list, next);
                if (window.ToneSFX) ToneSFX.uiHover();
            }
        }
        window.pollGamepadMenuNav = pollGamepadMenuNav;
```

- [ ] **Step 4: Hook it into the always-running render loop**

Find (`index.html:13077`, inside the `scene.onBeforeRenderObservable.add(() => { ... })` block that already contains the menu-title guard):

```js
                // Debug hide-HUD: re-hide GUI HUD controls that event-driven code re-shows
                if (window.enforceHudHidden) window.enforceHudHidden();
```

Insert immediately after that line (before the "Retired Babylon GUI menu" comment block):

```js
                // Drive gamepad menu navigation whenever a menu/overlay is open (no-ops otherwise)
                if (window.pollGamepadMenuNav) window.pollGamepadMenuNav();
```

- [ ] **Step 5: Test — main menu focus movement**

Load the game, real Xbox controller connected. On the main menu, press D-pad down: the first button (`Start Battle`) should get the hover-look + a gold ▶ arrow to its left. Keep pressing down: focus moves through all six buttons in order (`Start Battle → Multiplayer → Settings → How to Play → Credits → Career`), wrapping back to `Start Battle` after `Career`. Press up from `Start Battle`: wraps to `Career`. Then hold down (don't release): focus should sit for a beat (~400ms) then start auto-advancing roughly every 120ms until released — confirms `navDirEdge`'s hold-to-repeat, not just single presses.

- [ ] **Step 6: Test — keyboard Tab gets the same visual for free**

Click anywhere on the page to give it focus, then press Tab repeatedly. Each `.menu-btn` should get the identical hover-look + ▶ arrow via `:focus-visible` (no gamepad needed) — confirms Step 1/2's CSS applies correctly without JS.

- [ ] **Step 7: Run the syntax check** (command from Task 1, Step 6). Expected: `OK`.

- [ ] **Step 8: Commit**

```bash
git add index.html styles.css
git commit -m "Add generic gamepad menu navigator: focus movement + highlight"
```

---

### Task 5: Confirm and Back

**Files:**
- Modify: `index.html` — extends `pollGamepadMenuNav()` (Task 4)

**Interfaces:**
- Consumes: `window._navRoot`, `window._navFocusedIndex`, `getNavFocusables()`, `setNavFocus()` (all Task 4)
- Produces: back-button lookup used by Task 7 too (the table gets its remaining entries added there — this task only adds the four screens already in `MENU_SCREENS` plus the main menu no-op)

- [ ] **Step 1: Add the back-target lookup and the confirm/back edge handling**

Find, inside `pollGamepadMenuNav()` (added in Task 4), the block:

```js
            if (upEdge) {
                const next = (window._navFocusedIndex - 1 + list.length) % list.length;
                setNavFocus(list, next);
                if (window.ToneSFX) ToneSFX.uiHover();
            } else if (downEdge) {
                const next = (window._navFocusedIndex + 1) % list.length;
                setNavFocus(list, next);
                if (window.ToneSFX) ToneSFX.uiHover();
            }
        }
```

Replace with (adds confirm/back below the existing up/down block, still inside the same function):

```js
            if (upEdge) {
                const next = (window._navFocusedIndex - 1 + list.length) % list.length;
                setNavFocus(list, next);
                if (window.ToneSFX) ToneSFX.uiHover();
            } else if (downEdge) {
                const next = (window._navFocusedIndex + 1) % list.length;
                setNavFocus(list, next);
                if (window.ToneSFX) ToneSFX.uiHover();
            }

            // Confirm (bottom face button, index 0) — click the focused element, exactly what a
            // mouse click would do. No-op on sliders/the FPS cycler (they're adjusted, not
            // "confirmed" — see Task 6).
            const confirmNow = pressed(0);
            if (confirmNow && !_navPadPrev.confirm) {
                const el = list[window._navFocusedIndex];
                if (el && el.tagName !== 'INPUT' && !el.classList.contains('fps-cycler')) {
                    el.click();
                }
            }
            _navPadPrev.confirm = confirmNow;

            // Back (right face button, index 1) — click this screen's designated back/cancel
            // button. Root id -> back-button id. Main menu has no entry (nothing to back out of).
            const backNow = pressed(1);
            if (backNow && !_navPadPrev.back) {
                const backTargetId = NAV_BACK_TARGETS[root.id];
                if (backTargetId) {
                    const backEl = document.getElementById(backTargetId);
                    if (backEl) backEl.click();
                }
            }
            _navPadPrev.back = backNow;

            // Start/Menu button (index 9) — same handler Task 2 wired into the gameplay-only
            // poller. That poller never runs while a menu is open (gated on gameState ===
            // "playing"), so a menu screen reached by MOUSE (no pad input yet) would otherwise be
            // unreachable by Start. This is the only place Start gets handled while a menu is open.
            const startNow = pressed(9);
            if (startNow && !_navPadPrev.start) handleMenuOrPauseToggle();
            _navPadPrev.start = startNow;
        }
```

- [ ] **Step 2: Add the `NAV_BACK_TARGETS` table above `pollGamepadMenuNav`**

Find (`index.html`, just before `function pollGamepadMenuNav() {`, from Task 4's Step 3):

```js
        function pollGamepadMenuNav() {
```

Insert immediately before it:

```js
        // Screen root id -> its Back/Cancel button id. Extended in a later task with the
        // multiplayer lobby's four sub-views and the pause overlay.
        const NAV_BACK_TARGETS = {
            settingsScreen: 'settingsBack',
            howToPlayScreen: 'howToBack',
            creditsScreen: 'creditsBack',
            careerScreen: 'careerBack',
        };
```

- [ ] **Step 3: Test — confirm and back on the main menu and settings**

Main menu: D-pad to `Settings`, press the bottom face button (A on Xbox) — the Settings screen opens. Press the right face button (B on Xbox) — returns to the main menu (via `settingsBack`'s existing click handler, `closeMenuScreen()`). Press B again on the main menu — nothing happens (no entry for `domMenu` in `NAV_BACK_TARGETS`, correct per spec).

Then, reach Settings with the **mouse** (click it), so no pad input has happened yet, and press the controller's Start button — it should close Settings exactly like B/Escape would. This specifically exercises the Start-in-an-open-menu path added just above, which the gameplay-only poller (Task 2) cannot reach.

- [ ] **Step 4: Run the syntax check** (command from Task 1, Step 6). Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "Add gamepad confirm/back to the menu navigator"
```

---

### Task 6: Left/Right adjust — sliders, FPS cycler, How-to-Play pager

**Files:**
- Modify: `index.html` — extends `pollGamepadMenuNav()` further, adds `tabindex="0"` to the FPS cycler markup
- Modify: `index.html:170` (the `.fps-cycler` div) — add `tabindex="0"`

**Interfaces:**
- Consumes: existing `Settings.set(...)` change handlers (unchanged — triggered via dispatched `input`/`change` events), existing `setFpsCapPrev`/`setFpsCapNext` click handlers, existing `htpSetPage()` (from the How-to-Play carousel work)
- Produces: nothing new consumed by later tasks

- [ ] **Step 1: Make the FPS cycler focusable**

Find (`index.html:169`, the FPS Cap row):

```html
                <div class="settings-row"><span>FPS Cap</span>
                    <div class="fps-cycler">
```

Replace with:

```html
                <div class="settings-row"><span>FPS Cap</span>
                    <div class="fps-cycler" tabindex="0">
```

- [ ] **Step 2: Add left/right adjust handling**

Find, inside `pollGamepadMenuNav()`, the block added in Task 5, Step 1 (starting `// Confirm (bottom face button...`). Insert a new block immediately **before** it (still after the up/down block, before confirm/back):

```js
            // Left/Right: adjust whatever's focused, or page the How-to-Play carousel (which
            // pages regardless of focus, matching its existing ArrowLeft/Right keyboard handler).
            // Same hold-to-repeat as up/down (navDirEdge, defined in Task 4).
            const leftNow  = pressed(14);
            const rightNow = pressed(15);
            const leftEdge  = navDirEdge('left', leftNow);
            const rightEdge = navDirEdge('right', rightNow);

            if (leftEdge || rightEdge) {
                if (root.id === 'howToPlayScreen' && window.htpSetPage && typeof window.htpPage === 'number') {
                    htpSetPage(window.htpPage + (rightEdge ? 1 : -1));
                    if (window.ToneSFX) ToneSFX.uiHover();
                } else {
                    const el = list[window._navFocusedIndex];
                    if (el && el.tagName === 'INPUT' && el.type === 'range') {
                        if (rightEdge) el.stepUp(); else el.stepDown();
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        if (window.ToneSFX) ToneSFX.uiHover();
                    } else if (el && el.classList.contains('fps-cycler')) {
                        const btn = document.getElementById(rightEdge ? 'setFpsCapNext' : 'setFpsCapPrev');
                        if (btn) btn.click();
                    }
                }
            }

```

- [ ] **Step 3: Expose the How-to-Play carousel's current page as `window.htpPage`**

The existing carousel code (added earlier this session) tracks its page in a closure-local `htpPage` variable, not exposed on `window`. Find the existing pager code:

```js
            let htpPage = 0;
            function htpSetPage(p) {
                htpPage = Math.max(0, Math.min(htpPages.length - 1, p));
```

Replace with:

```js
            window.htpPage = 0;
            function htpSetPage(p) {
                window.htpPage = Math.max(0, Math.min(htpPages.length - 1, p));
```

Then find every remaining bare `htpPage` reference in that same function/surrounding closure (the dots-render line and the prev/next disabled-state lines use it) and prefix with `window.`:

```js
                htpPages.forEach((el, i) => el.classList.toggle('active', i === htpPage));
```

becomes

```js
                htpPages.forEach((el, i) => el.classList.toggle('active', i === window.htpPage));
```

and

```js
                if (dots) dots.innerHTML = Array.from(htpPages, (_, i) =>
                    '<span class="htp-dot' + (i === htpPage ? ' active' : '') + '"></span>').join('');
                const prev = document.getElementById('htpPrev');
                const next = document.getElementById('htpNext');
                if (prev) prev.disabled = (htpPage === 0);
                if (next) next.disabled = (htpPage === htpPages.length - 1);
```

becomes

```js
                if (dots) dots.innerHTML = Array.from(htpPages, (_, i) =>
                    '<span class="htp-dot' + (i === window.htpPage ? ' active' : '') + '"></span>').join('');
                const prev = document.getElementById('htpPrev');
                const next = document.getElementById('htpNext');
                if (prev) prev.disabled = (window.htpPage === 0);
                if (next) next.disabled = (window.htpPage === htpPages.length - 1);
```

Also update the two `htpPage - 1`/`htpPage + 1` call sites (the `htpPrev`/`htpNext` click handlers and the `ArrowLeft`/`ArrowRight` keydown handler) from `htpSetPage(htpPage - 1)` / `htpSetPage(htpPage + 1)` to `htpSetPage(window.htpPage - 1)` / `htpSetPage(window.htpPage + 1)`.

- [ ] **Step 4: Test — sliders, FPS cycler, How-to-Play paging**

Settings screen: D-pad to the Master slider, press D-pad left/right — the slider value changes and the number/label updates live (confirms the dispatched `input` event reached the existing listener). Hold right — the value should climb steadily after the initial ~400ms delay (same repeat behavior as focus movement, shared via `navDirEdge`), not require repeated individual presses. D-pad to the FPS Cap row, left/right cycles through the FPS options exactly like clicking the arrow buttons. D-pad to Render Resolution, left/right steps by 25 (its `step` attribute).

How-to-Play screen: D-pad left/right pages through all four cards regardless of which element (if any) is focused, matching the existing keyboard behavior exactly.

- [ ] **Step 5: Run the syntax check** (command from Task 1, Step 6). Expected: `OK`.

- [ ] **Step 6: Commit**

```bash
git add index.html
git commit -m "Add gamepad left/right adjust for sliders, FPS cycler, How-to-Play paging"
```

---

### Task 7: Extend to remaining screens — credits, career, multiplayer lobby, pause

**Files:**
- Modify: `index.html` — extends `NAV_BACK_TARGETS` (Task 5)

**Interfaces:**
- Consumes: `NAV_BACK_TARGETS` (Task 5), `getNavFocusables`/`isAnyMenuOpen` (Tasks 3–4, already generic — no changes needed to make them work on these screens)

Credits and Career already work as of Task 5 (they're in `MENU_SCREENS` and already have `NAV_BACK_TARGETS` entries). This task's real work is the multiplayer lobby's four sub-views and the pause overlay, which `isAnyMenuOpen()` (Task 3) already returns correctly — only the back-target table needs their entries.

- [ ] **Step 1: Add the remaining back-target entries**

Find (`index.html`, `NAV_BACK_TARGETS`, added in Task 5):

```js
        const NAV_BACK_TARGETS = {
            settingsScreen: 'settingsBack',
            howToPlayScreen: 'howToBack',
            creditsScreen: 'creditsBack',
            careerScreen: 'careerBack',
        };
```

Replace with:

```js
        const NAV_BACK_TARGETS = {
            settingsScreen: 'settingsBack',
            howToPlayScreen: 'howToBack',
            creditsScreen: 'creditsBack',
            careerScreen: 'careerBack',
            lobbyModeView: 'btnBackMenu',
            lobbyHostView: 'btnCancelHost',
            lobbyJoinView: 'btnCancelJoin',
            lobbyConnectedView: 'btnDisconnect',
            pauseOverlay: 'pauseResumeBtn',
        };
```

- [ ] **Step 2: Verify the multiplayer lobby's Connect button doesn't get skipped**

`lobbyJoinView` contains `#joinInput` (a text input, correctly excluded by `getNavFocusables`'s query) followed by `#btnConnect` and `#btnCancelJoin`. Confirm in the console:

```js
document.getElementById('lobbyJoinView').classList; // after clicking Join Game
getNavFocusables(document.getElementById('lobbyJoinView')).map(el => el.id)
// expect: ["btnConnect", "btnCancelJoin"] — joinInput correctly absent
```

Same check on the Settings screen's player-name field:

```js
getNavFocusables(document.getElementById('settingsScreen')).map(el => el.id || el.className)
// expect: setName is NOT in this list; setMaster/setMusic/setSfx/setFullscreen/setRenderScale/
// fps-cycler/setReduceMotion/setColorblind/settingsBack are
```

- [ ] **Step 3: Test — every remaining screen**

Credits: D-pad down focuses `creditsBack` (only one focusable item), A activates it, B does the same. Career: identical, `careerBack`. Multiplayer lobby: from the main menu, open Multiplayer, D-pad between Host/Join/Back, confirm Host Game — the host view's Copy Code / Cancel become navigable, B returns to the mode-select sub-view (not the main menu — confirms `isAnyMenuOpen()`'s root-changed detection correctly resets focus when swapping sub-views within the same outer `#multiplayerLobby`). Pause: start a match, press Start (or Escape) to pause, D-pad between Resume/Settings/Quit, B (or Escape) resumes exactly like clicking Resume.

- [ ] **Step 4: Run the syntax check** (command from Task 1, Step 6). Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add index.html
git commit -m "Extend gamepad back-navigation to multiplayer lobby and pause overlay"
```

---

### Task 8: Prompt bar — DOM, CSS, glyph resolution, API

**Files:**
- Modify: `index.html` — new markup inside `#gameContainer`, new JS near `padGlyphHTML` (~line 3723)
- Modify: `styles.css` — new `#gamepadPromptBar` rules

**Interfaces:**
- Consumes: `detectPadType()`, `padGlyphHTML()` (existing, reused for confirm/back icons), `window._lastInputMode` (Task 3)
- Produces: `window.setGamepadPrompts(entries)` — global function, `entries` is an array of `{ action: 'navigate' | 'confirm' | 'back' | 'adjust' | 'page' }` objects. Task 9 calls this from every in-scope screen.

- [ ] **Step 1: Add the prompt bar markup**

Find (`index.html`, inside `#gameContainer`, immediately before its closing tag — search for `</div><!-- /gameContainer -->`):

```html
    </div><!-- /gameContainer -->
```

Insert immediately before it:

```html
        <!-- Gamepad/keyboard prompt bar — bottom-right, always visible while a menu is open
             (Task 9 wires each screen to call window.setGamepadPrompts). Purely informational:
             pointer-events none so it never blocks a click underneath it. -->
        <div id="gamepadPromptBar"></div>
    </div><!-- /gameContainer -->
```

- [ ] **Step 2: Add the CSS**

Find (`styles.css`, near the other `#loadingScreen`/HUD-adjacent rules — add as a new block at the end of the file):

```css
/* ============================================================
   GAMEPAD/KEYBOARD PROMPT BAR — bottom-right, matches the steel-panel
   HUD window look (command/status windows), swaps content live.
   ============================================================ */
#gamepadPromptBar {
    position: absolute;
    right: 24px;
    bottom: 24px;
    display: flex;
    gap: 16px;
    pointer-events: none;
    z-index: 250;   /* above .arcane-overlay (200), below the pause overlay (700) */
}
#gamepadPromptBar .gp-prompt-item {
    display: flex;
    align-items: center;
    gap: 6px;
    font-family: 'FF9UI', sans-serif;
    font-size: 14px;
    color: #dfe6f2;
    text-shadow: var(--ff9-shadow, 2px 2px 0 #000);
}
#gamepadPromptBar .gp-prompt-glyph {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 20px;
    height: 20px;
    padding: 0 4px;
    border-radius: 4px;
    background: rgba(20,26,40,0.82);
    border: 1px solid #5a4a78;
    font-size: 12px;
    font-weight: 700;
}
```

- [ ] **Step 3: Add the glyph resolution + render function**

Find (`index.html`, immediately after `window.updateHudInputHints = updateHudInputHints;`, `index.html:3740`):

```js
        window.updateHudInputHints = updateHudInputHints;
```

Insert immediately after:

```js
        window.updateHudInputHints = updateHudInputHints;

        // ---- Prompt bar: resolves an action name to a keyboard OR pad-glyph label ----
        // Reuses padGlyphHTML for confirm/back (real vendor-colored face-button chips — these
        // are the only two actions where the vendor glyph actually differs meaningfully).
        // navigate/adjust/page use plain arrow glyphs, which don't vary by vendor.
        const PROMPT_KEYBOARD = {
            navigate: { glyph: '↑↓', label: 'Navigate' },
            confirm:  { glyph: 'Enter', label: 'Select' },
            back:     { glyph: 'Esc', label: 'Back' },
            adjust:   { glyph: '←→', label: 'Adjust' },
            page:     { glyph: '←→', label: 'Page' },
        };
        let _gpPromptEntries = [];
        function renderGamepadPromptBar() {
            const bar = document.getElementById('gamepadPromptBar');
            if (!bar) return;
            const usePad = window._lastInputMode === 'pad';
            let padType = 'generic';
            if (usePad && navigator.getGamepads) {
                let id = ''; const pads = navigator.getGamepads();
                for (let i = 0; i < pads.length; i++) { if (pads[i]) { id = pads[i].id; break; } }
                padType = detectPadType(id);
            }
            bar.innerHTML = _gpPromptEntries.map(entry => {
                const kb = PROMPT_KEYBOARD[entry.action] || { glyph: '?', label: entry.action };
                if (!usePad) {
                    return '<span class="gp-prompt-item"><span class="gp-prompt-glyph">' + kb.glyph + '</span>' + kb.label + '</span>';
                }
                if (entry.action === 'confirm') {
                    // Literal index 0 (bottom face button) — matches Task 5's `pressed(0)` confirm
                    // check exactly. Deliberately NOT GP.slot1: that constant means "frostbolt's
                    // ability slot" for gameplay and only coincidentally equals 0; borrowing it
                    // here would silently break the prompt bar if gameplay rebalancing ever moves it.
                    return '<span class="gp-prompt-item">' + padGlyphHTML(padType, 0) + '<span>Select</span></span>';
                }
                if (entry.action === 'back') {
                    // Literal index 1 (right face button) — matches Task 5's `pressed(1)` back
                    // check exactly. NOT GP.parry (index 5, the shoulder button) — that would show
                    // the player the wrong button entirely.
                    return '<span class="gp-prompt-item">' + padGlyphHTML(padType, 1) + '<span>Back</span></span>';
                }
                // navigate/adjust/page: pad-agnostic D-pad glyphs (Standard Gamepad D-pad doesn't
                // vary by vendor the way face buttons do).
                const dpadGlyph = (entry.action === 'navigate') ? '↑↓' : '←→';
                return '<span class="gp-prompt-item"><span class="gp-prompt-glyph">' + dpadGlyph + '</span>' + kb.label + '</span>';
            }).join('');
        }
        window.setGamepadPrompts = function (entries) {
            _gpPromptEntries = entries || [];
            renderGamepadPromptBar();
        };
        window.renderGamepadPromptBar = renderGamepadPromptBar;   // re-render on input-mode flips (Step 4)
```

- [ ] **Step 4: Switch to pad mode and re-render the bar on first pad input**

Find, at the very end of `pollGamepadMenuNav()` (the Start-button handling added in Task 5, Step 1):

```js
            const startNow = pressed(9);
            if (startNow && !_navPadPrev.start) handleMenuOrPauseToggle();
            _navPadPrev.start = startNow;
        }
```

Replace with (adds one final block **after** every direction/button has already been read this frame — appending here, rather than checking earlier in the function, avoids referencing `leftEdge`/`rightEdge`/`confirmNow`/`backNow` before their `const` declarations run, which would throw a ReferenceError):

```js
            const startNow = pressed(9);
            if (startNow && !_navPadPrev.start) handleMenuOrPauseToggle();
            _navPadPrev.start = startNow;

            // First pad input this poll (any direction or button) switches the shared input-mode
            // flag and refreshes both the ability-bar glyphs and this prompt bar. Checked last, now
            // that upEdge/downEdge (Task 4), leftEdge/rightEdge (Task 6), and confirmNow/backNow/
            // startNow (Task 5) have all been computed above.
            if ((upEdge || downEdge || leftEdge || rightEdge || confirmNow || backNow || startNow)
                && window._lastInputMode !== 'pad') {
                window._lastInputMode = 'pad';
                if (window.updateHudInputHints) updateHudInputHints();
                if (window.renderGamepadPromptBar) renderGamepadPromptBar();
            }
        }
```

Also find the two keyboard/mouse revert listeners added in Task 3, Step 2, and add the same re-render call to both:

```js
        document.addEventListener('keydown', () => {
            if (window._hudForceType) return;   // preview override stays put
            if (window._lastInputMode !== 'keyboard') { window._lastInputMode = 'keyboard'; updateHudInputHints(); }
        }, true);
        document.addEventListener('click', () => {
            if (window._hudForceType) return;
            if (window._lastInputMode !== 'keyboard') { window._lastInputMode = 'keyboard'; updateHudInputHints(); }
        }, true);
```

Replace with:

```js
        document.addEventListener('keydown', () => {
            if (window._hudForceType) return;   // preview override stays put
            if (window._lastInputMode !== 'keyboard') { window._lastInputMode = 'keyboard'; updateHudInputHints(); if (window.renderGamepadPromptBar) renderGamepadPromptBar(); }
        }, true);
        document.addEventListener('click', () => {
            if (window._hudForceType) return;
            if (window._lastInputMode !== 'keyboard') { window._lastInputMode = 'keyboard'; updateHudInputHints(); if (window.renderGamepadPromptBar) renderGamepadPromptBar(); }
        }, true);
```

- [ ] **Step 5: Test the API directly (screens aren't wired yet — that's Task 9)**

In the console, on any screen:

```js
setGamepadPrompts([{ action: 'navigate' }, { action: 'confirm' }, { action: 'back' }]);
document.getElementById('gamepadPromptBar').textContent
// expect: "↑↓Navigate Enter Select Esc Back" (or similar — keyboard hints, since no pad touched yet)
```

Then simulate pad mode and re-check:

```js
window._lastInputMode = 'pad';
renderGamepadPromptBar();
document.getElementById('gamepadPromptBar').innerHTML
// expect: HTML containing padGlyphHTML output (colored chips) instead of "Enter"/"Esc" text
```

- [ ] **Step 6: Run the syntax check** (command from Task 1, Step 6). Expected: `OK`.

- [ ] **Step 7: Commit**

```bash
git add index.html styles.css
git commit -m "Add gamepad/keyboard prompt bar component"
```

---

### Task 9: Wire every in-scope screen to declare its prompts

**Files:**
- Modify: `index.html` — one `setGamepadPrompts(...)` call added at each screen's existing "show" call site

**Interfaces:**
- Consumes: `window.setGamepadPrompts` (Task 8)
- Produces: nothing new consumed by later tasks (Task 10 is manual verification only)

- [ ] **Step 1: Main menu**

Find (`index.html`, `setDOMMenuVisible`, from earlier reading — the `if (show) { ... }` block):

```js
            if (show) {
                const ms = document.getElementById('domModeSelect');
                if (ms) ms.classList.remove('visible');
            }
```

Replace with:

```js
            if (show) {
                const ms = document.getElementById('domModeSelect');
                if (ms) ms.classList.remove('visible');
                if (window.setGamepadPrompts) setGamepadPrompts([{ action: 'navigate' }, { action: 'confirm' }]);
            }
```

- [ ] **Step 2: Settings / How-to-Play / Credits / Career (all four via `showMenuScreen`)**

Find (`index.html`, `showMenuScreen`):

```js
        function showMenuScreen(id, from = 'menu') {
            _menuScreenReturn = from;
            if (from === 'menu') setDOMMenuVisible(false);
            if (from === 'pause') { const ov = document.getElementById('pauseOverlay'); if (ov) ov.style.display = 'none'; }
            hideAllMenuScreens();
            const el = document.getElementById(id);
            if (el) el.classList.add('visible');
        }
```

Replace with:

```js
        function showMenuScreen(id, from = 'menu') {
            _menuScreenReturn = from;
            if (from === 'menu') setDOMMenuVisible(false);
            if (from === 'pause') { const ov = document.getElementById('pauseOverlay'); if (ov) ov.style.display = 'none'; }
            hideAllMenuScreens();
            const el = document.getElementById(id);
            if (el) el.classList.add('visible');
            if (window.setGamepadPrompts) {
                if (id === 'settingsScreen') setGamepadPrompts([{ action: 'navigate' }, { action: 'adjust' }, { action: 'confirm' }, { action: 'back' }]);
                else if (id === 'howToPlayScreen') setGamepadPrompts([{ action: 'page' }, { action: 'back' }]);
                else setGamepadPrompts([{ action: 'navigate' }, { action: 'back' }]);   // credits, career
            }
        }
```

- [ ] **Step 3: Multiplayer lobby (all four sub-views via `showLobbyView`)**

Find (`index.html`, `showLobbyView`):

```js
        function showLobbyView(viewId) {
            // Accept legacy 'lobbyModeSelect' alias for the mode-select view
            if (viewId === 'lobbyModeSelect') viewId = 'lobbyModeView';

            const views = ['lobbyModeView', 'lobbyHostView', 'lobbyJoinView', 'lobbyConnectedView'];
            for (const id of views) {
                const el = document.getElementById(id);
                if (el) el.style.display = (id === viewId) ? 'flex' : 'none';
            }
```

Replace with:

```js
        function showLobbyView(viewId) {
            // Accept legacy 'lobbyModeSelect' alias for the mode-select view
            if (viewId === 'lobbyModeSelect') viewId = 'lobbyModeView';

            const views = ['lobbyModeView', 'lobbyHostView', 'lobbyJoinView', 'lobbyConnectedView'];
            for (const id of views) {
                const el = document.getElementById(id);
                if (el) el.style.display = (id === viewId) ? 'flex' : 'none';
            }
            if (window.setGamepadPrompts) setGamepadPrompts([{ action: 'navigate' }, { action: 'confirm' }, { action: 'back' }]);
```

- [ ] **Step 4: Pause overlay**

Find (`index.html`, `GameSM.enterPause`):

```js
                this.state = 'pause';
                if (gameMode !== 'pvp') paused = true;   // freeze sim (can't pause a P2P peer)
                const quitBtn = document.getElementById('pauseQuitBtn');
                if (quitBtn) quitBtn.textContent = (gameMode === 'pvp') ? 'Leave Match' : 'Quit to Menu';
                const ov = document.getElementById('pauseOverlay');
                if (ov) ov.style.display = 'flex';
```

Replace with:

```js
                this.state = 'pause';
                if (gameMode !== 'pvp') paused = true;   // freeze sim (can't pause a P2P peer)
                const quitBtn = document.getElementById('pauseQuitBtn');
                if (quitBtn) quitBtn.textContent = (gameMode === 'pvp') ? 'Leave Match' : 'Quit to Menu';
                const ov = document.getElementById('pauseOverlay');
                if (ov) ov.style.display = 'flex';
                if (window.setGamepadPrompts) setGamepadPrompts([{ action: 'navigate' }, { action: 'confirm' }, { action: 'back' }]);
```

- [ ] **Step 5: Hide the bar during live gameplay**

Find (`index.html`, `stepFixedSim`):

```js
            function stepFixedSim() {
                const now = performance.now();
                if (gameState !== "playing" || gameOver || paused) { lastSimWallTime = now; return; }
```

Replace with:

```js
            function stepFixedSim() {
                const now = performance.now();
                if (gameState !== "playing" || gameOver || paused) { lastSimWallTime = now; return; }
                if (window.setGamepadPrompts && document.getElementById('gamepadPromptBar')?.innerHTML) {
                    setGamepadPrompts([]);   // clear once, first frame of live gameplay — ability bar owns hints now
                }
```

- [ ] **Step 6: Test — prompt bar content per screen**

Visit each screen and confirm the bar's content: main menu shows Navigate/Select (no Back, correct — matches `NAV_BACK_TARGETS` having no `domMenu` entry). Settings shows Navigate/Adjust/Select/Back. How-to-Play shows Page/Back (no Navigate — correct, there's only one focusable item there). Credits/Career/lobby/pause show Navigate/Select/Back. Starting a match clears the bar entirely within one frame.

- [ ] **Step 7: Run the syntax check** (command from Task 1, Step 6). Expected: `OK`.

- [ ] **Step 8: Commit**

```bash
git add index.html
git commit -m "Wire every in-scope screen to declare its gamepad prompts"
```

---

### Task 10: Full controller-only playthrough (capstone verification)

**Files:** none — verification only

**Interfaces:** none

- [ ] **Step 1: Play an entire match using only a real Xbox controller — no mouse, no keyboard**

From page load: click through the loading screen (mouse is fine here — it's pre-controller-detection), then controller-only from the main menu onward: navigate to Start Battle, confirm, play a full match (movement, all three spells, parry, ultimate). While playing, glance at the ability bar — `#fireballSlot`, `#frostboltSlot`, `#thunderstormSlot`, `#parryButton`'s `.ability-key` labels should all show colored controller glyphs, not `1`/`2`/`3`/`Space` (this is Task 1's fix/verification, re-confirmed here in a real full match rather than in isolation). Reach the victory screen, confirm Continue, back at the main menu.

- [ ] **Step 2: Repeat for Settings, adjusting every control type**

Enter Settings via controller, adjust Master/Music/SFX/Render Res sliders, step the FPS cycler, toggle Fullscreen/Reduce Motion/Colorblind, back out — confirm every value actually changed (check the on-screen labels, and that Master/Music/SFX audibly changed).

- [ ] **Step 3: Repeat for the multiplayer lobby (host side)**

Controller-only: Multiplayer → Host Game → Copy Code → Cancel → back to main menu.

- [ ] **Step 4: Mid-match pause via Start button, not Escape**

Confirm Start opens pause, Resume/Settings/Quit are all navigable, Resume via confirm button returns to the match with correct sim state (no desync — this is single-player so there's no rollback risk, but confirm the match continues normally, not restarted).

- [ ] **Step 5: Switch back to mouse mid-session**

After any of the above, click a menu button with the mouse — confirm the prompt bar and ability-bar glyphs revert to keyboard hints within one frame.

- [ ] **Step 6: If anything in Steps 1–5 fails, identify which task's code is responsible and fix it there** (not a patch bolted onto this task) — re-run that task's own Step "Test" before re-attempting this capstone task.

- [ ] **Step 7: Final syntax check** (command from Task 1, Step 6). Expected: `OK`.

- [ ] **Step 8: No commit for this task** — it's verification-only. If Step 6 required fixes, those commits already happened inside the relevant earlier task.
