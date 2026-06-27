# Main-Menu Additions (Settings + companion screens) — Design

**Date:** 2026-06-27
**Project:** Volleybolt
**Status:** Approved (pending spec review)

## Goal

Add the standard "boring but necessary" main-menu features the game is missing: a real
**Settings** screen plus **How to Play**, **Career**, and **Credits** screens. Reuse the existing
arcane menu system so everything matches the FF9 title-screen look.

## Decisions (locked)

- **Main menu = flat list:** `Start Battle · Multiplayer · Settings · How to Play · Career · Credits`.
  Each new entry opens its own arcane screen with a **Back** button.
- **Audio controls:** Master + Music + SFX (three sliders) — requires splitting the single audio
  master into separate music/SFX buses.
- **Graphics controls:** **Fullscreen toggle only.** The CRT/PS1 aesthetic stays always-on (core to
  the look); no CRT/PS1/UI-scale toggles in this pass.
- **Controls screen:** display-only (no key remapping). Control scheme is small and fixed.
- **Settings is reachable from the pause menu too** (Esc), so audio is tweakable mid-match.
- **Remove** the floating `#volumeControl` HUD widget — the Settings screen owns audio now.
- **Persistence:** `localStorage['volleybolt_settings']`, applied on boot, saved on change.

## Architecture

Everything is built on the **existing arcane menu system** (`.arcane-overlay` + `.arcane-scrim` +
Ferrum `.arcane-title` + gold `.menu-btn` items + Back), exactly like `#domModeSelect` and the
multiplayer lobby. Each new screen is its own DOM overlay **inside `#gameContainer`** (so it's scoped
to the 16:9 viewport, not the window).

**Single-screen nav helper.** Reuse the show-one/hide-others pattern that already fixed the
bleed-through bug: a small helper that, when opening a menu screen, hides the main menu and every
other menu screen and shows the target; Back returns to the main menu via the same helper. New
screens register with this helper so we never show two arcane overlays at once.

### Files

- `index.html` — all UI is in this monolith. Add the four screen markup blocks (inside
  `#gameContainer`, alongside `#domMenu` / `#domModeSelect`), the new main-menu buttons, the
  `Settings` module + audio-bus wiring, the nav helper, and the pause-menu Settings entry. Remove the
  `#volumeControl` widget markup + its wiring.
- `styles.css` — minor additions for Settings rows (slider rows, toggle rows) and the static
  How-to-Play / Career / Credits layouts. Reuse existing `.arcane-*` / `.menu-btn` styles; bump the
  `styles.css?v=NN` cache-bust.

## Components

### 1. Settings screen (`#settingsScreen`)

Arcane overlay. Title "Settings". Two labelled sections then a Back button:

- **Audio**
  - **Master** slider (0–100)
  - **Music** slider (0–100)
  - **SFX** slider (0–100)
- **Graphics**
  - **Fullscreen** toggle (on/off)

Each control applies live and writes to the `Settings` module (which persists). Sliders reuse the
existing range-input styling; the toggle is a simple on/off control styled to match.

### 2. How to Play (`#howToPlayScreen`)

Static arcane overlay. A keybind list and a one-line objective:

```
W / S        Move
1 / 2 / 3    Cast spell
Space        Parry
Block and parry incoming spells to destroy the enemy tower.
```

### 3. Career (`#careerScreen`)

Arcane overlay that, on show, reads the existing `StatTracker` career stats from
`localStorage['volleybolt_career_stats']` and renders a labelled list, e.g.:

```
Matches Won      <n>
Matches Lost     <n>
Spells Cast      <n>
Parries          <n>
Perfect Rounds   <n>
```

Exact rows come from whatever keys `StatTracker` already persists; render all meaningful career
counters it exposes. No new tracking is added in this pass.

### 4. Credits (`#creditsScreen`)

Static arcane overlay: game title, tagline, tech line (Babylon.js, Tone.js, PeerJS), year.

## Audio bus change (the one real engineering piece)

Today all audio routes to `Tone.getDestination()` and a single `setMasterVolume()` controls
everything. To get independent Master/Music/SFX:

1. Create two `Tone.Volume` nodes at audio init: **musicBus** and **sfxBus**, each connected to
   `Tone.getDestination()`. (Use `Tone.Volume`, not `Tone.Gain`, so all three controls share the same
   dB-based mapping as the existing master.)
2. Route `synths.music` → `musicBus`. Route every SFX synth/sample (the rest of `synths.*` and
   `synths.samples.*`) → `sfxBus`. Each source's existing per-sound `volume.value` (its mix level) is
   preserved; the bus only applies the user's group volume on top.
3. Volume mapping (0–100 slider → dB), used identically for all three:
   `vol === 0 ? -Infinity : 20 * Math.log10(vol / 100)`.
   - **Master** → `Tone.getDestination().volume.value` (keep `setMasterVolume`).
   - **Music** → `musicBus.volume.value`.
   - **SFX** → `sfxBus.volume.value`.
4. Apply all three saved values on boot.

If routing every SFX source individually is impractical, the acceptable fallback is a single shared
SFX output node that all non-music sources already pass through; route that node → `sfxBus`. The
implementation plan will confirm the exact wiring point against the current `synths` graph.

## Settings model + persistence

A small `Settings` object/module:

```
{ master: 50, music: 50, sfx: 50, fullscreen: false }   // defaults
```

- **Load** on boot from `localStorage['volleybolt_settings']` (try/catch; fall back to defaults on
  missing/corrupt), then **apply** (set the three bus/master volumes; sync the fullscreen toggle's
  displayed state to actual fullscreen — do not force-enter fullscreen on load).
- **Save** the whole object on any change.
- Migrate the existing `localStorage['volleybolt_volume']` value into `settings.master` once if
  present (so users don't lose their volume), then it's superseded.

## Access points

- **Main menu** → Settings button (and How to Play / Career / Credits).
- **Pause menu** (Esc during a match) → add a **Settings** entry that opens the same
  `#settingsScreen` overlay on top of the pause state; Back returns to the pause menu (not the main
  menu) when opened from pause. The screen tracks where it was opened from so Back routes correctly.

## Error handling

- All `localStorage` reads/writes wrapped in try/catch (matches existing `StatTracker` /
  volume-persistence pattern).
- Fullscreen via the Fullscreen API; the toggle reflects **actual** state via a `fullscreenchange`
  listener (so it stays correct if the user exits fullscreen with Esc/F11). If the request rejects
  (blocked context), the toggle reverts to off.

## Testing (manual)

- Each screen opens from the main menu, Back returns to the main menu, only one arcane overlay is
  ever visible (no bleed-through).
- Master/Music/SFX sliders change their group's volume live; reload preserves them.
- Music slider affects only music; SFX slider affects only SFX (verify by moving one to 0).
- Fullscreen toggle enters/exits fullscreen; exiting via Esc updates the toggle.
- Settings opens from the pause menu mid-match; Back returns to pause.
- Career screen shows real saved numbers (play a match, return, see counters change).
- The old floating volume widget is gone and nothing references it.

## Out of scope (this pass)

- Key remapping; CRT/PS1/UI-scale toggles; difficulty/gameplay options; per-screen animations beyond
  what the arcane system already provides.
