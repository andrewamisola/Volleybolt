# Controller Menu Navigation + Prompt Bar — Design

**Date:** 2026-07-03
**Project:** Volleybolt
**Status:** Approved (pending spec review)

## Goal

Gamepad support today only covers live gameplay (movement, spells, parry) — every menu screen
(main menu, settings, how-to-play, credits, career, multiplayer lobby, pause) is mouse/click-only,
and there's no on-screen indication of what button does what. This adds:

1. Full D-pad/stick navigation across every menu screen.
2. A persistent, context-aware button-prompt bar (bottom-right) showing what's currently doable.
3. A fix (or verified confirmation) that the in-game ability-bar glyphs actually swap to the
   connected pad's real buttons — the wiring exists but was reported not working.

## Decisions (locked)

- **One generic navigator, not eight bespoke ones.** A single module scans whichever screen is
  currently visible for its focusable elements and drives focus uniformly. New screens get
  navigation for free as long as their buttons/controls follow the existing DOM conventions.
- **Index-based button mapping**, matching how gameplay bindings already work: bottom face button
  (A / Cross / B-on-Nintendo) = confirm, right face button (B / Circle / A-on-Nintendo) = back,
  Start/Menu button = same as Escape. Labels differ by vendor; physical button indices don't.
- **Up/down moves focus, left/right adjusts** whatever's focused (slider, FPS cycler, or the
  How-to-Play page) — it never moves focus. Holding a direction auto-repeats after an initial
  delay, matching old console menu feel.
- **Focus visual = existing hover highlight + a small ▶ arrow**, the same glyph already used to
  mark the selected spell in the in-game command menu, so menu selection and battle-command
  selection read as the same visual language.
- **Prompt bar is data-driven and always visible in menus.** Each screen declares what's currently
  doable; the bar renders that, in keyboard-hint form by default and pad glyphs once a pad is
  touched. It does **not** appear during live gameplay — the ability bar already fills that role
  there.
- **Single shared "last input device" flag**, broadened from the existing ability-bar-only
  `_hudInputMode` into one global source of truth both the ability bar and the prompt bar read.
  Clicking with a mouse reverts it to keyboard-style hints; touching the pad flips it back.
- **Text inputs are skipped** by the navigator (player name field, multiplayer join code) — no
  on-screen keyboard in this pass. They're reachable by mouse/keyboard as today.

### Screens in scope

`#domMenu` (main menu) · `#settingsScreen` · `#howToPlayScreen` · `#creditsScreen` ·
`#careerScreen` · `#multiplayerLobby` (all four sub-views: mode/host/join/connected) ·
`#pauseOverlay`.

**Out of scope:** `#domModeSelect` (dormant — Start Battle currently bypasses it), the backtick
debug menu (dev-only, not player-facing).

## Architecture

### Files

- `index.html` — all logic lives in the existing inline script, alongside the current gamepad
  code (`GP`, `pollGamepadInput`, `detectPadType`, `padGlyphHTML`). New pieces:
  - `pollGamepadMenuNav()` — the generic navigator, polled every frame a menu/overlay is open.
  - `#gamepadPromptBar` — new DOM element + its render function.
  - `window.setGamepadPrompts(...)` — small per-screen API to declare the current button legend.
- `styles.css` — prompt bar styling (reuses the steel-panel HUD look already established for the
  command/status windows) and the `.gp-focused` focus-highlight class.

### Input polling split

Two independent polling functions, mutually exclusive by construction:

- `pollGamepadInput()` (existing) — runs only when `gameState === "playing"`. Untouched.
- `pollGamepadMenuNav()` (new) — runs whenever any in-scope menu/overlay is currently visible
  (checked via one small `isAnyMenuOpen()` helper covering `#domMenu`, `MENU_SCREENS`,
  `#multiplayerLobby`, `#pauseOverlay`). Hooked into the same always-running
  `scene.onBeforeRenderObservable` callback the menu-title guard already uses — proven to keep
  firing regardless of `gameState`, including in the menu state.

Neither runs during an active, unpaused match with no menu open (gameplay polling only) or while
any menu is open (menu-nav polling only) — there's no state where both or neither should apply.

### The generic navigator

On each poll, if a menu is open:

1. Query the CURRENT visible screen's focusable elements: `.menu-btn:not([disabled])`,
   `.settings-slider`, `.settings-toggle`, `.fps-arrow` (cycler treated as one focusable row, not
   two), skipping text inputs — in DOM order.
2. Track a `focusedIndex` per screen (reset to 0 whenever a screen opens).
3. D-pad/stick up/down moves `focusedIndex`, wraps at the ends, calls `element.focus()` (for
   scroll-into-view) and adds `.gp-focused` to the newly focused element, removes it from the
   previous one.
4. D-pad/stick left/right: if the focused element is a range input, calls its native
   `stepUp()`/`stepDown()` and dispatches a real `input`/`change` event (reuses the existing
   listener unchanged); if it's the FPS cycler, calls the existing prev/next handler directly; if
   the current screen is How-to-Play, calls the existing `htpSetPage()` directly. No-op otherwise.
