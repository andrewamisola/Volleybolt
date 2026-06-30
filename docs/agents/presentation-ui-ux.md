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

- 2026-06-30 · Spell-cast floating text: anchored above 3D cast bar + non-overlapping queue. Decoupled spellCastQueue {player,ai} from combatTextQueue; new window.updateSpellCastText registered in render loop (line 13863). Anchor: projects cast-bar top edge (paddle world Y + 2.09 world units) to HUD screen space; bubble centre placed BUBBLE_HALF_H(17px) + ABOVE_GAP(8px) above that projected point. Stack: slot 0 = newest (bottom), each older entry offset -48px (STACK_SPACING, exceeds ~41px bubble+tail height); 1 s hold then 25fps stepped upward drift; stepped fade in last 0.5 s; queue capped at 4. showSpellCastText rewired to push to spellCastQueue instead of calling showCombatText; FX-only, no sim state touched; node --check passes. · Open: doubles-mode front combatants share the same player/ai side key as back combatants; if a front and back combatant cast simultaneously their bubbles share one queue (benign stacking). If per-combatant queues are needed, plumb combatant identity through showSpellCastText and add four queue slots.

- 2026-06-29 · Landing page revision D (4 changes): (1) Single CTA — removed "Join the Playtest" and "Wishlist" buttons; one "Join Discord" / "Join Discord to Playtest" button with href="#" placeholder in both hero and CTA section. (2) Hook — primary line changed to "Pong, Evolved."; two alternatives noted in an HTML comment (B: "Pong, Enchanted.", C: "Pong with Spells."); sub-line unchanged. (3) Seamless hero — added <video autoplay loop muted playsinline> with TODO source comment; hero uses ::before for gradient overlay and ::after for scanlines; hero-bottom-fade element dissolves bottom edge into narrative with linear-gradient; removed border-top from #narrative. (4) Faithful tooltips — replaced .vb-tooltip/.vb-tt-* with exact game DOM structure (.ability-tooltip, .tooltip-title, .tooltip-stats-row, .tooltip-stats-left, .tooltip-stat-item.{mana|cast|cooldown}, .tooltip-description, .tt-*); CSS hex values resolved directly (no CSS vars): #f0c050 gold, #c9b896 parchment, #3060b0 blue-light (mana), #c03030 red-light (cooldown), #1a0f0a brown-dark (arrow), full tt-* accent palette; tooltip positions right on desktop / above on mobile with matching arrows. Note: game's .ability-slot DOM bar is visibility:hidden at runtime; faithful reproduction is of the DOM markup pattern, not the visible Babylon GUI spell-detail box (which uses steel + #5ad0ff mana). · Open: video src + poster + og:image/og:url still placeholder; Discord invite URL still placeholder; owner should confirm hook line choice from alternatives.
- 2026-06-29 · Created landing page at docs/landing/index.html: single-page promotional site using vb-* design system components; ability tooltips pulled verbatim from index.html; all three CTA links are href="#" placeholders; no invented facts, counts, quotes, or dates; mobile-responsive. Hook chosen: "Pong, but you're a wizard." · Open: owner needs to fill in Join the Playtest URL, Discord invite URL, and Wishlist URL; og:image/og:url meta tags marked as PLACEHOLDER.
- 2026-06-29 · Audit pass on design-system files: removed invented parchment/stone sub-palette (5 tokens); restyled .vb-tooltip to the real steel panel treatment (STEEL/RIM constants); replaced all brown-tone hex values with verified game tokens; renamed "arcane" labels to neutral descriptions across all three files; grep confirms zero parchment/brown/arcane/brown-hex references remain; all retained hex values verified present in index.html/styles.css. No game files changed. · Open: see prior entry.
- 2026-06-29 · Created design-system extraction under docs/design-system/: STYLE-GUIDE.md (full token catalog + component specs), volleybolt-ui.css (standalone CSS with :root tokens + component classes), demo.html (static showcase of all components). No game files changed. · Open: local custom fonts (FF9UI.ttf, Ferrum.otf) are not web-hosted — website build will need to either bundle them or accept Press Start 2P / Cinzel fallbacks; the CSS already declares both. The CRT overlay is authored and documented but currently disabled in-game; the demo shows it on-by-default for marketing purposes.

- _(start here)_

---
_[Presentation pillar](../pillars/presentation.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
