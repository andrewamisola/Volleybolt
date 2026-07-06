# Branding Pass — Art Bible & Asset Pack Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `brand/` (raw art-reference assets: character sheet, spell GIFs, world shots, UI) and the art bible page `brand/art-bible.html` — the reference pack external artists use to paint itch.io key art.

**Architecture:** All captures come from the REAL game renderer. Spell GIFs: a debug-only `dbg.capture` namespace in `index.html` blacks out the stage (hide env meshes + HUD, black clearColor, no fog) and streams canvas frames via POST to a local capture server; ffmpeg assembles GIFs. Character captures: a new standalone `capture_viewer.html` (derived from `pickle_viewer.html`) renders the pickle GLB clips on black. The art bible is a static HTML page styled with the game's own FF9-steel design system.

**Tech Stack:** Babylon.js (already in game), Python 3 stdlib (capture server), ffmpeg (on PATH at `/opt/homebrew/bin/ffmpeg`), browser automation via Playwright MCP or claude-in-chrome tools.

## Global Constraints

- **Zero sim/gameplay impact.** After ANY `index.html` edit, both goldens must hold: `dbg.determinism().fold === '954ea557'` (defaults: 180 frames, seed 12345 — MUST be run from a FRESH single-player match, not mid-PvP; seed 99999 cross-check → `'56c1c1ac'`) and `dbg.aiDeterminism(50, 42).fold === '8ea9157c'`. See `js/sim.js:20-24` for the oracle law.
- Team identity: **Blue left / Red right — never reversed** (spec + style guide hard rule).
- One gold accent: `#f0c050`. Element colors: fire `#ffa040`, frost `#80d0ff`, lightning `#ffff40`.
- Game is served at the FIXED origin `http://localhost:8080` (`play.command`). The capture server uses port **8090** so it never collides with a running play server. All capture-page URLs in this plan use `http://localhost:8090`.
- Intermediate frames go to `/private/tmp/claude-501/-Users-andrewamisola-Projects-Volleybolt/b2792772-682a-491d-9dc3-4accb2f33339/scratchpad/frames/` (call it `$FRAMES` below) — never committed.
- Final assets are committed under `brand/`. GIF target: ≤ 3 MB each, 30 fps, court-cropped.
- Lore text is marked **DRAFT** wherever it appears.
- Work on branch `branding/art-bible` off `master`.

---

### Task 1: Branch, folder skeleton, copy existing assets

**Files:**
- Create: `brand/character/`, `brand/spells/`, `brand/world/`, `brand/ui/` (via copied files)

**Interfaces:**
- Produces: `brand/` tree that Tasks 4-9 write into; canonical asset filenames listed below (later tasks reference them verbatim).

- [ ] **Step 1: Branch**

```bash
cd /Users/andrewamisola/Projects/Volleybolt
git checkout -b branding/art-bible
```

- [ ] **Step 2: Copy the assets that already exist**

```bash
mkdir -p brand/character brand/spells brand/world brand/ui
cp .pickle/pickle_wizard_v1.png   brand/character/pickle-2d-concept.png
cp .pickle/pickle_face.png        brand/character/pickle-face-sprite.png
cp screenshots/volleybolt-nohud-1-2880x1620.png brand/world/arena-wide-1.png
cp screenshots/volleybolt-nohud-2-2880x1620.png brand/world/arena-wide-2.png
cp screenshots/volleybolt-nohud-fireball-1920x1080.png brand/world/arena-fireball-rally.png
cp textures/fireball.png  brand/spells/tex-fireball.png
cp textures/frostbolt.png brand/spells/tex-frostbolt.png
cp textures/chainlightning.png brand/spells/tex-lightning.png
cp docs/superpowers/audits/blind-shots/02-main-menu-loaded.png brand/ui/main-menu.png
```

- [ ] **Step 3: Verify and commit**

Run: `find brand -type f | sort`
Expected: the 10 files above, no more.

```bash
git add brand && git commit -m "brand: folder skeleton + existing 2D/world/texture assets"
```

---

### Task 2: Capture server (static serve + frame sink)

**Files:**
- Create: `tools/capture_server.py`

**Interfaces:**
- Produces: HTTP server on `:8090` serving the repo root; `POST /save?name=<file>.png` with a `data:image/png;base64,...` body writes the decoded PNG to the directory given by `--out`. Tasks 3-6 POST frames to it.

- [ ] **Step 1: Write the server**

