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

- _(start here)_

---
_[Presentation pillar](../pillars/presentation.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
