# Agent · Audio  ·  Presentation pillar

**Owns.** Tone.js synthesis, procedural SFX, the solfeggio / isochronic layer.

**Reports into** → [Presentation pillar](../pillars/presentation.md) · also reads [Shared Core](../SHARED_CORE.md)

## Grounded in (external canon)
- [Tone.js docs](https://tonejs.github.io/)
- [Web Audio API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)

## Internal docs
- `docs/AUDIO.md` _(author + maintain)_

## Invariants
- Audio reads sim state, never writes it.
- Audio context starts on a user gesture (browser autoplay policy).

## Working log
_Append-only. Newest at top. Each entry: date · decision/change · open issues._

- 2026-07-02 · Fixed mono-synth retrigger crash in the menu sounds: hover + click landing on the same tick threw Tone's "start time must be strictly greater than previous" and killed the confirm sound. All UI beeps now route through uiBeep(), which schedules monotonically (bumps 5 ms past the last scheduled note) and wraps triggerAttackRelease in try/catch. · Open: none.
- 2026-07-02 · Implemented the stubbed ToneSFX.uiHover/uiConfirm/uiBack as JRPG menu sounds: lazy square-wave Tone.Synth (−18 dB, instant envelope) straight into sfxBus so the SFX slider governs it. Cursor blip on .menu-btn/.fps-arrow hover, rising two-note confirm on click, falling two-note cancel on .menu-btn-ghost (Back/Cancel) and Esc-close; settings sliders/toggles tick on change. Wired via document-level delegation, so pause + debug menus get sounds for free. uiHover never awaits init (hover can precede the audio-unlock gesture). · Open: pitches/volume tuned by ear in one pass — Andrew may want different notes.
- _(start here)_

---
_[Presentation pillar](../pillars/presentation.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