```python
#!/usr/bin/env python3
"""Serves the repo on :8090 and accepts POSTed canvas frames.

Usage: python3 tools/capture_server.py --out /path/to/frames
POST /save?name=fireball_0001.png with a data-URL body writes frames/fireball_0001.png
"""
import argparse, base64, os, re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--port', type=int, default=8090)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    class Handler(SimpleHTTPRequestHandler):
        def do_POST(self):
            u = urlparse(self.path)
            if u.path != '/save':
                self.send_error(404); return
            name = parse_qs(u.query).get('name', [''])[0]
            if not re.fullmatch(r'[A-Za-z0-9._-]+\.png', name):
                self.send_error(400, 'bad name'); return
            body = self.rfile.read(int(self.headers['Content-Length'])).decode('ascii')
            b64 = body.split(',', 1)[1] if ',' in body else body
            with open(os.path.join(args.out, name), 'wb') as f:
                f.write(base64.b64decode(b64))
            self.send_response(200); self.end_headers(); self.wfile.write(b'ok')
        def log_message(self, *a):  # keep terminal quiet during 60-frame bursts
            pass

    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()

if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Test it round-trip**

```bash
FRAMES="/private/tmp/claude-501/-Users-andrewamisola-Projects-Volleybolt/b2792772-682a-491d-9dc3-4accb2f33339/scratchpad/frames"
python3 tools/capture_server.py --out "$FRAMES" & sleep 1
# 1x1 red PNG as a data URL
curl -s -X POST "http://localhost:8090/save?name=test_0001.png" --data \
"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
file "$FRAMES/test_0001.png"
```

Expected: `test_0001.png: PNG image data, 1 x 1` and curl printed `ok`.
Also: `curl -s http://localhost:8090/index.html | head -1` returns `<!DOCTYPE html>` (static serving works).

- [ ] **Step 3: Commit**

```bash
rm "$FRAMES/test_0001.png"
git add tools/capture_server.py && git commit -m "brand: capture server (static serve + POST frame sink)"
```

---

### Task 3: `dbg.capture` stage in index.html

**Files:**
- Modify: `index.html` — insert immediately BEFORE the line `console.log('%c[Volleybolt] MP debug ready — dbg.help() for commands · F2 toggles the netcode overlay', 'color:#2f8f6f');` (currently line ~15589, right after the `dbg.aiDeterminism` block).

**Interfaces:**
- Consumes: top-level globals already in scope at that point: `scene` (let, line 778), `combatants`, `abilities`, `pendingNetInput`, `setHudHidden` (line 14082), `window.gameEngine` (line 4206), `window.spawnFireball` (11183), `window.spawnFrostbolt` (11379), `createSkyLightningStrike` (17587), `createZapFlash` (17672).
- Produces: `dbg.capture.stage()`, `.unstage()`, `.fireball(fromLeft)`, `.frostbolt(fromLeft)`, `.thunder(x, z)`, `.parry()`, `.record(name, frames, every)`, `.stop()` — Task 4 drives these from the browser console/automation.

- [ ] **Step 1: Insert the capture namespace**

