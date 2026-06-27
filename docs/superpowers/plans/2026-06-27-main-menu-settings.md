# Main-Menu Additions (Settings + companion screens) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Settings screen (Master/Music/SFX audio + Fullscreen) plus How to Play, Career, and Credits screens to the main menu, reusing the existing arcane menu system.

**Architecture:** Everything lives in the `index.html` monolith + `styles.css`. New screens are DOM `.arcane-overlay` blocks inside `#gameContainer` (like `#domModeSelect`), shown one-at-a-time by a nav helper. Audio's single master is split into `musicBus`/`sfxBus` (`Tone.Volume`) so Music/SFX volumes are independent. A small `Settings` module persists `{master, music, sfx, fullscreen}` to `localStorage`.

**Tech Stack:** Vanilla JS, Babylon.js GUI (not used here), Tone.js (audio), DOM/CSS for menus. No build step, no test framework.

## Global Constraints

- All code goes in `C:\Users\andre\Volleybolt\index.html` and `C:\Users\andre\Volleybolt\styles.css` (single-file monolith + stylesheet). No new files.
- **No test framework exists.** Verify by serving the folder (`python -m http.server 8000` from the repo root) and loading `http://localhost:8000/index.html?cb=<n>` in a browser; check the devtools console for `0 errors` and run the given `evaluate` expressions in the console. Visual layout is confirmed by the user (per project convention, do not burn tokens driving the game for visuals — ask the user to look).
- Reuse the arcane menu system: `.arcane-overlay crt-screen` container, `.arcane-scrim` + `.arcane-embers`, `.arcane-content` > `.arcane-title-wrap` (`.arcane-title` with `data-text`), `.arcane-buttons`. Buttons are `<button class="game-btn menu-btn">` with a `<span class="menu-btn-label">` for text (use `setMenuBtnLabel(btn, text)` for dynamic text).
- **Only one arcane overlay may be `.visible` at a time** (preserves the bleed-through fix). The nav helper enforces this.
- Persist settings to `localStorage['volleybolt_settings']` as JSON. All localStorage access wrapped in try/catch.
- Volume mapping (0–100 → dB), identical for all three controls: `vol === 0 ? -Infinity : 20 * Math.log10(vol / 100)`.
- When editing `styles.css`, bump the cache-bust in `index.html` (`<link rel="stylesheet" href="styles.css?v=NN">` — currently `v=46`).
- Keep the FF9/Ferrum aesthetic; gold accent is `#f0c050` / `var(--ff9-gold)`.

---

### Task 1: Audio Music/SFX buses

Split the single Tone.js master into independent music and SFX buses so their volumes can be controlled separately.

**Files:**
- Modify: `index.html` — inside `doToneInit()` (starts at line ~3333). Reroute `therapyPanner` (~3344), `chipPanner` (~3428), `musicBitCrusher` (~3510); add bus creation + `setMusicVolume`/`setSfxVolume`.

**Interfaces:**
- Consumes: `Tone` (global), `setMasterVolume(vol)` (existing, line ~3114).
- Produces: globals `window.musicBus`, `window.sfxBus` (`Tone.Volume` nodes); `window.setMusicVolume(vol0to1)`, `window.setSfxVolume(vol0to1)` — set the bus `.volume.value` in dB; no-op if the bus isn't created yet (audio not started).

- [ ] **Step 1: Create the two buses at the top of `doToneInit`, after `Tone.start()` succeeds.**

In `index.html`, find (line ~3342–3344):

```javascript
            // Stereo panner for therapy sounds (controlled by X position)
            therapyPanner = new Tone.Panner(0).toDestination();
```

Replace with:

```javascript
            // Group buses: music (ambient/therapy + music track) and SFX (chip sounds) each
            // feed the master destination, so their volumes can be controlled independently.
            window.musicBus = new Tone.Volume(0).toDestination();
            window.sfxBus = new Tone.Volume(0).toDestination();

            // Stereo panner for therapy sounds (controlled by X position) -> music bus (ambient).
            therapyPanner = new Tone.Panner(0).connect(window.musicBus);
```

- [ ] **Step 2: Reroute the chip (SFX) terminal node to the SFX bus.**

Find (line ~3428):

```javascript
            chipPanner = new Tone.Panner(0).toDestination();
```

Replace with:

```javascript
            chipPanner = new Tone.Panner(0).connect(window.sfxBus);
```

- [ ] **Step 3: Reroute the music track terminal node to the music bus.**

Find (line ~3510):

```javascript
            const musicBitCrusher = new Tone.BitCrusher(8).toDestination();  // Direct to output, no panning
```

Replace with:

```javascript
            const musicBitCrusher = new Tone.BitCrusher(8).connect(window.musicBus);  // -> music bus
```

