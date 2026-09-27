# Castle Remodel — Design

**Date:** 2026-09-26
**Status:** Approved (owner: "try it out"), implemented
**Owner asks:** make the castle less flat: PS1 look, but geometry with some soul. Damage
should be staged states, not per-brick physics.

## Decisions

| Question | Decision |
|---|---|
| Art flavor | FF9 storybook: round tapered towers, a gentle lean, an oversized flared cone roof with finial and team pennant, timber hoarding, a corbelled side turret, warm lit windows |
| Damage | 4 authored states swapped on tower HP, plus a scripted crumble beat |
| Pipeline | Scripted Blender to GLB. The build script is the source; the `.blend` stays hand-editable |

## Constraints found in the code

- **The castle is presentation only.** The sim's gate line is an X constant and never reads castle
  meshes, so the model can't affect determinism.
- **The game camera is fixed:** orthographic, alpha −π/2, beta π/3 (30° above the ground). The online
  camera flip exists but is never called. Faces pointing along ±X are edge-on and never seen. Like
  an FF9 pre-rendered set, detail goes on the tops and the camera-facing side.
- **Tower HP is stored per zone,** and returning to a zone lifts a gate up to a 50% floor. So the
  castle must be able to show any state at round start, not just degrade.

## Asset

`tools/blender/build_castle.py` (run headless in Blender 5.0) writes `models/castle/castle.blend` and
`models/castle/castle.glb`.

- **Axes:** Blender +X is away from the court, +Y is toward the camera, +Z is up. The origin is the
  foot of the gate wall's centre line (the old `baseX, 0, 0`).
- **Nodes:** `castle_s0` … `castle_s3` are one joined mesh per state (pristine, battered, breached,
  ruined). `castle_debris` holds 12 loose chunks.
- **Layout:** the gate wall spans the whole lane end, rail to rail (`LANE_HALF` = 8.0 Blender units =
  Babylon z ±7.2 at 0.9 scale), with a drum bastion on each rail, so no grass gap shows at either rail
  and every hit visibly lands on the wall. The keep stands on a crisp paved footing. From its door,
  a worn flagstone path runs to the near rail: dense in the middle, then thinning into sparser,
  smaller, darker stones and then grass, so there's no hard-edged slab. Path stones sit at least 0.2
  above the ground because the lane's dirt-road decal draws with a polygon offset that covers
  anything lower. The game centres the castle on the lane
  (`setTowerOffset(0.4, 0)`).
- **Materials:** `M_keep`, `M_wall` (the existing 64 px `tower_stone.png` / `castle_wall.png`),
  `M_roof_team` and `M_cloth_team` (neutral, tinted at runtime), `M_wood`, `M_dark`, `M_window`, `M_paving` (a generated
  32 px flagstone texture). Samplers use nearest filtering.
- **Shading:** ground AO, under-roof shadow, per-face variation and scorch are baked into the
  `COLOR_0` vertex colors.
- **Budget:** about 1.2–1.4k triangles per state.
- **States:**
  - Battered: roof scorch, a missing hoarding plank and merlons, cracks, one window dark.
  - Breached: a hole through the camera-facing roof slope showing the attic and rafters, the turret
    roof gone, the pennant snapped, the gate wall breached, a bastion slumped.
  - Ruined: the keep's top collapsed with a jagged rim and charred beams, no roof, rubble piles.

## Game integration (`index.html`)

- **Loading:** `loadCastle(isPlayer)` loads the GLB once per side under `playerCastle` / `aiCastle`,
  parented to the tower roots so `setTowerOffset` still applies. Red is the same model mirrored,
  with scale (−0.9, 0.9, 0.9). It stands straight on the lane at y 0.
- **Materials:** converted to the flat PS1 look (no metal, no gloss, no environment light). The team
  materials follow `window.TEAM_RIGHT` through `refreshTeamColors`, so colorblind mode recolors the
  red castle live.
- **States:** a `scene.onBeforeRenderObservable` observer derives each castle's state from the
  settled `towerHealth` every frame. It crumbles only when a state gets worse mid-round (`gameState
  === 'playing' && !roundTransitioning`); otherwise it snaps.
  - `syncCastleStates()` (called from `resetRound`) recalls debris and forces a snap.
  - `castleHit()` (called from `dealDamageToTower`) drops 1–2 chunks per hit. It's skipped while
    re-simulating and under reduce-motion.
- **Removed:**
  - the procedural gate (bricks, buttresses, merlons, slits, archway, foundation, keep, parapet,
    crenellations, roof)
  - `destroyBrickAt` / `resetBricks`
  - the castle self-shadow light and generator
  - the team-colored backdrop walls, which poked through the round keep
- **Hidden:** the `blueBase` / `redBase` team slabs. They were covering the seam where the 3D stage
  ended and the painted backdrop began (thick 3D rails meeting thin painted ones, and the 3D floor
  meeting the painted ground). They're kept in code because 2v2 still resizes them and the painted
  tower shadows are placed from them.
- **Stage runoff:** the floor, the dirt road and both rails now run `STAGE_RUNOFF` (30) past both stage
  ends, under the castles and off-screen, with texture tiling scaled so nothing inside the stage
  changes. The road's opacity mask was made seamlessly tileable (whole-cycle edge waves, wrapped
  blobs and a wrapped blur), so it repeats along the longer road without a line at the stage ends.

## Verification

- Singles hashes are unchanged: `a90063b5`, `5e5eca1b`, `e6fdfae9`. The doubles hashes match the
  pre-change baseline: `c736299e`, `85eecc3f`, `0e029492`. The doubles pins in the `js/sim.js`
  header were already stale before this change.
- In the browser:
  - each state appears at its HP threshold, on both sides;
  - the crumble launches 12 chunks that fall, fade out between 1.1 and 1.6 s, and are recalled;
  - at a round end the tower crumbles to ruined, then snaps to pristine for the next zone;
  - the floor, road and rails are continuous from edge to edge, with no seam at the stage ends;
  - colorblind mode recolors the red castle live;
  - there are no console errors.
- `castle_viewer.html` shows all four states from the game's camera.