```js
        // ---- Capture stage (branding / marketing) — dbg.capture.* ------------------
        // Presentation-side ONLY. Blacks the backdrop, hides env meshes + HUD, and
        // streams canvas frames to the local capture server (tools/capture_server.py,
        // POST /save). Spawns reuse the game's own window.spawn* / input paths and a
        // running SP match — the sim is never modified. Safe: not reachable from gameplay.
        window.dbg.capture = {
            _hidden: [], _obs: null,
            stage() {
                if (!scene || !combatants.left || !combatants.left.paddle) { console.warn('[capture] start a battle first'); return; }
                setHudHidden(true);
                scene.fogMode = BABYLON.Scene.FOGMODE_NONE;
                scene.clearColor = new BABYLON.Color4(0, 0, 0, 1);
                const keep = new Set();
                for (const side of ['left', 'right']) {
                    const p = combatants[side] && combatants[side].paddle;
                    if (!p) continue;
                    keep.add(p);
                    p.getChildMeshes().forEach(m => keep.add(m));
                }
                for (const m of scene.meshes.slice()) {
                    if (keep.has(m) || !m.isEnabled()) continue;
                    m.setEnabled(false);
                    this._hidden.push(m);
                }
                console.log('[capture] stage ON — hid ' + this._hidden.length + ' meshes');
            },
            unstage() {
                this.stop();
                this._hidden.forEach(m => m.setEnabled(true));
                this._hidden = [];
                console.log('[capture] stage OFF — reload the page to fully restore fog/clearColor');
            },
            fireball(fromLeft = true) {
                const c = combatants[fromLeft ? 'left' : 'right'];
                const dir = fromLeft ? 1 : -1;
                window.spawnFireball(fromLeft ? 'player' : 'ai',
                    c.paddle.position.x + dir, c.paddle.position.z,
                    dir * abilities.fireball.baseSpeed, 0);
            },
            frostbolt(fromLeft = true) {
                const c = combatants[fromLeft ? 'left' : 'right'];
                const dir = fromLeft ? 1 : -1;
                window.spawnFrostbolt(fromLeft ? 'player' : 'ai',
                    c.paddle.position.x + dir, c.paddle.position.z,
                    dir * abilities.frostbolt.baseSpeed, 0);
            },
            thunder(x = 0, z = 0) {
                const p = new BABYLON.Vector3(x, 0.6, z);
                createSkyLightningStrike(p);
                if (typeof createZapFlash === 'function') createZapFlash(p);
            },
            parry() { pendingNetInput.parry = true; },
            record(name, frames = 45, every = 2) {
                if (this._obs) { console.warn('[capture] already recording'); return; }
                const canvas = window.gameEngine.getRenderingCanvas();
                let tick = 0, saved = 0;
                this._obs = scene.onAfterRenderObservable.add(() => {
                    if (tick++ % every !== 0) return;
                    if (saved >= frames) { this.stop(); return; }
                    const idx = String(saved).padStart(4, '0');
                    // toDataURL inside onAfterRender is synchronous with the draw, so it
                    // works despite preserveDrawingBuffer:false on the engine.
                    fetch('/save?name=' + name + '_' + idx + '.png',
                          { method: 'POST', body: canvas.toDataURL('image/png') })
                        .catch(e => console.warn('[capture] save failed', e));
                    saved++;
                });
                console.log('[capture] recording ' + frames + ' frames of "' + name + '"');
            },
            stop() {
                if (!this._obs) return;
                scene.onAfterRenderObservable.remove(this._obs);
                this._obs = null;
                console.log('[capture] recording stopped');
            }
        };
```

Also append one line to the `dbg.help()` string array (line ~15452, after the `dbg.forceDesync` entry):

```js
                    'dbg.capture.*         branding capture stage (stage/record/fireball/frostbolt/thunder/parry)',
```

- [ ] **Step 2: Golden verification (MANDATORY)**

Serve via `python3 tools/capture_server.py --out "$FRAMES"`, open `http://localhost:8090/index.html` (Playwright MCP `browser_navigate` + `browser_run_code_unsafe`, or claude-in-chrome equivalents):

1. From the main menu run `dbg.aiDeterminism(50, 42).fold` → Expected: `"8ea9157c"`.
2. Start a FRESH single-player battle, then run `dbg.determinism().fold` → Expected: `"954ea557"`. Cross-check: `dbg.determinism(180, 99999).fold` → `"56c1c1ac"`.

If either differs, the edit touched something it must not have — STOP and fix before committing.

- [ ] **Step 3: Smoke-test the stage**

In the running battle: `dbg.freeze('right', 60); dbg.capture.stage(); dbg.capture.fireball(true);` then take one screenshot.
Expected: black background, both pickles visible, no towers/court/HUD, a fireball streaking right.

- [ ] **Step 4: Commit**

```bash
git add index.html && git commit -m "brand: dbg.capture stage — black-box capture mode + frame recorder (goldens verified 8f6e6da1 / 8ea9157c)"
```

---

### Task 4: Capture + assemble the four spell GIFs

**Files:**
- Create: `brand/spells/fireball.gif`, `brand/spells/frostbolt.gif`, `brand/spells/thunder.gif`, `brand/spells/parry.gif`

**Interfaces:**
- Consumes: `dbg.capture.*` (Task 3), capture server (Task 2).
- Produces: the four committed GIFs the art bible (Task 8) embeds by exactly these paths.

- [ ] **Step 1: Session setup**

Server already running on :8090 with `--out "$FRAMES"`. In the browser: load `http://localhost:8090/index.html`, Start Battle, wait for gameplay, then in console: `dbg.freeze('right', 600); dbg.capture.stage();`

- [ ] **Step 2: Record each spell**

