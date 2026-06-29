# Volleybolt Design System — Style Guide

Extracted from `index.html` + `styles.css` (v56), 2026-06-29.
This is an extraction document — it describes what the game already uses.
All hex values are the authoritative source values; nothing is invented here.

---

## Design philosophy

Volleybolt's visual language is Final Fantasy IX / PS1-era menu design
filtered through NES-palette 3D rendering. The governing rules:

- Every window is a **steel panel**: a blue-grey gradient pane with a
  brushed-metal grain texture, a crisp light-rimmed border, and a hard
  (no-blur) 4-5 px offset drop shadow. No soft glows on structural chrome.
- Text always carries a **2 px hard-offset black shadow** (`2px 2px 0 #000`).
  No blurred text shadows except for the title bloom effect.
- **Pixel-first**: `steps()` timing functions, `pixelated` image-rendering,
  integer offsets. Avoid sub-pixel anti-aliasing aesthetics.
- **Gold is the accent color** for all player-facing labels (tower names,
  scores, ability names, section headers). One gold: `#f0c050`.
- Team identity: **Blue** left / **Red** right. Every gauge, label, and badge
  follows this split — never reverse it.

---

## 1. Color tokens

### Core palette

| Token name          | Hex / rgba                  | Semantic role                               |
|---------------------|-----------------------------|---------------------------------------------|
| `--vb-gold`         | `#f0c050`                   | FF9 gold accent — headings, labels, icons   |
| `--vb-gold-mid`     | `#d4a849`                   | Mid gold — dividers, gradient midpoint      |
| `--vb-gold-dark`    | `#8b6914`                   | Dark gold — shadow stop, deep gradient end  |
| `--vb-gold-bright`  | `#ffe9a8`                   | Bright gold — title gradient top stop       |
| `--vb-gold-amber`   | `#fc9838`                   | NES amber — 3-D object highlight            |

### Steel window system (FF9 panel chrome)

| Token name          | Value                        | Role                                        |
|---------------------|------------------------------|---------------------------------------------|
| `--vb-steel-bg`     | `rgba(46,56,76,0.94)`        | Panel background (the "STEEL" constant)     |
| `--vb-steel-hi`     | `rgba(84,96,118,0.90)`       | Gradient top — lighter steel                |
| `--vb-steel-lo`     | `rgba(42,52,70,0.93)`        | Gradient bottom — deeper steel              |
| `--vb-rim`          | `#dfe6f2`                    | Border / light rim                          |
| `--vb-rim-inner`    | `rgba(16,24,40,0.75)`        | Inner dark line (creates double-border look)|
| `--vb-text`         | `#f4f7ff`                    | Primary UI text — cream-white               |
| `--vb-text-hover`   | `#fff4c2`                    | Hovered / selected text — warm cream        |
| `--vb-text-dim`     | `#8b94a8`                    | Dimmed text — cooldown, disabled rows       |

### Background tones

| Token name          | Hex                         | Where used                                  |
|---------------------|-----------------------------|---------------------------------------------|
| `--vb-bg-game`      | `#15121b`                   | Body / letterbox bars                       |
| `--vb-bg-load`      | `#0a0808`                   | Loading screen full-bleed                   |
| `--vb-bg-menu`      | `#04050a`                   | Menu overlay darkest edge                   |
| `--vb-bg-menu-mid`  | `#0a0d16`                   | Menu overlay center                         |
| `--vb-bg-menu-glow` | `#1b2233`                   | Title-screen backdrop ellipse glow center   |

### Team colors

| Token name                  | Hex        | Role                                    |
|-----------------------------|------------|-----------------------------------------|
| `--vb-blue`                 | `#0078F8`  | NES iconic team blue                    |
| `--vb-blue-gauge-hi`        | `#57c4ec`  | Blue HP gauge bright end                |
| `--vb-blue-gauge-lo`        | `#2173ac`  | Blue HP gauge deep end                  |
| `--vb-blue-mana`            | `#5ad0ff`  | Player mana orbs / mana cost text       |
| `--vb-blue-mana-rim`        | `#9fe3ff`  | Gauge cyan rim (all gauges)             |
| `--vb-blue-cast-hi`         | `#6fb0ff`  | Cast bubble — blue team border          |
| `--vb-blue-hp-text`         | `#209cee`  | HP percentage text — blue               |
| `--vb-red`                  | `#F83800`  | NES iconic team red                     |
| `--vb-red-gauge-hi`         | `#ff9e82`  | Red HP gauge bright end (mirrored)      |
| `--vb-red-gauge-lo`         | `#992f1e`  | Red HP gauge deep end                   |
| `--vb-red-text`             | `#e76e55`  | Red team labels / percentages           |
| `--vb-red-cast-hi`          | `#ff8a6f`  | Cast bubble — red team border           |

