# Controller/Gamepad Support — As-Built Reference

**Date:** 2026-07-03
**Project:** Volleybolt
**Status:** Shipped, live-tested with a real Xbox controller

## Purpose

The original design doc ([2026-07-03-controller-menu-navigation-design.md](2026-07-03-controller-menu-navigation-design.md))
and its [plan](../plans/2026-07-03-controller-menu-navigation.md) covered menu
navigation + prompt bar + ability-bar glyphs, executed as 10 subagent-driven
tasks. Real-controller playtesting after those 10 tasks turned up several
gaps the design didn't anticipate and one entire UI surface (the in-battle
COMMAND window) that fell outside its scope. This doc describes the system
as it actually shipped, so a future touch doesn't have to re-derive it from
a diff. Read this instead of re-reading the design doc's Decisions section
line by line — this supersedes it where they disagree.

## The three UI surfaces, and why there are three

Controller glyphs/hints have to reach three unrelated rendering systems.
Each was wired up separately and each has its own refresh function:

1. **DOM menu screens** (`index.html`) — main menu, settings, how-to-play,
   credits, career, multiplayer lobby, pause overlay. Driven by
   `pollGamepadMenuNav()` (~3785) and `getNavFocusables()`/`setNavFocus()`
   (~3745/3763).
2. **DOM in-game HUD** — the four `.ability-key` chips under the health
   bars. Driven by `updateHudInputHints()` (~3964), reads `GP`/`PAD_LABELS`
   and renders via `padGlyphHTML()` (~3940), which returns real HTML
   (colored glyph chips) since DOM elements support `innerHTML`.
3. **Babylon GUI "COMMAND" window** — the in-battle spell list (steel
   window, bottom-center trio). Built inside a Babylon GUI closure
   (~5836+), its own `updateCommandMenuInputHints()` (~6060) is defined
   *inside that closure* (it closes over `cmdRefs`), not in the outer
   scope like the other two. **Babylon GUI `TextBlock`s cannot render
   HTML** — no colored chips here, plain text labels only (`PAD_LABELS`
   directly: "A"/"Square"/"RB"/etc.).

This split is real, not accidental complexity: DOM and Babylon GUI are two
independent render trees with no shared node type. Any 4th UI surface added
later (another Babylon GUI window, a new DOM overlay) needs its own refresh
function following whichever of these two patterns it matches — but it only
needs ONE line to plug into the system (see next section).

## Single source of truth: `setLastInputMode()`

`window._lastInputMode` (`'keyboard'` | `'pad'`) is the one flag all three
surfaces read. It is set **only** through `setLastInputMode(mode)` (~3641),
which no-ops if the mode is unchanged and otherwise:

```js
function setLastInputMode(mode) {
    if (window._lastInputMode === mode) return;
    window._lastInputMode = mode;
    document.body.classList.toggle('gp-cursor-hidden', mode === 'pad');
    if (window.updateHudInputHints) updateHudInputHints();
    if (window.renderGamepadPromptBar) renderGamepadPromptBar();
    if (window.updateCommandMenuInputHints) updateCommandMenuInputHints();
}
window.setLastInputMode = setLastInputMode;
```

**This is the load-bearing lesson from this whole feature.** The COMMAND
window went completely unwired for the entire live-testing session because
its would-be refresh call didn't live near this flag — six different call
sites flipped `_lastInputMode` directly and each one had to remember to
call the right refresh functions, and none of them knew about a UI surface
that didn't exist yet when they were written. Centralizing means: **any
future UI that needs to react to input-device changes adds one
`if (window.yourRefreshFn) yourRefreshFn();` line here, once, instead of
hunting down every call site that flips the flag.**

Call sites that flip the mode (all now just call `setLastInputMode(...)`
with no follow-up refresh calls — that would be redundant):
- `pollGamepadInput()` (~3692) — any mapped button/stick press during play → `'pad'`
- `pollGamepadMenuNav()` (~3921) — any menu nav input → `'pad'`
- `keydown` / `click` / `mousemove` listeners (~4035-4059) → `'keyboard'`
- the `?hud=xbox|playstation|nintendo|generic` preview override (~4066) → `'pad'`

## Gamepad polling: two pollers, mutually exclusive, both hooked into the render loop

- `pollGamepadInput()` — existing pre-feature poller, runs during active
  gameplay.
- `pollGamepadMenuNav()` — new generic menu navigator.

**Both are called from the top of `window.gameRenderLoop` (~13547)**, before
its early-return for `GameSM.state === 'menu'/'lobby'/'boot'`:

```js
window.gameRenderLoop = () => {
    if (window.pollGamepadMenuNav) window.pollGamepadMenuNav();
    if (GameSM.state === 'menu' || GameSM.state === 'lobby' || GameSM.state === 'boot') return;
    // ... rest of the original loop (pollGamepadInput lives further down, gated to "playing")
```

**Why this matters:** the design's original plan was to hook menu-nav
polling into `scene.onBeforeRenderObservable`. That observable only fires
from `scene.render()`, and `gameRenderLoop` skips `scene.render()` entirely
whenever a menu/lobby/boot state is active — i.e. exactly when menu nav
needs to run. This was invisible in every automated/simulated test because
those called `pollGamepadMenuNav()` directly, bypassing the render loop
gate entirely. It only surfaced with a real controller on a real menu.
**If you ever add a new polling function, hook it into `gameRenderLoop`
directly, not an `onBeforeRenderObservable`-style callback** — the latter
is not guaranteed to fire in every game state.

The loading screen (`#loadingScreen`, before `GameSM` even exists) has its
own tiny self-contained `pollLoadingScreenGamepad()` (~8768), a
`requestAnimationFrame` loop started from inside `checkAllLoaded`'s
`setTimeout` block. It doesn't go through the generic navigator (it's a
one-shot full-screen click target, not a focusable list) — it just shows
"Click or Press [glyph] to Start" and clicks through on any button press.