Run each block in the console; wait for `[capture] recording stopped` between takes.

```js
// fireball — 60 frames @30fps = 2s of flight
dbg.capture.record('fireball', 60, 2); dbg.capture.fireball(true);
```
```js
dbg.capture.record('frostbolt', 60, 2); dbg.capture.frostbolt(true);
```
```js
// thunder strikes are brief — record first, fire three strikes across the court
dbg.capture.record('thunder', 60, 2);
dbg.capture.thunder(0, 0);
setTimeout(() => dbg.capture.thunder(2, 1.5), 600);
setTimeout(() => dbg.capture.thunder(-2, -1.5), 1200);
```
```js
// parry — incoming fireball from the right, parry as it arrives.
// Player paddle sits near x=-6.4; projectile speed = abilities.fireball.baseSpeed.
// Trigger parry slightly before impact; retake with adjusted delay until the
// deflection reads cleanly (this is a by-eye timing, expect 2-3 takes).
dbg.capture.record('parry', 75, 2);
dbg.capture.fireball(false);                       // from the RIGHT side, flying left
setTimeout(() => dbg.capture.parry(), 900);        // adjust 700-1100ms per take
```

Frame count check after each take: `ls "$FRAMES" | grep -c '^fireball_'` → Expected `60` (75 for parry).

- [ ] **Step 3: Assemble GIFs with ffmpeg (palette two-pass, court crop)**

The game canvas is 1920×1080; the court band is roughly the middle — start with `crop=1280:520:320:300` and adjust after eyeballing the first GIF (Read the PNG frames to pick the crop; the projectile path must stay fully inside).

```bash
cd "$FRAMES"
for name in fireball frostbolt thunder parry; do
  ffmpeg -y -framerate 30 -i "${name}_%04d.png" -vf \
    "crop=1280:520:320:300,split[a][b];[a]palettegen=stat_mode=diff[p];[b][p]paletteuse=dither=bayer" \
    "/Users/andrewamisola/Projects/Volleybolt/brand/spells/${name}.gif"
done
ls -la /Users/andrewamisola/Projects/Volleybolt/brand/spells/*.gif
```