### Spell element colors

| Token name          | Hex        | Role                              |
|---------------------|------------|-----------------------------------|
| `--vb-fire`         | `#ffa040`  | Fire damage text                  |
| `--vb-frost`        | `#80d0ff`  | Frost damage / frozen text        |
| `--vb-lightning`    | `#ffff40`  | Lightning / cancel text           |
| `--vb-success`      | `#6ad26a`  | Connected / ready states          |

### Combat text colors

| Class           | Hex        | Meaning            |
|-----------------|------------|--------------------|
| `.fire`         | `#ffa040`  | Fire hit           |
| `.frost`        | `#80d0ff`  | Frost hit          |
| `.lightning`    | `#ffff40`  | Lightning / cancel |
| `.frozen`       | `#8fd0ff`  | Frozen status      |
| `.damage`       | `#ff4040`  | Numeric damage     |
| `.cancel`       | `#ffff40`  | Ability cancelled  |

---

## 2. Typography

### Font stack

| Role         | Family                  | Format | Source       | Notes                                  |
|--------------|-------------------------|--------|--------------|----------------------------------------|
| UI / body    | `FF9UI`                 | TTF    | `fonts/ff9ui.ttf` (local) | Primary pixel-style UI font for all labels, menus, buttons. Bold weight is `font-weight: 400` (font has one weight — no faux-bold). |
| Title / logo | `Ferrum`                | OTF    | `fonts/ferrum.otf` (local) | Display-only. Title screen + loading screen logo. |
| Decorative   | `Esthetique`            | OTF    | `fonts/esthetique.otf` (local) | Loaded but used sparingly for headers. |
| Fallback 1   | `Press Start 2P`        | Google Fonts | CDN | 8-bit pixel feel; closest web-safe substitute for FF9UI. |
| Fallback 2   | `Cinzel`                | Google Fonts | CDN | Serif display; approximate stand-in for Ferrum. |

The full Google Fonts import in the game:
```
Cinzel:wght@400;600;700
Crimson+Text:ital,wght@0,400;0,600;0,700;1,400
Press+Start+2P
Rajdhani:wght@400;500;600;700
Cabin:wght@500;600;700
Cormorant+Garamond:wght@500;600;700
```

### Type scale

| Use                      | Size (px) | Weight | Letter-spacing | Font       |
|--------------------------|-----------|--------|----------------|------------|
| Title logo               | 108       | 700    | 8px            | Ferrum     |
| Section / round title    | 84        | 700    | 6px            | FF9UI      |
| Loading title            | 72        | 700    | 8px            | Ferrum     |
| Menu item label          | 46        | 600    | 2px            | FF9UI      |
| Stage transition         | 42        | 400    | 6px            | FF9UI      |
| Score / victory text     | 48-56     | 700    | 4-6px          | FF9UI      |
| Section heading (in-game)| 22-28     | —      | 1-2px          | FF9UI      |
| Body / settings          | 22        | —      | —              | FF9UI      |
| Ability name (command)   | 21        | —      | 0.3px          | FF9UI      |
| Tooltip title            | 18        | —      | —              | FF9UI      |
| Tooltip body             | 16        | —      | —              | FF9UI      |
| Small badge / key hint   | 11-14     | —      | —              | FF9UI      |
| Copyright footer         | 14        | —      | 2px            | FF9UI      |

### Text shadow convention

All FF9UI text on dark backgrounds uses a **2 px hard-offset black shadow**:

```css
text-shadow: 2px 2px 0 #000;  /* --vb-text-shadow */
```

The score / center-message escalates to double-stacked shadows for emphasis:
```css
text-shadow: 3px 3px 0 #000, 4px 4px 0 #000;
```

---

## 3. The FF9 steel panel

This is the single most reused component. Every in-game window (command menu,
health bars, cast bars, loading card, buttons) is a variant of this recipe.

### Background recipe