## `isAnyMenuOpen()` — what counts as "a menu is open"

(~14794) Checked in priority order: pause overlay → victory/defeat report
(`gameOver` flag → `#victoryContinueBtn`, appended straight to `<body>`,
not part of `MENU_SCREENS`) → `MENU_SCREENS` list → multiplayer lobby
sub-views → main menu → `null`. The victory-screen case exists because
without it a controller-only player reaches the post-match report and has
literally no way to press Continue (`pollGamepadInput()` also stops the
moment `gameOver` is true). If you add a new full-screen DOM overlay that a
controller-only player must be able to dismiss, it needs an entry here.

## Focusable-element visibility check

`getNavFocusables(root)` (~3745) filters candidates with:

```js
el.offsetWidth > 0 || el.offsetHeight > 0 || el.getClientRects().length > 0
```

**Not** `el.offsetParent !== null`, which was tried first and has a
documented false negative for `position: fixed` elements (the victory
Continue button is `position: fixed`, appended to `<body>`) — it silently
excluded it from the focusable list even though it was visibly on screen.

## Remembered focus position

`_navLastIndexByRoot` (~3761), a `WeakMap<rootElement, index>`. On a
root-change, `pollGamepadMenuNav()` restores the remembered index (clamped
to the new list length) instead of resetting to 0 — added because
navigating away from and back to a screen with the default reset-to-0
behavior was reported as "a bit annoying" during live testing.

## Cursor hiding + the mousemove race

`body.gp-cursor-hidden` (CSS, hides the OS cursor) is toggled inside
`setLastInputMode()` whenever mode flips to `'pad'`. The `mousemove`
listener that flips back to `'keyboard'` requires a **>3px delta from the
last recorded position**, not just any mousemove event:

```js
let _lastMouseX = null, _lastMouseY = null;
document.addEventListener('mousemove', (e) => {
    if (window._hudForceType) return;
    const moved = _lastMouseX === null || Math.abs(e.clientX - _lastMouseX) > 3 || Math.abs(e.clientY - _lastMouseY) > 3;
    _lastMouseX = e.clientX; _lastMouseY = e.clientY;
    if (!moved) return;
    if (window._lastInputMode !== 'keyboard') { setLastInputMode('keyboard'); }
}, true);
```

Without the threshold, spurious near-zero-delta mousemove events (trackpad
sensor noise, a resting hand, or the browser re-dispatching one on unrelated
DOM changes) fought a controller that was actively being used: every real
button press flipped to `'pad'`, then an incidental mousemove immediately
flipped it back, so pad glyphs and the hidden cursor never visibly stuck.

## Vendor detection and glyph labels

`detectPadType(id)` (~4095) matches the `Gamepad.id` string against
vendor-ID / name regexes (`playstation`, `nintendo`, `xbox`, else
`'generic'`). **Note:** it looks for vendor IDs like `054c` (Sony),
`057e` (Nintendo), `045e` (Microsoft) as hex substrings — a fake/test pad
ID needs the real vendor ID substring present, not just a friendly name, to
be classified correctly (`"54c-268-PS4 Controller"` does NOT match; a real
DualSense reports something like `"...Vendor: 054c Product: 0ce6"` and
does).

`PAD_LABELS` (~4103) maps button index → label per vendor:

```js
const PAD_LABELS = {
    xbox:        { 0: 'A', 1: 'B', 2: 'X', 3: 'Y', 5: 'RB' },
    playstation: { 0: 'Cross', 1: 'Circle', 2: 'Square', 3: 'Triangle', 5: 'R1' },
    nintendo:    { 0: 'B', 1: 'A', 2: 'Y', 3: 'X', 5: 'R' },   // Nintendo swaps A/B and X/Y
    generic:     { 0: 'Bottom', 1: 'Right', 2: 'Left', 3: 'Top', 5: 'R1' },
};
```

`padGlyphHTML(type, idx)` (~3940, DOM-only) renders colored glyph chips for
known vendors and falls back to plain letters (A/B/X/Y) for `'generic'` —
previously ambiguous directional arrows, changed after live-testing
feedback ("if you can't get the real glyph just put plain text").

## Button/axis index mapping (`GP`, ~3625)

```js
const GP = { slot0: 2, slot1: 0, slot2: 1, ult: 3, parry: 5, dpadUp: 12, dpadDown: 13, stickY: 1 };
```

Index-based (Standard Gamepad layout), not vendor-label-based — this is why
Nintendo's A/B swap doesn't require any special-casing anywhere else in the
code: `GP.slot1 = 0` always means "the bottom-face button," and only the
*label* shown for index 0 changes per vendor via `PAD_LABELS`.

## Known gaps / explicitly out of scope

- No on-screen keyboard for text entry (player name, join code) — unchanged
  from the original design's scope.
- Mode-select screen and the backtick debug menu remain out of scope.
- Single controller only; no player-2 menu control.
- Safari is deprioritized for this project generally — controller work was
  only tested in Chrome.

## If you need to add a new controller-aware UI surface

1. Write its refresh function (`updateXInputHints()` or similar), following
   whichever pattern fits — DOM (`padGlyphHTML`, HTML glyph chips) or
   Babylon GUI (`PAD_LABELS` plain text only).
2. Expose it as `window.updateXInputHints`.
3. Add one defensive line inside `setLastInputMode()`:
   `if (window.updateXInputHints) updateXInputHints();`
4. Do **not** add refresh calls at the mode-flipping call sites — that's
   the exact pattern that let the COMMAND window go unwired for an entire
   playtesting session.
