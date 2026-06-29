# Agent · UI / UX  ·  Presentation pillar

**Owns.** FF9 command menu (Babylon GUI), DOM menus, ability bar, combat log, party stats, the FF9 gem-panel restyle.

**Reports into** → [Presentation pillar](../pillars/presentation.md) · also reads [Shared Core](../SHARED_CORE.md)

## Grounded in (external canon)
- [Babylon GUI](https://doc.babylonjs.com/features/featuresDeepDive/gui/gui)
- [NES.css](https://nostalgic-css.github.io/NES.css/)

## Internal docs
- `docs/UI.md` _(author + maintain)_

## Invariants
- Follow the Babylon-GUI-vs-DOM decision rule recorded in UI.md.

## Working log
_Append-only. Newest at top. Each entry: date · decision/change · open issues._

- 2026-06-29 · Audit pass on design-system files: removed invented parchment/stone sub-palette (5 tokens); restyled .vb-tooltip to the real steel panel treatment (STEEL/RIM constants); replaced all brown-tone hex values with verified game tokens; renamed "arcane" labels to neutral descriptions across all three files; grep confirms zero parchment/brown/arcane/brown-hex references remain; all retained hex values verified present in index.html/styles.css. No game files changed. · Open: see prior entry.
- 2026-06-29 · Created design-system extraction under docs/design-system/: STYLE-GUIDE.md (full token catalog + component specs), volleybolt-ui.css (standalone CSS with :root tokens + component classes), demo.html (static showcase of all components). No game files changed. · Open: local custom fonts (FF9UI.ttf, Ferrum.otf) are not web-hosted — website build will need to either bundle them or accept Press Start 2P / Cinzel fallbacks; the CSS already declares both. The CRT overlay is authored and documented but currently disabled in-game; the demo shows it on-by-default for marketing purposes.

- _(start here)_

---
_[Presentation pillar](../pillars/presentation.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