```css
/* 1. Brushed-metal grain (118° diagonal micro-lines) */
repeating-linear-gradient(
  118deg,
  rgba(255,255,255,0.035) 0px,
  rgba(255,255,255,0.035) 1px,
  rgba(0,0,0,0.05) 1px,
  rgba(0,0,0,0.05) 2px,
  transparent 2px,
  transparent 4px
),
/* 2. Steel blue-grey base gradient */
linear-gradient(180deg, rgba(84,96,118,0.90) 0%, rgba(42,52,70,0.93) 100%)
```

### Border and shadow

```css
border: 2px solid #dfe6f2;               /* light rim */
border-radius: 8-13px;                   /* 8px tight, 13px loose */
box-shadow:
  inset 0 0 0 1px rgba(16,24,40,0.75),   /* dark inner line → double-border */
  inset 0 2px 3px rgba(255,255,255,0.22),/* top bevel highlight */
  inset 0 -3px 4px rgba(0,0,0,0.38),    /* bottom bevel shade */
  5px 5px 0 rgba(0,0,0,0.5);            /* hard drop shadow (no blur) */
```

The tab overlay that floats above the panel top edge is the same STEEL
background and RIM border, `cornerRadius: 6`, sitting at `top = -4px` relative
to the panel's top edge so the bottom of the tab merges with the panel rim.

---

## 4. Button / menu item

### `.game-btn` (the canonical button)

- Background: FF9 steel recipe above
- Border: `2px solid #e0e6f0`
- Border-radius: `11px`
- Min-width: `220px`, padding: `14px 32px`
- Font: FF9UI, `22px`, letter-spacing `2px`, color `#eef2fa`
- Text-shadow: `2px 2px 0 #2a2f3a` (dark-grey, not pure black)
- Box-shadow: steel system above with `5px 5px 0 rgba(0,0,0,0.5)`

**Hover state**:
- `border-color: #ffffff`
- `color: #fff4c2` (warm cream)
- `transform: translateY(-2px)`

**Active/pressed**: `transform: translateY(1px)`

**Disabled**: `opacity: 0.45`, `cursor: not-allowed`

### `.menu-btn` (title-screen variant — no box, text-only)

The title-screen overrides `.game-btn` to be a plain text list:
- `background: none; border: none; border-radius: 0; box-shadow: none`
- Left padding `48px` — room for the triangle hand pointer
- Label: FF9UI `46px`, weight `600`, color `#f0c050` (gold), text-shadow `2px 2px 0 #000`
- Hover: `color: #fff4c2`

### FF9 hand pointer

Applied as a CSS `::before` pseudo-element on hovered/active items:

```css
::before {
  content: '';
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 0; height: 0;
  border-top: 8px solid transparent;
  border-bottom: 8px solid transparent;
  border-left: 13px solid #f4f7ff;
  filter: drop-shadow(2px 2px 0 rgba(8,12,26,0.85));
  opacity: 0;
  transition: opacity 0.08s ease;
}
:hover::before { opacity: 1; }
```

### Primary CTA pulse animation

```css
@keyframes menuPrimaryBreath {
  0%, 100% { box-shadow: /* steel system */ 0 0 8px rgba(200,215,240,0.12); }
  50%       { box-shadow: /* steel system */ 0 0 18px rgba(200,215,240,0.4); }
}
```

---

## 5. Gauge / bar

### FF9 gauge anatomy

```
┌──────────────────────────────────────┐  ← cyan rim (#9fe3ff), 2px, cornerRadius 3
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│  ← track: vertical gradient #2f191b → #160c0d
│███████████████████▌░░░░░░░░░░░░░░░░░│  ← fill: team gradient (left-anchored)
│‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾│                 │  ← inset sheen: rgba(255,255,255,0.5), 2px tall
│                    ▐                 │  ← lit edge: rgba(220,245,255,0.9), 3px wide
└──────────────────────────────────────┘
     3px 3px 0 #000 hard shadow
```

- Track bg: `linear-gradient(0deg, #160c0d 0%, #2f191b 100%)` (vertical, warm-dark)
- Rim: `#9fe3ff` (cyan), 2px border
- Shadow: `shadowOffsetX: 3, shadowOffsetY: 3` (hard, no blur)

### Fill gradients (by team / purpose)

| Use                   | Start (c0)  | End (c1)    | Direction |
|-----------------------|-------------|-------------|-----------|
| Blue HP               | `#2173ac`   | `#57c4ec`   | left→right|
| Red HP (mirrored)     | `#992f1e`   | `#ff9e82`   | right→left|
| Gold cast bar         | `#bf8a30`   | `#ffd96a`   | left→right|
| Red cast bar (mirror) | `#992f1e`   | `#ff9e82`   | right→left|

