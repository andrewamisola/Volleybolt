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

- 2026-07-06 · Overdrive beam upgraded from Tone.js synthesis to real samples (sfx/beam_windup.ogg one-shot, sfx/beam_roar_loop.ogg stereo loop → sfxBus direct, sfx/beam_rumble_loop.ogg earthquake loop panned ±0.7 toward opponent gate). Three shared ToneAudioBuffers / per-side Players. MembraneSynth overdriveBeat deleted; window.onOverdriveBeat no-op; beamRoarUpdate no-op stub. New beamRumbleStart/Stop methods (loaded-guard, boolean return for retry). State machine gains rumbleOn flag (connecting=not-blocked, crackleOn and rumbleOn mutually exclusive). Background dim: backdropLayer.color lerped to 35% while any juiceActive, back in 0.3s; cached origColor; no per-frame allocs. Commit b7e6ffa on juice-overdrive. · Open: Tone.js ToneAudioBuffer(url) constructor untested against exact Tone build in repo — if it silently fails, Players will never mark .loaded and beamRoarStart will retry forever (harmless but silent). Verify in browser.

- 2026-07-06 · Implemented Task 5 overdrive beam audio (index.html only). Synth architecture: two independent persistent per-side roar loops (brown noise + sine oscillator through sweeping bandpass filter, sfxBus) plus per-side deflection crackle (highpass white noise). One-shot sounds (windup riser, eruption MembraneSynth boom, power-down sawtooth fizzle) use create-on-use/dispose pattern so two simultaneous channels never share voice objects. Damage-beat boom is a shared mono MembraneSynth; volume scales with chunk. State machine in updateMatchPresentation section 1d: edge-triggered per side, mirrors _castingDesired pattern with desired-state flags. Stop fires on ALL channel-death paths via sim-state falling edge + beamRoarStopAll() backstops at both game-exit call sites. window.onOverdriveBeat defined in the audio closure for direct synths access. · Open: MembraneSynth.triggerAttackRelease pitch/timbre for eruption vs beat boom untested by ear — tune in playtest. Volumes (-6 dB eruption, -14 dB roar, -26 dB crackle) are starting points.

- 2026-07-02 · Fixed mono-synth retrigger crash in the menu sounds: hover + click landing on the same tick threw Tone's "start time must be strictly greater than previous" and killed the confirm sound. All UI beeps now route through uiBeep(), which schedules monotonically (bumps 5 ms past the last scheduled note) and wraps triggerAttackRelease in try/catch. · Open: none.
- 2026-07-02 · Implemented the stubbed ToneSFX.uiHover/uiConfirm/uiBack as JRPG menu sounds: lazy square-wave Tone.Synth (−18 dB, instant envelope) straight into sfxBus so the SFX slider governs it. Cursor blip on .menu-btn/.fps-arrow hover, rising two-note confirm on click, falling two-note cancel on .menu-btn-ghost (Back/Cancel) and Esc-close; settings sliders/toggles tick on change. Wired via document-level delegation, so pause + debug menus get sounds for free. uiHover never awaits init (hover can precede the audio-unlock gesture). · Open: pitches/volume tuned by ear in one pass — Andrew may want different notes.
- _(start here)_

---
_[Presentation pillar](../pillars/presentation.md) · [Shared Core](../SHARED_CORE.md) · [Master](../../PROJECT.md)_
