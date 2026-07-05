# Branding Pass — Art Bible & Asset Pack — Design

**Date:** 2026-07-05
**Status:** Approved
**Purpose:** Produce the reference material external artists need to create
itch.io key art / flavor art (League-of-Legends-splash-style) that looks like
Volleybolt actually looks — extracted from the real game, not invented.

## Context

Volleybolt's visual identity already exists in the shipping game; it has just
never been collected in one place. The authoritative sources:

- **2D character model:** `.pickle/pickle_wizard_v1.png` (cartoon pickle wizard,
  purple star hat, glowing staff) + `.pickle/pickle_face.png`.
- **3D character model:** `.pickle/pickle_wizard_v1.glb`, rigged clips in
  `models/pickle/` (idle, left/right, cast, cast_release, victory, defeat),
  viewable in `pickle_viewer.html`. In-game: player tinted blue-side, AI tinted
  red — team identity is Blue left / Red right, never reversed.
- **World/arena:** two stone castle towers (blue vs red conical roofs) flanking
  a dirt-road court with grass fringes and low-poly bushes, purple void
  backdrop, PS1 low-res render with 15-bit quantization + Bayer dither.
- **UI/style system:** `docs/design-system/STYLE-GUIDE.md` — FF9/PS1 steel
  panels, NES palette, gold `#f0c050` accent, hard-offset shadows, element
  colors (fire `#ffa040`, frost `#80d0ff`, lightning `#ffff40`).
- **Existing captures:** `screenshots/volleybolt-nohud-*.png` (2880×1620 and
  1920×1080, HUD-free), plus audit shots of menus/UI.

The pickle design is a light nod to Pickleball's character design; the art
style itself is unbiased — this pack documents what is on screen.

## Deliverable 1 — `brand/` asset folder

Raw, artist-downloadable assets, organized:

```
brand/
  README.md            ← art-direction brief (see below)
  character/           ← 2D concept + face; 3D turnaround stills
                          (front / ¾ / side / back); GIFs: idle,
                          cast → cast_release, victory, defeat
  spells/              ← fireball.gif, frostbolt.gif, thunder.gif,
                          parry.gif (in-game captures); source spell
                          textures; element color swatches
  world/               ← arena wides (no HUD), tower close-ups,
                          court/biome details, backdrop grade
  ui/                  ← main menu, steel panel samples, logo
                          treatment, palette sheet
```

`README.md` contents: style pillars (PS1/FF9 menu chrome × NES palette ×
cozy-cute pickle characters), palette tables distilled from the style guide,
the draft lore, and a **key-art brief** — what to emphasize (character charm,
elemental magic, the two-tower standoff), splash-art reference framing, and
hard rules (team colors never reversed; one gold; no randomness in tone —
deterministic duel, not chaos).

## Deliverable 2 — Art bible HTML page

One self-contained page styled with the game's own design system (steel
panels, FF9UI/Ferrum-style type, gold accents), structured like the League of
Legends "How to Play" page — hero first, then progressive sections:

1. **Hero** — full-bleed arena shot + logo treatment
2. **What is Volleybolt** — one-paragraph pitch of the game fantasy
3. **The World** — draft lore (below) + biome imagery
4. **The Character** — character sheet: 2D concept beside 3D turnaround,
   animation GIF strip, personality notes
5. **The Magic** — spell showcase: each GIF in its element color frame with
   name + one-line flavor
6. **The Arena** — court anatomy, towers, biome details
7. **Style & UI** — palette swatches, typography, panel chrome, CRT/PS1
   render treatment
8. **Brief for Artists** — the key-art ask, do/don't list

Saved in-repo at `brand/art-bible.html`, published as a shareable Artifact.

## Draft lore (light-touch, marked DRAFT)

A few paragraphs only — enough story hook for key art, explicitly revisable
draft canon, extrapolated from what's on screen: who the pickle wizards are,
why two towers face each other across a court, and what the "bolt" volley
ritual is. No world name / faction naming pass (explicitly out of scope —
user chose light lore over a full naming pass).

## Capture approach (Approach A — staged live-game captures)

- Drive the real game headlessly (Playwright), use debug/free-play to trigger
  each spell cleanly, capture frame bursts, assemble GIFs with ffmpeg.
- Character turnarounds + animation GIFs via `pickle_viewer.html` camera
  orbit (it renders the real GLB with the game's shading).
- Reuse the existing 2880×1620 no-HUD shots for wides; capture new detail
  shots as needed.

Rejected alternatives: **B** custom clean-room capture scenes (more control,
but no longer "the game" and more work); **C** raw match recordings (noisy,
spells fire unpredictably, illegible as reference).

## Explicit non-goals

- No AI-generated key-art concepts (user chose reference-only — artists get
  ground truth, not a pre-baked style anchor).
- No full lore/naming bible.
- No changes to game code beyond whatever debug hooks already exist; this
  pass is read-only with respect to gameplay.

## GIF list (approved)

Fireball, Frostbolt, Thunder, Parry/block. (Rally-exchange and
victory/defeat *match* GIFs were offered and not selected; victory/defeat
*animations* still appear in the character sheet via the viewer.)

## Acceptance

- `brand/` folder exists with the four subfolders populated and README brief.
- Art bible page renders self-contained, all assets embedded, structured per
  the LoL-style section flow, styled with the game's design language.
- All four spell GIFs are real in-game captures, clearly legible.
- Character sheet shows 2D + 3D side by side with a turnaround and animation
  strip.
- Lore section is clearly marked DRAFT.