### Loading bar

- Container: `rgba(20,28,42,0.9)`, border `#cfd6e4`, `border-radius: 7px`
- Fill: `linear-gradient(180deg, #bfe6ff 0%, #6db4e6 50%, #8fc8ee 100%)`
- Transitions with `steps(8)` for a chunky retro fill feel

---

## 6. Tooltip

Steel panel treatment — matches the game's Babylon GUI detail box (STEEL constant):

```css
background:
  repeating-linear-gradient(
    118deg,
    rgba(255,255,255,0.035) 0px, rgba(255,255,255,0.035) 1px,
    rgba(0,0,0,0.05) 1px, rgba(0,0,0,0.05) 2px,
    transparent 2px, transparent 4px
  ),
  linear-gradient(180deg,
    rgba(84,96,118,0.96) 0%,
    rgba(42,52,70, 0.97) 100%
  );
border: 2px solid #dfe6f2;   /* --vb-rim */
border-radius: 8px;
box-shadow:
  inset 0 0 0 1px rgba(16,24,40,0.75),
  inset 0 2px 3px rgba(255,255,255,0.18),
  4px 4px 0 rgba(0,0,0,0.55);
```

- Title row: FF9UI 18px, color `#f0c050` (`--vb-gold`), text-shadow `1px 1px 0 #000`
- Body: FF9UI 16px, color `#f4f7ff` (`--vb-text`), line-height 1.4
- Stats: FF9UI 14px, color `#f4f7ff` (`--vb-text`)
- Divider: `1px solid rgba(206,214,230,0.25)` (dim rim)
- Arrow (::after): CSS border trick pointing down, `border-top-color: rgba(46,56,76,0.96)` (steel bg)
- Width: 280px

### Tooltip inline text colors

| Class            | Color     | Meaning                   |
|------------------|-----------|---------------------------|
| `.tt-value`      | `#ffd700` | Numeric values (bold)     |
| `.tt-spell`      | `#f0c050` | Spell name (bold)         |
| `.tt-mechanic`   | `#b8a060` | Game mechanic (italic)    |
| `.tt-fire`       | `#ff8844` | Fire keyword              |
| `.tt-frost`      | `#66ccff` | Frost keyword             |
| `.tt-lightning`  | `#ffee66` | Lightning keyword         |
| `.tt-damage`     | `#ff6655` | Damage keyword            |
| `.tt-duration`   | `#88dd88` | Duration keyword          |
| `.tt-enemy`      | `#e76e55` | Enemy reference           |
| `.tt-mana`       | `#6699ff` | Mana reference            |
| `.tt-key`        | `#aaaaaa` + `#333` bg | Keyboard key badge |

---

## 7. CRT overlay

Currently disabled in the shipping game (`display: none`) — the low-res 3D
render carries the retro feel without the overlay. The CSS recipe is preserved
in `#crtOverlay` for reactivation or marketing use.

### Scanlines

```css
background-image: repeating-linear-gradient(
  to bottom,
  rgba(0,0,0,0.18) 0px,
  rgba(0,0,0,0.18) 1px,
  rgba(255,255,255,0.0) 1px,
  rgba(255,255,255,0.0) 2px
);
mix-blend-mode: multiply;
```

### Vignette (::before)

```css
background: radial-gradient(
  ellipse at center,
  rgba(0,0,0,0.0) 55%,
  rgba(0,0,0,0.45) 95%,
  rgba(0,0,0,0.7) 100%
);
mix-blend-mode: multiply;
```

### Subtle flicker (::after)

```css
background: rgba(255,255,255,0.015);
mix-blend-mode: overlay;
animation: crt-flicker 6s steps(60) infinite;
/* opacity keyframes: 0.20 → 0.55 → 0.30 → 0.70 → 0.40 → 0.55 → 0.30 → 0.20 */
```

---

## 8. Menu / title screen backdrop

```css
background: radial-gradient(
  ellipse 72% 62% at 50% 42%,
  #1b2233 0%,
  #0a0d16 56%,
  #04050a 100%
);
```

Title logo bloom (behind the Ferrum text):
```css
background: radial-gradient(ellipse at center,
  rgba(190,212,255,0.42) 0%,
  rgba(115,155,238,0.22) 32%,
  rgba(70,100,200,0.08) 56%,
  transparent 72%);
filter: blur(16px);
animation: titleBloom 5s ease-in-out infinite;
```