- [ ] **Step 4: Add the volume setters right after `setMasterVolume` (after line ~3130, `window.setMasterVolume = setMasterVolume;`).**

```javascript
        // Group-volume setters (0-1). No-op until the buses exist (audio starts on first input).
        function volToDb(vol) { return vol <= 0 ? -Infinity : 20 * Math.log10(vol); }
        function setMusicVolume(vol) { if (window.musicBus) window.musicBus.volume.value = volToDb(vol); }
        function setSfxVolume(vol)   { if (window.sfxBus)   window.sfxBus.volume.value   = volToDb(vol); }
        window.setMusicVolume = setMusicVolume;
        window.setSfxVolume = setSfxVolume;
```

- [ ] **Step 5: Verify — reload and check audio still works + buses exist after interaction.**

Serve the repo (`python -m http.server 8000`) and load `http://localhost:8000/index.html?cb=t1`. Click "Click to Start" (initializes audio). In the console:

```javascript
({ music: typeof window.musicBus, sfx: typeof window.sfxBus,
   setMusic: typeof window.setMusicVolume, setSfx: typeof window.setSfxVolume })
```

Expected: `{ music: "object", sfx: "object", setMusic: "function", setSfx: "function" }`, console shows **0 errors**, and game audio (start a match, cast a spell) still plays.

- [ ] **Step 6: Verify independence — muting one bus does not affect the other.**

In the console during a match:

```javascript
window.setMusicVolume(0);   // music/ambient silenced; SFX (spell casts, parry) still audible
window.setSfxVolume(0);     // now SFX silenced too
window.setMusicVolume(0.5); window.setSfxVolume(0.5);  // restore
```

Expected: music goes silent independently of SFX; no console errors.

- [ ] **Step 7: Commit.**

```bash
git add index.html
git commit -m "feat(audio): split master into independent music/SFX Tone.Volume buses"
```

---

### Task 2: Settings model (persistence + apply)

A small module that loads/saves `{master, music, sfx, fullscreen}` and applies the audio values, migrating the legacy `volleybolt_volume`.

**Files:**
- Modify: `index.html` — add the `Settings` module near the other persistence code (right after `window.setSfxVolume = setSfxVolume;` from Task 1, ~line 3136). Add an apply-call at the end of `doToneInit`.

**Interfaces:**
- Consumes: `setMasterVolume(vol)`, `setMusicVolume(vol)`, `setSfxVolume(vol)` (Task 1), `localStorage`.
- Produces: `window.Settings` with: `Settings.values` (`{master,music,sfx,fullscreen}`, numbers 0–100 for audio, bool for fullscreen), `Settings.load()`, `Settings.save()`, `Settings.set(key, value)` (updates + applies that one setting + saves), `Settings.applyAudio()` (pushes master/music/sfx to the audio setters). Audio values are 0–100; the setters take 0–1, so `Settings.applyAudio` divides by 100.

- [ ] **Step 1: Add the `Settings` module after the Task-1 setters (after `window.setSfxVolume = setSfxVolume;`).**

```javascript
        // ---- Persistent player settings (audio + fullscreen) -> localStorage ----
        const Settings = (() => {
            const KEY = 'volleybolt_settings';
            const DEFAULTS = { master: 50, music: 50, sfx: 50, fullscreen: false };
            const values = { ...DEFAULTS };

            function load() {
                try {
                    const raw = localStorage.getItem(KEY);
                    if (raw) {
                        const saved = JSON.parse(raw);
                        for (const k of Object.keys(DEFAULTS)) {
                            if (saved[k] !== undefined) values[k] = saved[k];
                        }
                    } else {
                        // One-time migration of the old single-volume key into master.
                        const oldVol = localStorage.getItem('volleybolt_volume');
                        if (oldVol !== null) values.master = Math.max(0, Math.min(100, parseInt(oldVol, 10) || 50));
                    }
                } catch (e) { console.warn('Settings: load failed', e); }
                return values;
            }
            function save() {
                try { localStorage.setItem(KEY, JSON.stringify(values)); }
                catch (e) { console.warn('Settings: save failed', e); }
            }
            function applyAudio() {
                if (window.setMasterVolume) window.setMasterVolume(values.master / 100);
                if (window.setMusicVolume) window.setMusicVolume(values.music / 100);
                if (window.setSfxVolume)   window.setSfxVolume(values.sfx / 100);
            }
            function set(key, value) {
                values[key] = value;
                if (key === 'master') { if (window.setMasterVolume) window.setMasterVolume(value / 100); }
                else if (key === 'music') { if (window.setMusicVolume) window.setMusicVolume(value / 100); }
                else if (key === 'sfx')   { if (window.setSfxVolume)   window.setSfxVolume(value / 100); }
                save();
            }
            return { values, load, save, applyAudio, set };
        })();
        window.Settings = Settings;
        Settings.load();   // load on boot; audio applied when Tone initializes (see doToneInit)
```