Expected: four GIFs, each ≤ 3 MB (`bayer` dither also matches the game's PS1 look).

- [ ] **Step 4: Eyeball every GIF (MANDATORY)**

Read each GIF file (or open in browser). Checklist per GIF: black background; effect clearly legible; no HUD/env remnants; parry shows the deflection. Retake any failure (Step 2 + 3 for that spell only).

- [ ] **Step 5: Commit**

```bash
git add brand/spells && git commit -m "brand: spell GIFs — fireball, frostbolt, thunder, parry (black-plate captures)"
```

---

### Task 5: Character capture viewer

**Files:**
- Create: `capture_viewer.html` (repo root, sibling of `pickle_viewer.html`)

**Interfaces:**
- Consumes: `models/pickle/pickle_{idle,cast,cast_release,victory,defeat}.glb`, `.pickle/pickle_face.png`, capture server POST `/save`.
- Produces: page at `http://localhost:8090/capture_viewer.html?anim=<name>` with `window.cap = { setAngle(name), record(prefix, frames, every), still(name) }` — Task 6 drives it.

- [ ] **Step 1: Write the viewer**

Derived from `pickle_viewer.html` (keep its face-seating logic verbatim); differences: pure black clearColor, no grid/HUD, loads the clip GLB named by `?anim=`, exposes `window.cap`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Pickle — Capture Stage</title>
<style>html,body{margin:0;height:100%;background:#000;overflow:hidden}#c{width:100%;height:100%;display:block}</style>
</head>
<body>
<canvas id="c"></canvas>
<script src="https://cdn.babylonjs.com/babylon.js"></script>
<script src="https://cdn.babylonjs.com/loaders/babylonjs.loaders.min.js"></script>
<script>
const ANIM = new URLSearchParams(location.search).get('anim') || 'idle';
const CLIP = { idle:'pickle_idle.glb', cast:'pickle_cast.glb', cast_release:'pickle_cast_release.glb',
               victory:'pickle_victory.glb', defeat:'pickle_defeat.glb' }[ANIM];

const canvas = document.getElementById('c');
const engine = new BABYLON.Engine(canvas, true, { preserveDrawingBuffer:true, stencil:true });
const scene = new BABYLON.Scene(engine);
scene.clearColor = new BABYLON.Color4(0, 0, 0, 1);

const camera = new BABYLON.ArcRotateCamera('cam', -Math.PI/2, Math.PI/2.15, 3.2, new BABYLON.Vector3(0,0.9,0), scene);
camera.attachControl(canvas, true);
new BABYLON.HemisphericLight('h', new BABYLON.Vector3(0,1,0), scene).intensity = 0.9;
const dir = new BABYLON.DirectionalLight('d', new BABYLON.Vector3(-0.5,-1,-0.5), scene);
dir.intensity = 1.1;

// ---- face seating: copied VERBATIM from pickle_viewer.html (buildFace + the
// onBeforeRenderObservable seat block + const seat = {...}), minus the HUD calls.
// When copying, delete updateSeatHud() calls and the one-shot _framedFront block.
// ----

let groups = [];
BABYLON.SceneLoader.ImportMesh('', 'models/pickle/', CLIP, scene,
  (meshes, ps, sk, animationGroups) => {
    groups = animationGroups;
    groups.forEach(a => a.stop());
    if (groups[0]) groups[0].start(true);
    buildFace();
    console.log('CAP_READY', ANIM, meshes.length, 'meshes', groups.map(a=>a.name));
  },
  null, (s, msg) => console.error('CAP_LOAD_ERROR', msg));

const ANGLES = { front: -Math.PI/2, threequarter: -Math.PI/4, side: 0, back: Math.PI/2 };
window.cap = {
  setAngle(name) { camera.alpha = ANGLES[name]; },
  still(name) {
    scene.onAfterRenderObservable.addOnce(() =>
      fetch('/save?name=' + name + '.png', { method:'POST', body: canvas.toDataURL('image/png') }));
  },
  record(prefix, frames = 60, every = 2) {
    let tick = 0, saved = 0;
    const obs = scene.onAfterRenderObservable.add(() => {
      if (tick++ % every !== 0) return;
      if (saved >= frames) { scene.onAfterRenderObservable.remove(obs); console.log('CAP_DONE', prefix); return; }
      fetch('/save?name=' + prefix + '_' + String(saved).padStart(4,'0') + '.png',
            { method:'POST', body: canvas.toDataURL('image/png') });
      saved++;
    });
  }
};
engine.runRenderLoop(() => scene.render());
addEventListener('resize', () => engine.resize());
</script>
</body>
</html>
```

Note for the implementer: "copied VERBATIM" above is a copy-paste instruction — lift lines 50-124 of `pickle_viewer.html` (the `seat` const, `buildFace()`, and the seating observable) into the marked block, deleting only `updateSeatHud()` calls and the `_framedFront` one-shot.

- [ ] **Step 2: Verify each clip loads**

Open `http://localhost:8090/capture_viewer.html?anim=idle` (and then each of `cast`, `cast_release`, `victory`, `defeat`). Console must show `CAP_READY <anim> ... meshes` with a non-empty anims list, and the pickle must render animated on black with its face.

**Contingency (only if a clip GLB renders no mesh):** the clip files may be animation-only. In that case load the base model first and retarget, exactly as the game does at `index.html:10334` — replace the ImportMesh call with: import `'.pickle/', 'pickle_wizard_v1.glb'` first, then in its callback `BABYLON.SceneLoader.ImportAnimationsAsync('models/pickle/', CLIP, scene, false, BABYLON.SceneLoaderAnimationGroupLoadingMode.Clean)` and play the resulting group.

- [ ] **Step 3: Commit**

```bash
git add capture_viewer.html && git commit -m "brand: character capture stage (black-plate viewer over models/pickle clips)"
```

---

### Task 6: Character turnaround stills + animation GIFs

**Files:**
- Create: `brand/character/turn-front.png`, `turn-threequarter.png`, `turn-side.png`, `turn-back.png`
- Create: `brand/character/anim-idle.gif`, `anim-cast.gif`, `anim-victory.gif`, `anim-defeat.gif`

**Interfaces:**
- Consumes: `capture_viewer.html` (Task 5), capture server (Task 2).
- Produces: the eight committed files the art bible (Task 8) embeds by exactly these paths.

- [ ] **Step 1: Turnaround stills (idle clip, 4 angles)**

On `http://localhost:8090/capture_viewer.html?anim=idle`, run in console:

```js
['front','threequarter','side','back'].forEach((a, i) =>
  setTimeout(() => { cap.setAngle(a); cap.still('turn-' + a); }, i * 500));
```

Then: `ls "$FRAMES"/turn-*.png` → Expected 4 files. Read each: pickle centered, black bg, face visible on front/threequarter.

```bash
cp "$FRAMES"/turn-{front,threequarter,side,back}.png /Users/andrewamisola/Projects/Volleybolt/brand/character/
```

- [ ] **Step 2: Animation GIFs (front-facing)**

Per clip — navigate to `?anim=<clip>`, wait for `CAP_READY`, then:

```js
cap.setAngle('threequarter'); cap.record('anim-idle', 60, 2);      // on ?anim=idle
cap.setAngle('threequarter'); cap.record('anim-cast', 60, 2);      // on ?anim=cast
cap.setAngle('threequarter'); cap.record('anim-victory', 60, 2);   // on ?anim=victory
cap.setAngle('threequarter'); cap.record('anim-defeat', 60, 2);    // on ?anim=defeat
```

- [ ] **Step 3: Assemble**

```bash
cd "$FRAMES"
for name in anim-idle anim-cast anim-victory anim-defeat; do
  ffmpeg -y -framerate 30 -i "${name}_%04d.png" -vf \
    "crop=760:900:580:90,split[a][b];[a]palettegen[p];[b][p]paletteuse=dither=bayer" \
    "/Users/andrewamisola/Projects/Volleybolt/brand/character/${name}.gif"
done
```

(Adjust the crop after eyeballing the first output — the pickle must fill the frame without clipping the hat or staff.)

- [ ] **Step 4: Eyeball all 8 outputs, then commit**

```bash
git add brand/character && git commit -m "brand: character sheet captures — 4-angle turnaround + 4 animation GIFs"
```

---

### Task 7: World & UI detail shots

**Files:**
- Create: `brand/world/tower-blue.png`, `brand/world/tower-red.png`, `brand/world/court-biome.png`
- Create: `brand/ui/palette.png` (optional — skip if the art bible's CSS swatches suffice; see Step 3)

**Interfaces:**
- Consumes: `brand/world/arena-wide-1.png` (2880×1620, Task 1).
- Produces: crops the art bible (Task 8) embeds by exactly these paths.

- [ ] **Step 1: Crop tower + biome details from the 2880 wide**

In `arena-wide-1.png` the blue tower occupies roughly the left 1/5, the red tower the right 1/5, the court the center band. Starting crops (verify by Reading the output and adjust ±50px):

```bash
cd /Users/andrewamisola/Projects/Volleybolt/brand/world
ffmpeg -y -i arena-wide-1.png -vf "crop=620:1100:170:120" tower-blue.png
ffmpeg -y -i arena-wide-1.png -vf "crop=620:1100:2090:120" tower-red.png
ffmpeg -y -i arena-wide-1.png -vf "crop=1800:760:540:490" court-biome.png
```

- [ ] **Step 2: Eyeball each crop** — full tower visible roof-to-base; court crop shows dirt road, grass fringe, and bushes.

- [ ] **Step 3: Palette decision** — the art bible renders swatches in CSS (Task 8), so `palette.png` is NOT generated. This step exists to record the decision: skip it.

- [ ] **Step 4: Commit**

```bash
git add brand/world && git commit -m "brand: world detail crops — towers, court biome"
```

---

### Task 8: `brand/README.md` — the art-direction brief

**Files:**
- Create: `brand/README.md`

**Interfaces:**
- Produces: the written brief; the art bible (Task 9) reuses its lore + brief text verbatim.

- [ ] **Step 1: Write the brief** (this exact content):

````markdown
# Volleybolt — Brand & Art Direction Pack

Reference pack for artists creating key art / flavor art (itch.io page, splash
illustrations). Everything in this folder is captured from the real game —
this is ground truth, not concept work.

## The game in one line

Two tiny pickle wizards duel across a castle court, volleying elemental spells
back and forth — a fantasy sport where every exchange is pure skill: **no
randomness, ever**.

## Style pillars

1. **PS1-era fantasy.** Low-poly models, low-res render, 15-bit color with
   Bayer dithering, affine-texture charm. Final Fantasy IX menus are the UI
   north star: steel blue-grey panels, light rims, hard offset shadows, gold
   headings.
2. **NES palette discipline.** Team Blue `#0078F8` vs Team Red `#F83800`,
   amber `#FC9838`, cream `#F8F8F8`. Saturated, iconic, few colors.
3. **Cute body, epic magic.** The pickle wizard is small, round, and
   charming; the spells are outsized and dramatic. Key art lives in that
   contrast.
4. **Deterministic duel.** The fiction and the feel are honor-duel, not
   chaos: readable arcs, clean geometry, nothing splattery or random.

## Character — the Pickle Wizard

- 2D concept: `character/pickle-2d-concept.png` (canonical face + proportions;
  the face sprite `character/pickle-face-sprite.png` is applied as a flat,
  always-front FF9-style decal in game)
- 3D turnaround: `character/turn-{front,threequarter,side,back}.png`
- Motion personality: `character/anim-{idle,cast,victory,defeat}.gif`
- In game the two duelists are the SAME pickle tinted per team — blue-side
  player LEFT, red-side opponent RIGHT. **Never reverse the sides.**
- Design nod: the pickle is a wink at Pickleball's character design — keep it
  a wink, not a joke; the character carries real hero energy in key art.

## Palette (authoritative hexes)

| Role | Hex |
|---|---|
| Gold accent (headings, trim) | `#f0c050` |
| Team blue / Team red | `#0078F8` / `#F83800` |
| Fire / Frost / Lightning | `#ffa040` / `#80d0ff` / `#ffff40` |
| Steel panel bg | `rgba(46,56,76,0.94)` |
| Panel rim | `#dfe6f2` |
| Backdrop dark | `#15121b` |
| NES amber / cream | `#FC9838` / `#F8F8F8` |

Full UI system: `docs/design-system/STYLE-GUIDE.md`.

## The world — DRAFT lore (revisable; not yet canon)

Long ago, the wizards of two rival towers settled their disputes the civilized
way: by hurling spells at each other across a garden court until somebody's
gate gave in. The tradition stuck. Now every dispute — territorial, academic,
or purely personal — is settled by **the volley**: magic answered with magic,
bolt for bolt, until one side can no longer return.

The duelists are pickle-folk: small, brined, and utterly fearless
spellcasters who train their whole lives for court day. Their code is strict —
no luck, no tricks, no dice. A volley is won by reading your opponent, not by
fortune. Fire scorches, frost slows, lightning splits the sky, and a
well-timed parry turns your enemy's best shot back at them.

The court sits between the two towers — blue in the west, red in the east — a
worn dirt road flanked by hedges, lit by a dusk that never quite ends.

## Spells

| Spell | Color | Reference | Reads as |
|---|---|---|---|
| Fireball | `#ffa040` | `spells/fireball.gif` | fast streaking comet + trail |
| Frostbolt | `#80d0ff` | `spells/frostbolt.gif` | cold shard, crystalline trail |
| Thunder | `#ffff40` | `spells/thunder.gif` | jagged sky-strike, instant |
| Parry | team color | `spells/parry.gif` | crescent ward + deflection |

Source in-game textures: `spells/tex-*.png`.

## Key-art brief

**The ask:** splash-style illustration (League of Legends key-art energy) that
looks like THIS game — PS1 fantasy, NES color discipline, cute-vs-epic.

DO
- Low camera angle, pickle wizard mid-cast, spell lighting the scene
- Team colors carrying the composition; gold `#f0c050` for trim/title
- The two-tower standoff as backdrop; dusk purple sky `#15121b`
- Chunky, readable silhouettes (the game reads at 64px — key art should too)

DON'T
- Don't reverse team sides (blue left / red right)
- Don't render the pickle hyper-real or gross — it's a hero, not a gag
- Don't add dice, sparkle-chaos, or randomness motifs — this is a duel of skill
- Don't introduce new spell colors — fire/frost/lightning only

## Folder map

```
character/  2D concept, face sprite, 3D turnaround, animation GIFs
spells/     4 spell GIFs (black plates) + source textures
world/      arena wides (no HUD), tower crops, court biome
ui/         main menu, palette reference
```
````

- [ ] **Step 2: Commit**

```bash
git add brand/README.md && git commit -m "brand: art-direction brief — pillars, palette, DRAFT lore, key-art brief"
```

---

### Task 9: Art bible page `brand/art-bible.html`

**Files:**
- Create: `brand/art-bible.html`
- Create: `tools/inline_assets.py` (emits a self-contained copy for Artifact publishing)

**Interfaces:**
- Consumes: every asset filename from Tasks 1, 4, 6, 7 (relative paths from `brand/`), text from Task 8.
- Produces: `brand/art-bible.html` (repo version, relative asset refs) and `$SCRATCHPAD/art-bible-inline.html` (all assets as data URIs) for the Artifact tool.

- [ ] **Step 1: Build the page**

Structure (LoL How-to-Play flow), styled with the game's design system — reuse the recipes from `docs/design-system/STYLE-GUIDE.md` §1-§8 (steel panel, gold gradient title, hand-pointer accents). Google-font fallbacks (`Press Start 2P`, `Cinzel`) since FF9UI/Ferrum stay in-repo. Sections in order:

1. **Hero** — full-bleed `world/arena-wide-1.png`, gold-gradient "VOLLEYBOLT" title (style guide §8 recipe), tagline: *"Magic answered with magic."*
2. **What is Volleybolt** — one steel panel, the one-liner + 3 bullet fantasy beats.
3. **The World** — DRAFT-badged lore (verbatim from README) beside `world/court-biome.png`, tower crops side by side (blue left, red right).
4. **The Character** — 2D concept and `turn-front.png` side-by-side "same character, two mediums"; 4-angle turnaround strip; 4 animation GIFs in a row with captions (idle / cast / victory / defeat); personality notes.
5. **The Magic** — 4 spell cards: GIF on top, element-colored border (`#ffa040`/`#80d0ff`/`#ffff40`/team blue), name in gold, one flavor line each.
6. **The Arena** — `arena-fireball-rally.png` annotated with a caption row: towers = the stakes, court = the duel, dusk void = the mood.
7. **Style & UI** — CSS swatch grid of the palette table, `ui/main-menu.png`, a live steel-panel demo block, typography note.
8. **Brief for Artists** — the DO/DON'T list from the README in two columns.

Page rules: dark backdrop `#15121b`; every image inside a steel panel frame; `image-rendering: pixelated` on turnaround stills and textures; DRAFT badge = gold border chip. Single `<style>` block, no external CSS/JS beyond Google fonts import.

- [ ] **Step 2: `tools/inline_assets.py`**

```python
#!/usr/bin/env python3
"""Emit a self-contained copy of brand/art-bible.html with all local images inlined."""
import base64, mimetypes, pathlib, re, sys

src = pathlib.Path('brand/art-bible.html')
out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path('art-bible-inline.html')
html = src.read_text()

def inline(m):
    rel = m.group(2)
    p = src.parent / rel
    if not p.exists() or rel.startswith(('http', 'data:')):
        return m.group(0)
    mime = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
    return m.group(1) + f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode() + m.group(3)

html = re.sub(r'''(src=["'])([^"']+)(["'])''', inline, html)
out.write_text(html)
print(out, len(html) // 1024, 'KB')
```

- [ ] **Step 3: Verify in a real browser**

Serve (`capture_server.py` already serves the repo) and open `http://localhost:8090/brand/art-bible.html`. Checklist: all images/GIFs load (zero broken refs — check DevTools network for 404s), section order matches, spell cards use the right element colors, DRAFT badge visible on lore, page scrolls with no horizontal overflow at 1280px width.

- [ ] **Step 4: Build the inline copy and publish as Artifact**

```bash
python3 tools/inline_assets.py "/private/tmp/claude-501/-Users-andrewamisola-Projects-Volleybolt/b2792772-682a-491d-9dc3-4accb2f33339/scratchpad/art-bible-inline.html"
```

Then publish via the Artifact tool (`file_path` = that inline copy, favicon `🥒`, title "Volleybolt Art Bible").

- [ ] **Step 5: Commit**

```bash
git add brand/art-bible.html tools/inline_assets.py
git commit -m "brand: art bible page — LoL-style flow, FF9-steel styling, self-contained inliner"
```

---

### Task 10: Final acceptance check against the spec

**Files:** none (verification only)

- [ ] **Step 1: Run the spec's acceptance list** (`docs/superpowers/specs/2026-07-05-branding-art-bible-design.md`):

1. `find brand -type f | sort` — four subfolders populated + README + art-bible.html.
2. Art bible: all assets render, LoL-style section flow, game design language.
3. All four spell GIFs are real captures, legible (re-eyeball).
4. Character sheet shows 2D + 3D side by side, turnaround + animation strip.
5. Lore marked DRAFT.
6. Goldens still hold (re-run Task 3 Step 2 — index.html was touched once).

- [ ] **Step 2: Merge decision** — present the branch for user review (superpowers:finishing-a-development-branch).