Title gold gradient text:
```css
background: linear-gradient(180deg,
  #ffe9a8 0%,        /* bright highlight */
  #f0c050 40%,       /* FF9 gold midpoint */
  #d4a849 64%,       /* mid gold */
  #8b6914 100%);     /* dark gold shadow */
-webkit-background-clip: text;
background-clip: text;
color: transparent;
filter: drop-shadow(4px 4px 0 #000) drop-shadow(0 0 16px rgba(212,168,73,0.3));
```

Shimmer sweep (::before, looped):
```css
background: linear-gradient(100deg,
  transparent 30%,
  rgba(255,255,255,0.85) 50%,
  transparent 70%);
background-size: 220% 100%;
animation: titleShimmer 5s ease-in-out infinite;
```

---

## 9. Mana orb / cast bubble

### Speech bubble (cast announcement)

```css
/* Neutral steel */
background:
  repeating-linear-gradient(118deg, rgba(255,255,255,0.05)...),
  linear-gradient(180deg, rgba(84,96,118,0.95), rgba(42,52,70,0.97));
border: 2px solid #d3dae8;
border-radius: 8px;
box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 3px 0 rgba(0,0,0,0.45);

/* Blue team */
border-color: #6fb0ff;
background: ...linear-gradient(180deg, rgba(58,92,150,0.96), rgba(28,48,88,0.97));

/* Red team */
border-color: #ff8a6f;
background: ...linear-gradient(180deg, rgba(150,60,58,0.96), rgba(90,30,30,0.97));
```

---

## 10. NES 3-D palette (reference, not for UI chrome)

These are used on 3-D meshes (towers, projectiles, environment) and in the
scoreboard labels. Included here for completeness:

| Name        | Hex      | 3-D role                 |
|-------------|----------|--------------------------|
| NES black   | `#0F0F0F`| Deep shadow              |
| NES dark gray| `#3D3D3D`| Stone floor              |
| NES gray    | `#7C7C7C`| Accent stone             |
| NES blue    | `#0078F8`| Blue tower / player      |
| NES red     | `#F83800`| Red tower / AI           |
| NES green   | `#00A800`| —                        |
| NES gold    | `#FC9838`| Objective highlights     |
| NES yellow  | `#F8D878`| Highlight                |
| NES cream   | `#F8F8F8`| Near-white highlight     |

---

## 11. Notable effects that don't translate to plain CSS

| Effect                        | Game technique                          | CSS / web fallback                                                    |
|-------------------------------|-----------------------------------------|-----------------------------------------------------------------------|
| Babylon GUI gradient fill     | `LinearGradient` on a `Rectangle` control with absolute texture-space coordinates | `background: linear-gradient(...)` on a `<div>` — direct equivalent   |
| Gauge lit leading edge        | 3 px `Rectangle` child at right/left of fill | `::after` pseudo with `position: absolute; right/left: 0; width: 3px; background: rgba(220,245,255,0.9)` |
| Title logo font (Ferrum)      | Local OTF — `fonts/ferrum.otf`          | `@font-face` referencing relative path; fallback: `Cinzel` (Google Fonts — similar display weight) |
| FF9UI pixel font              | Local TTF — `fonts/ff9ui.ttf`           | `@font-face` referencing relative path; fallback: `Press Start 2P` (Google Fonts — closest 8-bit feel) |
| `steps()` animation           | `transition: width 0.15s steps(8)` on loading bar | Direct CSS equivalent — `steps(N)` is standard CSS                   |
| SVG posterize filter          | `<filter id="posterize">` inline SVG `<feComponentTransfer>` | Embed the same SVG inline in the website page; reference with `filter: url(#posterize)` |
| Title shimmer sweep           | `::before` with clipped gradient + `background-position` animation | Direct CSS equivalent — see section 8                                |
| CRT scanlines / vignette      | `mix-blend-mode: multiply` overlay div  | Direct CSS equivalent — see section 7. Works on modern browsers.     |
| Babylon `shadowBlur: 0 / shadowOffsetX: 3/4` | Babylon GUI control property | `box-shadow: 3px 3px 0 #000` (no blur) — direct CSS equivalent      |
| `zoom: var(--ui-scale)` HUD scaling | JS sets `--ui-scale = containerWidth/1920` on `#gameContainer`; HUD uses `zoom` to scale | For website: use `transform: scale(factor)` with `transform-origin: top left`, or responsive CSS units |