- [ ] **Step 2: Apply audio settings when Tone finishes initializing.**

In `doToneInit`, find the music bus creation from Task 1 (the `synths.music = ...` block ends ~line 3523). At the END of `doToneInit` (just before its closing `}` / after all synths are built — find the last synth/setup line in the function, before `toneInitializing = false` or the function's closing brace), add:

```javascript
            // Push persisted volumes onto the freshly-created buses/master.
            if (window.Settings) window.Settings.applyAudio();
```

(If unsure where the function ends, search for the next top-level `function ` after `doToneInit` and place this line immediately before `doToneInit`'s closing brace.)

- [ ] **Step 3: Verify — settings persist and apply.**

Reload `http://localhost:8000/index.html?cb=t2`, click to start. Console:

```javascript
window.Settings.set('music', 0); window.Settings.values
```

Expected: `{ master: 50, music: 0, sfx: 50, fullscreen: false }`; music/ambient goes silent.

Then reload `?cb=t2b` and click to start. Console:

```javascript
window.Settings.values.music
```

Expected: `0` (persisted across reload). Restore: `window.Settings.set('music', 50)`. 0 console errors.

- [ ] **Step 4: Commit.**

```bash
git add index.html
git commit -m "feat(settings): add persistent Settings model (audio + fullscreen)"
```

---

### Task 3: Menu nav helper + Settings screen

The first arcane screen + the show-one-at-a-time helper that all four new screens use, wired to `Settings`, opened from a new main-menu button.

**Files:**
- Modify: `index.html` — add `#settingsScreen` markup inside `#gameContainer` (after `#domModeSelect`, ~line 166); add a "Settings" button to `#domMenuButtons` (~line 118–129); add the nav helper + settings wiring (near `wireDOMMenu`, ~line 14806).
- Modify: `styles.css` — settings rows/sliders/toggle styles; bump `?v=` in `index.html`.

**Interfaces:**
- Consumes: `setDOMMenuVisible(show)` (~14872), `setMenuBtnLabel` (~14670), `Settings` (Task 2), `#pauseOverlay` (for Task 4).
- Produces: `showMenuScreen(id, from = 'menu')` and `closeMenuScreen()` globals; `#settingsScreen` overlay; main-menu `#domBtnSettings`.

- [ ] **Step 1: Add the "Settings" button to the main menu.**

In `index.html`, find `#domMenuButtons` (the `Multiplayer` button block ends ~line 128 with `</button>` then `</div>`). After the Multiplayer `</button>`, add:

```html
                <button class="game-btn menu-btn" id="domBtnSettings">
                    <span class="menu-btn-accent" aria-hidden="true"></span>
                    <span class="menu-btn-glyph" aria-hidden="true">&#9881;</span>
                    <span class="menu-btn-label">Settings</span>
                </button>
```

- [ ] **Step 2: Add the `#settingsScreen` overlay markup after `#domModeSelect`'s closing `</div>` (~line 166), inside `#gameContainer`.**

```html
    <!-- Settings screen — arcane menu system (Audio + Graphics) -->
    <div id="settingsScreen" class="arcane-overlay crt-screen">
        <div class="arcane-scrim">
            <div class="arcane-embers" aria-hidden="true">
                <span class="ember"></span><span class="ember"></span><span class="ember"></span>
                <span class="ember"></span><span class="ember"></span><span class="ember"></span>
                <span class="ember"></span><span class="ember"></span><span class="ember"></span>
            </div>
        </div>
        <div class="arcane-content">
            <div class="arcane-title-wrap">
                <h1 class="arcane-title" data-text="Settings">Settings</h1>
            </div>
            <div class="arcane-buttons settings-panel">
                <div class="settings-section-label">Audio</div>
                <label class="settings-row"><span>Master</span>
                    <input type="range" class="settings-slider" id="setMaster" min="0" max="100"></label>
                <label class="settings-row"><span>Music</span>
                    <input type="range" class="settings-slider" id="setMusic" min="0" max="100"></label>
                <label class="settings-row"><span>SFX</span>
                    <input type="range" class="settings-slider" id="setSfx" min="0" max="100"></label>
                <div class="settings-section-label">Graphics</div>
                <label class="settings-row"><span>Fullscreen</span>
                    <input type="checkbox" class="settings-toggle" id="setFullscreen"></label>
                <button class="game-btn menu-btn menu-btn-ghost" id="settingsBack">
                    <span class="menu-btn-accent" aria-hidden="true"></span>
                    <span class="menu-btn-glyph" aria-hidden="true">&#8249;</span>
                    <span class="menu-btn-label">Back</span>
                </button>
            </div>
        </div>
    </div>
```

- [ ] **Step 3: Add CSS for the settings rows in `styles.css` (append near the end, before any closing media query — append at end of file is fine).**

```css
/* ---- Settings screen rows ---- */
.settings-panel { gap: 10px; align-items: stretch; min-width: 420px; }
.settings-section-label {
    font-family: 'FF9UI', sans-serif; font-size: 22px; color: var(--ff9-gold);
    text-shadow: var(--ff9-shadow); margin-top: 8px; letter-spacing: 1px; text-align: left;
}
.settings-row {
    display: flex; align-items: center; justify-content: space-between; gap: 16px;
    font-family: 'FF9UI', sans-serif; font-size: 22px; color: #e7ecf6;
    text-shadow: var(--ff9-shadow); padding: 2px 4px;
}
.settings-row > span { min-width: 110px; text-align: left; }
.settings-slider { flex: 1; accent-color: var(--ff9-gold); height: 6px; cursor: pointer; }
.settings-toggle { width: 22px; height: 22px; accent-color: var(--ff9-gold); cursor: pointer; }
```

- [ ] **Step 4: Bump the stylesheet cache-bust.**

In `index.html`, change `<link rel="stylesheet" href="styles.css?v=46">` to `href="styles.css?v=47"`.

- [ ] **Step 5: Add the nav helper + settings wiring (in `index.html`, right after `window.setDOMMenuVisible = setDOMMenuVisible;`, ~line 14889).**

```javascript
        // ---- Shared menu-screen nav: show ONE arcane screen at a time (no bleed-through). ----
        const MENU_SCREENS = ['settingsScreen', 'howToPlayScreen', 'careerScreen', 'creditsScreen'];
        let _menuScreenReturn = 'menu';   // where Back goes: 'menu' or 'pause'
        function hideAllMenuScreens() {
            MENU_SCREENS.forEach(id => { const el = document.getElementById(id); if (el) el.classList.remove('visible'); });
        }
        function showMenuScreen(id, from = 'menu') {
            _menuScreenReturn = from;
            if (from === 'menu') setDOMMenuVisible(false);
            if (from === 'pause') { const ov = document.getElementById('pauseOverlay'); if (ov) ov.style.display = 'none'; }
            hideAllMenuScreens();
            const el = document.getElementById(id);
            if (el) el.classList.add('visible');
        }
        function closeMenuScreen() {
            hideAllMenuScreens();
            if (_menuScreenReturn === 'pause') {
                const ov = document.getElementById('pauseOverlay'); if (ov) ov.style.display = 'flex';
            } else {
                setDOMMenuVisible(true);
            }
        }
        window.showMenuScreen = showMenuScreen;
        window.closeMenuScreen = closeMenuScreen;

        // ---- Settings screen wiring (one-shot) ----
        let settingsWired = false;
        function wireSettingsScreen() {
            if (settingsWired) return;
            const $ = (id) => document.getElementById(id);
            const master = $('setMaster'), music = $('setMusic'), sfx = $('setSfx'),
                  full = $('setFullscreen'), back = $('settingsBack');
            if (!master) return;
            settingsWired = true;
            master.addEventListener('input', e => Settings.set('master', parseInt(e.target.value, 10)));
            music.addEventListener('input',  e => Settings.set('music',  parseInt(e.target.value, 10)));
            sfx.addEventListener('input',    e => Settings.set('sfx',    parseInt(e.target.value, 10)));
            full.addEventListener('change', e => {
                const want = e.target.checked;
                if (want && document.documentElement.requestFullscreen) {
                    document.documentElement.requestFullscreen().catch(() => { e.target.checked = false; });
                } else if (!want && document.exitFullscreen && document.fullscreenElement) {
                    document.exitFullscreen().catch(() => {});
                }
            });
            // Keep the toggle in sync with actual fullscreen state (Esc/F11 exit).
            document.addEventListener('fullscreenchange', () => {
                full.checked = !!document.fullscreenElement;
                Settings.set('fullscreen', !!document.fullscreenElement);
            });
            back.addEventListener('click', () => closeMenuScreen());
        }
        function openSettings(from = 'menu') {
            wireSettingsScreen();
            document.getElementById('setMaster').value = Settings.values.master;
            document.getElementById('setMusic').value = Settings.values.music;
            document.getElementById('setSfx').value = Settings.values.sfx;
            document.getElementById('setFullscreen').checked = !!document.fullscreenElement;
            showMenuScreen('settingsScreen', from);
        }
        window.openSettings = openSettings;
```

- [ ] **Step 6: Wire the main-menu Settings button. In `wireDOMMenu` (~line 14807), after the `btnMP.addEventListener(...)` block (before the closing `}` of `wireDOMMenu`), add:**

```javascript
            const btnSettings = document.getElementById('domBtnSettings');
            if (btnSettings) btnSettings.addEventListener('click', () => openSettings('menu'));
```

- [ ] **Step 7: Verify — open Settings from the main menu, change volumes, fullscreen, Back.**

Reload `http://localhost:8000/index.html?cb=t3`, click to start (lands on main menu). Console:

```javascript
document.getElementById('domBtnSettings').click();
({ settings: document.getElementById('settingsScreen').classList.contains('visible'),
   menu: document.getElementById('domMenu').classList.contains('visible'),
   master: document.getElementById('setMaster').value })
```

Expected: `{ settings: true, menu: false, master: "50" }`. Then:

```javascript
const m = document.getElementById('setMusic'); m.value = 0; m.dispatchEvent(new Event('input'));
window.Settings.values.music
```

Expected: `0` (music goes silent). Then `document.getElementById('settingsBack').click();` →

```javascript
({ settings: document.getElementById('settingsScreen').classList.contains('visible'),
   menu: document.getElementById('domMenu').classList.contains('visible') })
```

Expected: `{ settings: false, menu: true }`. 0 console errors. **Ask the user to confirm the Settings screen looks right (title, rows, sliders, Back).**

- [ ] **Step 8: Commit.**

```bash
git add index.html styles.css
git commit -m "feat(menu): Settings screen (audio + fullscreen) + show-one-screen nav helper"
```

---

### Task 4: Settings from the pause menu

Let players open the same Settings screen mid-match from the Esc pause menu; Back returns to pause.

**Files:**
- Modify: `index.html` — `ensurePauseOverlay()` (~line 14178): add a Settings button + handler.

**Interfaces:**
- Consumes: `openSettings(from)` and `closeMenuScreen()` (Task 3), `#pauseOverlay`.
- Produces: `#pauseSettingsBtn`.

- [ ] **Step 1: Add a Settings button to the pause overlay markup.** In `ensurePauseOverlay`, find the resume/quit buttons (~line 14186–14187):

```javascript
                '<button id="pauseResumeBtn" class="game-btn menu-btn" style="display:block;width:240px;margin:10px auto">Resume</button>' +
                '<button id="pauseQuitBtn" class="game-btn menu-btn" style="display:block;width:240px;margin:10px auto">Quit to Menu</button>' +
```

Replace with (insert a Settings button between them):

```javascript
                '<button id="pauseResumeBtn" class="game-btn menu-btn" style="display:block;width:240px;margin:10px auto">Resume</button>' +
                '<button id="pauseSettingsBtn" class="game-btn menu-btn" style="display:block;width:240px;margin:10px auto">Settings</button>' +
                '<button id="pauseQuitBtn" class="game-btn menu-btn" style="display:block;width:240px;margin:10px auto">Quit to Menu</button>' +
```

- [ ] **Step 2: Wire the pause Settings button.** After the existing `ov.querySelector('#pauseResumeBtn')...` listener (~line 14190), add:

```javascript
            ov.querySelector('#pauseSettingsBtn').addEventListener('click', () => window.openSettings('pause'));
```

- [ ] **Step 3: Verify — open Settings from pause, Back returns to pause (not main menu).**

Reload `http://localhost:8000/index.html?cb=t4`, click to start, start a match (`window.startSinglesMatch()` in console, wait ~5s), then:

```javascript
GameSM.enterPause();
document.getElementById('pauseSettingsBtn').click();
({ settings: document.getElementById('settingsScreen').classList.contains('visible'),
   pauseShown: document.getElementById('pauseOverlay').style.display })
```

Expected: `{ settings: true, pauseShown: "none" }`. Then `document.getElementById('settingsBack').click();`:

```javascript
({ settings: document.getElementById('settingsScreen').classList.contains('visible'),
   pauseShown: document.getElementById('pauseOverlay').style.display,
   menu: document.getElementById('domMenu').classList.contains('visible') })
```

Expected: `{ settings: false, pauseShown: "flex", menu: false }` (back to pause, NOT the main menu). 0 console errors.

- [ ] **Step 4: Commit.**

```bash
git add index.html
git commit -m "feat(menu): open Settings from the pause menu (Back returns to pause)"
```

---

### Task 5: How to Play screen

Static keybind + objective screen.

**Files:**
- Modify: `index.html` — add `#howToPlayScreen` markup (after `#settingsScreen`), a main-menu button, and one wiring line.
- Modify: `styles.css` — `.htp-row` style; bump `?v=`.

**Interfaces:**
- Consumes: `showMenuScreen`, `closeMenuScreen` (Task 3).
- Produces: `#howToPlayScreen`, `#domBtnHowTo`.

- [ ] **Step 1: Add the main-menu button** (in `#domMenuButtons`, after the Settings button from Task 3):

```html
                <button class="game-btn menu-btn" id="domBtnHowTo">
                    <span class="menu-btn-accent" aria-hidden="true"></span>
                    <span class="menu-btn-glyph" aria-hidden="true">&#9874;</span>
                    <span class="menu-btn-label">How to Play</span>
                </button>
```

- [ ] **Step 2: Add the `#howToPlayScreen` overlay** (after `#settingsScreen`'s closing `</div>`):

```html
    <!-- How to Play screen -->
    <div id="howToPlayScreen" class="arcane-overlay crt-screen">
        <div class="arcane-scrim">
            <div class="arcane-embers" aria-hidden="true">
                <span class="ember"></span><span class="ember"></span><span class="ember"></span>
                <span class="ember"></span><span class="ember"></span><span class="ember"></span>
                <span class="ember"></span><span class="ember"></span><span class="ember"></span>
            </div>
        </div>
        <div class="arcane-content">
            <div class="arcane-title-wrap">
                <h1 class="arcane-title" data-text="How to Play">How to Play</h1>
            </div>
            <div class="arcane-buttons settings-panel">
                <div class="htp-row"><span class="htp-key">W / S</span><span>Move up / down</span></div>
                <div class="htp-row"><span class="htp-key">1 / 2 / 3</span><span>Cast Fireball / Frostbolt / Thunderstorm</span></div>
                <div class="htp-row"><span class="htp-key">Space</span><span>Parry an incoming spell</span></div>
                <div class="htp-row htp-objective">Block and parry the enemy's spells, then return fire to destroy their tower.</div>
                <button class="game-btn menu-btn menu-btn-ghost" id="howToBack">
                    <span class="menu-btn-accent" aria-hidden="true"></span>
                    <span class="menu-btn-glyph" aria-hidden="true">&#8249;</span>
                    <span class="menu-btn-label">Back</span>
                </button>
            </div>
        </div>
    </div>
```

- [ ] **Step 3: Add CSS** (append to `styles.css`):

```css
/* ---- How to Play rows ---- */
.htp-row {
    display: flex; align-items: baseline; gap: 18px;
    font-family: 'FF9UI', sans-serif; font-size: 22px; color: #e7ecf6;
    text-shadow: var(--ff9-shadow); text-align: left;
}
.htp-key { min-width: 130px; color: var(--ff9-gold); font-weight: 600; }
.htp-objective { display: block; margin-top: 10px; max-width: 520px; line-height: 1.5; }
```

Bump `styles.css?v=47` → `?v=48` in `index.html`.

- [ ] **Step 4: Wire the buttons** (in `wireDOMMenu`, after the Settings button wiring from Task 3):

```javascript
            const btnHowTo = document.getElementById('domBtnHowTo');
            if (btnHowTo) btnHowTo.addEventListener('click', () => showMenuScreen('howToPlayScreen', 'menu'));
            const howToBack = document.getElementById('howToBack');
            if (howToBack) howToBack.addEventListener('click', () => closeMenuScreen());
```

- [ ] **Step 5: Verify.** Reload `?cb=t5`, click to start. Console:

```javascript
document.getElementById('domBtnHowTo').click();
document.getElementById('howToPlayScreen').classList.contains('visible')
```

Expected: `true`. Then `document.getElementById('howToBack').click();` → re-check returns `false` and `document.getElementById('domMenu').classList.contains('visible')` is `true`. 0 errors. **Ask the user to confirm it reads well.**

- [ ] **Step 6: Commit.**

```bash
git add index.html styles.css
git commit -m "feat(menu): How to Play screen"
```

---

### Task 6: Credits screen

Static about/credits screen.

**Files:**
- Modify: `index.html` — `#creditsScreen` markup, main-menu button, wiring.
- Modify: `styles.css` — `.credits-line` style; bump `?v=`.

**Interfaces:**
- Consumes: `showMenuScreen`, `closeMenuScreen`.
- Produces: `#creditsScreen`, `#domBtnCredits`.

- [ ] **Step 1: Main-menu button** (in `#domMenuButtons`, after the How to Play button):

```html
                <button class="game-btn menu-btn" id="domBtnCredits">
                    <span class="menu-btn-accent" aria-hidden="true"></span>
                    <span class="menu-btn-glyph" aria-hidden="true">&#9733;</span>
                    <span class="menu-btn-label">Credits</span>
                </button>
```

- [ ] **Step 2: `#creditsScreen` overlay** (after `#howToPlayScreen`):

```html
    <!-- Credits screen -->
    <div id="creditsScreen" class="arcane-overlay crt-screen">
        <div class="arcane-scrim">
            <div class="arcane-embers" aria-hidden="true">
                <span class="ember"></span><span class="ember"></span><span class="ember"></span>
                <span class="ember"></span><span class="ember"></span><span class="ember"></span>
                <span class="ember"></span><span class="ember"></span><span class="ember"></span>
            </div>
        </div>
        <div class="arcane-content">
            <div class="arcane-title-wrap">
                <h1 class="arcane-title" data-text="Credits">Credits</h1>
            </div>
            <div class="arcane-buttons settings-panel">
                <div class="credits-line credits-title">Volleybolt</div>
                <div class="credits-line">An arcane volley duel.</div>
                <div class="credits-line">Built with Babylon.js, Tone.js &amp; PeerJS.</div>
                <div class="credits-line">&#169; 2026 Volleybolt</div>
                <button class="game-btn menu-btn menu-btn-ghost" id="creditsBack">
                    <span class="menu-btn-accent" aria-hidden="true"></span>
                    <span class="menu-btn-glyph" aria-hidden="true">&#8249;</span>
                    <span class="menu-btn-label">Back</span>
                </button>
            </div>
        </div>
    </div>
```

- [ ] **Step 3: CSS** (append to `styles.css`):

```css
/* ---- Credits ---- */
.credits-line {
    font-family: 'FF9UI', sans-serif; font-size: 22px; color: #e7ecf6;
    text-shadow: var(--ff9-shadow); text-align: center;
}
.credits-title { font-size: 30px; color: var(--ff9-gold); margin-bottom: 6px; }
```

Bump `styles.css?v=48` → `?v=49`.

- [ ] **Step 4: Wire** (in `wireDOMMenu`, after the How to Play wiring):

```javascript
            const btnCredits = document.getElementById('domBtnCredits');
            if (btnCredits) btnCredits.addEventListener('click', () => showMenuScreen('creditsScreen', 'menu'));
            const creditsBack = document.getElementById('creditsBack');
            if (creditsBack) creditsBack.addEventListener('click', () => closeMenuScreen());
```

- [ ] **Step 5: Verify.** Reload `?cb=t6`, click to start, `document.getElementById('domBtnCredits').click()` → `#creditsScreen` visible; Back → main menu visible. 0 errors. **User confirms visual.**

- [ ] **Step 6: Commit.**

```bash
git add index.html styles.css
git commit -m "feat(menu): Credits screen"
```

---

### Task 7: Career screen

Surface the existing persisted career stats.

**Files:**
- Modify: `index.html` — `#careerScreen` markup, main-menu button, wiring + populate from `StatTracker`.
- Modify: `styles.css` — `.career-row` style; bump `?v=`.

**Interfaces:**
- Consumes: `StatTracker.getAll('career')` → `{ [key]: number }`; `StatTracker.STAT_DEFINITIONS` → `{ [key]: { category, label, default } }`; `showMenuScreen`, `closeMenuScreen`.
- Produces: `#careerScreen`, `#domBtnCareer`, `#careerList`.

- [ ] **Step 1: Main-menu button** (in `#domMenuButtons`, after the Credits button):

```html
                <button class="game-btn menu-btn" id="domBtnCareer">
                    <span class="menu-btn-accent" aria-hidden="true"></span>
                    <span class="menu-btn-glyph" aria-hidden="true">&#9876;</span>
                    <span class="menu-btn-label">Career</span>
                </button>
```

- [ ] **Step 2: `#careerScreen` overlay** (after `#creditsScreen`). The list is populated by JS into `#careerList`:

```html
    <!-- Career stats screen -->
    <div id="careerScreen" class="arcane-overlay crt-screen">
        <div class="arcane-scrim">
            <div class="arcane-embers" aria-hidden="true">
                <span class="ember"></span><span class="ember"></span><span class="ember"></span>
                <span class="ember"></span><span class="ember"></span><span class="ember"></span>
                <span class="ember"></span><span class="ember"></span><span class="ember"></span>
            </div>
        </div>
        <div class="arcane-content">
            <div class="arcane-title-wrap">
                <h1 class="arcane-title" data-text="Career">Career</h1>
            </div>
            <div class="arcane-buttons settings-panel">
                <div id="careerList" class="career-list"></div>
                <button class="game-btn menu-btn menu-btn-ghost" id="careerBack">
                    <span class="menu-btn-accent" aria-hidden="true"></span>
                    <span class="menu-btn-glyph" aria-hidden="true">&#8249;</span>
                    <span class="menu-btn-label">Back</span>
                </button>
            </div>
        </div>
    </div>
```

- [ ] **Step 3: CSS** (append to `styles.css`):

```css
/* ---- Career list ---- */
.career-list { display: flex; flex-direction: column; gap: 4px; max-height: 46vh; overflow-y: auto; }
.career-row {
    display: flex; justify-content: space-between; gap: 24px; min-width: 420px;
    font-family: 'FF9UI', sans-serif; font-size: 20px; color: #e7ecf6; text-shadow: var(--ff9-shadow);
}
.career-row > .career-val { color: var(--ff9-gold); }
```

Bump `styles.css?v=49` → `?v=50`.

- [ ] **Step 4: Wire + populate** (in `wireDOMMenu`, after the Credits wiring):

```javascript
            const btnCareer = document.getElementById('domBtnCareer');
            if (btnCareer) btnCareer.addEventListener('click', () => { populateCareer(); showMenuScreen('careerScreen', 'menu'); });
            const careerBack = document.getElementById('careerBack');
            if (careerBack) careerBack.addEventListener('click', () => closeMenuScreen());
```

Add the `populateCareer` function just above `wireDOMMenu` (or anywhere in the same script scope), reading the real stat defs/values:

```javascript
        // Render the persisted career stats into #careerList (label : value rows).
        function populateCareer() {
            const list = document.getElementById('careerList');
            if (!list || !window.StatTracker) return;
            const defs = StatTracker.STAT_DEFINITIONS;
            const career = StatTracker.getAll('career');
            list.innerHTML = '';
            for (const [key, def] of Object.entries(defs)) {
                const row = document.createElement('div');
                row.className = 'career-row';
                const val = Math.round((career[key] || 0) * 100) / 100;   // freeze_time may be fractional
                row.innerHTML = '<span>' + def.label + '</span><span class="career-val">' + val + '</span>';
                list.appendChild(row);
            }
        }
```

- [ ] **Step 5: Verify — shows real persisted numbers.** Reload `?cb=t7`, click to start. Console:

```javascript
StatTracker.increment('matches_won', 1);   // bump a career stat
document.getElementById('domBtnCareer').click();
document.querySelector('#careerList').textContent.includes('Matches Won')
```

Expected: `true`, and the "Matches Won" row shows the incremented value. Back → main menu. 0 errors. **User confirms visual.**

- [ ] **Step 6: Commit.**

```bash
git add index.html styles.css
git commit -m "feat(menu): Career stats screen"
```

---

### Task 8: Remove the floating volume widget

The Settings screen now owns audio; remove the old top-corner master slider.

**Files:**
- Modify: `index.html` — remove `#volumeControl` markup (~lines 296–300) and its wiring (~lines 13804–13837).

**Interfaces:**
- Consumes: nothing new. (Master volume is already applied by `Settings.applyAudio()` from Task 2.)
- Produces: nothing.

- [ ] **Step 1: Remove the markup.** Delete these lines (~296–300):

```html
    <!-- Volume control: inside the scale layer so it scales with the game, not the browser -->
    <div id="volumeControl">
        <span id="volumeIcon">🔊</span>
        <input type="range" id="volumeSlider" min="0" max="100" value="50">
    </div>
```

- [ ] **Step 2: Remove the wiring.** Delete the volume-slider block from the comment `// Volume slider with localStorage persistence` (~13804) through the closing `});` of the `volumeIcon.addEventListener('click', ...)` handler (~13837). **Keep** the line immediately after it — the enclosing function's closing `}` (~13838) — and `function getCasterAimDir` (~13840). I.e. remove only the ~34 lines of the volume block, not the surrounding function brace.

- [ ] **Step 3: Verify — widget gone, no dangling refs, audio still works via Settings.**

Reload `http://localhost:8000/index.html?cb=t8`, click to start. Console:

```javascript
({ widget: document.getElementById('volumeControl'),
   slider: document.getElementById('volumeSlider') })
```

Expected: `{ widget: null, slider: null }`, **0 console errors** (no "volumeSlider is null"). Open Settings, change Master → audio responds. Start a match → audio plays at the saved master level.

- [ ] **Step 4: Commit.**

```bash
git add index.html
git commit -m "chore(audio): remove floating volume widget (Settings owns audio now)"
```

---

## Notes for the implementer

- **Order matters:** Task 1 → 2 establish the audio buses + Settings model that Task 3 wires to. Tasks 4–7 reuse the Task-3 nav helper. Task 8 is safe last (Master is applied by `Settings.applyAudio` once Task 2 lands).
- **CSS cache-bust:** each CSS-touching task bumps `styles.css?v=NN`. If tasks are reordered/skipped, just ensure the final value is unique and matches the link.
- **`wireDOMMenu` grows** across Tasks 3–7 (one button wiring each). They're independent `if (btn) btn.addEventListener(...)` lines — order among them doesn't matter.
- **Local server:** verification assumes the repo is served at `http://localhost:8000` (`python -m http.server 8000`). Audio + most wiring only initialize after the "Click to Start" gate, so click it before running console checks.