5. Confirm button: synthesizes `.click()` on the focused element — reuses every existing handler
   unchanged, zero new click logic.
6. Back button: looks up the current screen's designated back-equivalent element (a small static
   table: `settingsScreen → settingsBack`, `howToPlayScreen → howToBack`, `creditsScreen →
   creditsBack`, `careerScreen → careerBack`, `pauseOverlay → pauseResumeBtn`, and for
   `multiplayerLobby` one entry per sub-view — `lobbyModeView → btnBackMenu`, `lobbyHostView →
   btnCancelHost`, `lobbyJoinView → btnCancelJoin`, `lobbyConnectedView → btnDisconnect`) and
   synthesizes a click on it. No-op on the main menu (nothing to back out of).
7. Start/Menu button: the existing Escape `keydown` handler's body is extracted into a named
   function so both the real Escape key and this button call the same logic — no duplicated
   pause/close routing.

### Prompt bar

`#gamepadPromptBar`, positioned `absolute` inside `#gameContainer` (not `position:fixed` on
`body` — the codebase already hit and documented the "sprawls past the centered viewport on
non-16:9 screens" bug from fixed-positioned overlays; this stays scoped to the letterboxed 16:9
frame like every other menu overlay). Bottom-right corner, `pointer-events: none` (purely
informational, never blocks a click).

`window.setGamepadPrompts([{ action: 'navigate', dpad: true }, { action: 'confirm', btn: 0 },
{ action: 'back', btn: 1 }])` — each in-scope screen calls this when it becomes visible (settings
additionally includes an `'adjust'` entry; how-to-play uses `'page'` instead of `'adjust'`). The
bar re-renders on every call and whenever the shared last-input-device flag flips, resolving each
entry to either a keyboard hint (Arrow keys / Enter / Esc) or the connected pad's real glyph via
the existing `padGlyphHTML`-style vendor lookup, extended to cover D-pad and Start/Back icons
(which the current function doesn't have yet — it only knows the four face buttons and one
shoulder button).

## Ability-bar glyph verification

The existing `updateHudInputHints()` mechanism looks correctly wired: `pollGamepadInput()` flips
`_hudInputMode` to `'pad'` and calls it the moment any mapped button is pressed during a match.
Before writing any fix, the implementation plan verifies this actually happens in a live match
with a real controller. If it's genuinely broken, the fix targets the real cause rather than
rebuilding the mechanism. This flag becomes the same shared one the prompt bar reads (see
Decisions above), so a single source of truth drives both.

## Error handling

- `isAnyMenuOpen()` and the focusable-element query both degrade to "no menu open" / empty list on
  any DOM lookup failure — the navigator simply does nothing rather than throwing, matching the
  defensive style already used throughout the gamepad code (`if (!navigator.getGamepads) return`).
- If a screen has zero focusable elements when opened (shouldn't happen, but e.g. a mid-refactor
  screen), up/down and confirm are no-ops rather than erroring.
- Disconnecting the pad mid-navigation: `pollGamepadMenuNav()` already no-ops when `navigator
  .getGamepads()` returns nothing (same guard the existing gameplay poller uses), so focus simply
  stops moving; the prompt bar and ability bar fall back to keyboard hints on the next input-mode
  check.

## Testing (manual)

- Every in-scope screen: reach it via mouse, then navigate its full length with a real Xbox
  controller (D-pad and stick), confirm each button with A, back out with B, confirm wrap-around
  at both ends.
- Settings: left/right adjusts Master/Music/SFX/Render-Res sliders and steps the FPS cycler;
  Fullscreen/Reduce Motion/Colorblind toggle with A; the name field is skipped over, not focusable.
- How-to-Play: left/right pages through the carousel while focused on the pager row.
- Multiplayer lobby: navigation works correctly across all four sub-views as they swap.
- Start button opens/closes pause during a match exactly like Escape; B does nothing on the main
  menu.
- Prompt bar: shows keyboard hints on load, swaps to the connected pad's real glyphs on first pad
  input, reverts to keyboard hints on the next mouse click; content changes correctly per screen
  (settings shows "Adjust", how-to-play shows "Page", others don't).
- Ability-bar glyphs: cast each of the three spells and parry with a real controller mid-match,
  confirm all four `.ability-key` slots show the pad's glyphs, not "1/2/3/Space".
- Play a full match using only the controller, start to finish, no mouse/keyboard — main menu →
  start battle → play → victory screen → continue, entirely pad-driven.

## Out of scope (this pass)

- Mode-select screen (dormant), debug menu (dev-only).
- Text-entry via gamepad (player name, join code) — no on-screen keyboard.
- Analog-stick acceleration curves for repeat-rate — a flat delay-then-repeat is enough.
- Real keyboard Tab-navigation for menus — a plausible side effect of using DOM focus internally,
  but not a design goal and not specifically tested here.
- Multiple simultaneous controllers / player-2 menu control.
