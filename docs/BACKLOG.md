# Noise Engine Backlog

*Updated: December 2025*

---

## Now
- [ ] Generator Envelope Compliance — Fix pack generators to use ~envVCA (see `docs/GENERATOR_ENVELOPE_COMPLIANCE.md`)

## Next (spec approved, ready to plan)
- [ ] Pack System — Phase 3: Preset Integration (blocked by envelope compliance)
- [ ] Imaginarium Phase 2 — Text/audio input, custom params exposed

---

## Needs Spec (Large/Medium)
- [ ] Preset System
- [ ] MIDI Learn
- [ ] Mod Matrix Expansion

---

## Mopup (Small — just do it)
- [ ] UI font audit — improve visibility across all labels (like HI/MID/LO fix)
- [ ] Empty mod state polish

---

## Generator Envelope Compliance (Pre-Phase 3 Blocker)

**Analysis:** `docs/GENERATOR_ENVELOPE_COMPLIANCE.md`

**Phase 1: Fix Pack Generators**
- [ ] Update Electric Shepherd generators (8 files) — replace `sig * amp` with `~envVCA`
- [ ] Update R'lyeh Collection generators (8 files) — replace `sig * amp` with `~envVCA`
- [ ] Test each generator: OFF mode sounds identical
- [ ] Test each generator: CLK mode triggers envelope
- [ ] Test each generator: MIDI mode triggers envelope
- [ ] Test ATK/DEC sliders have audible effect

**Phase 2: CI Enforcement**
- [ ] Add test to `test_generators.py`: SCD must contain `~envVCA`
- [ ] Add test to `test_packs.py`: Pack SCD files must contain `~envVCA`
- [ ] Verify CI passes on all existing core generators

**Phase 3: Spec Update**
- [ ] Update `GENERATOR_SPEC.md` — clarify `~envVCA` is REQUIRED
- [ ] Add "Common Mistakes" section documenting `sig * amp` anti-pattern
- [ ] Document future drone-only pattern (for reference, not implementing now)

---

## Imaginarium

**Spec:** `imaginarium/` module + `docs/IMAGINARIUM_SPEC.md`

### Phase 1: Core Pipeline ✅ COMPLETE
- [x] Image → SoundSpec extraction (brightness, noisiness)
- [x] Sobol quasi-random candidate generation
- [x] NRT SuperCollider rendering
- [x] Safety gates (silence, clipping, DC offset)
- [x] librosa feature extraction
- [x] Fit scoring against target SoundSpec
- [x] Farthest-first diversity selection
- [x] Pack export (Noise Engine-compliant)

### Phase 1 Methods ✅
- [x] subtractive/bright_saw
- [x] subtractive/dark_pulse
- [x] fm/simple_fm
- [x] physical/karplus (NRT render issue)

### Phase 1 Backlog
- [ ] Fix physical/karplus NRT rendering (Pluck trigger in NRT mode)
- [ ] Add more methods: modal, waveguide, complex_fm, noise_filtered
- [ ] Test generated pack in Noise Engine

### Phase 2: Enhanced Input
- [ ] Text → SoundSpec (NLP keywords to parameters)
- [ ] Audio → SoundSpec (analyze reference audio)
- [ ] Expose custom_params in generated generators

### Image Generator Backlog (lower priority)
- [ ] Backlog A: Calibration suite (hue parameter, sat/value tiers)
- [ ] Backlog B: Showcase suite (neutral backgrounds default)
- [ ] Backlog C: Harmony separability (distinct colour_* presets)
- [ ] Backlog D: Corpus health metric (hue histogram analysis)

---

## Ideas (not committed)
- Keyboard Mode (CMD+K)
- Imaginarium natural language interface
- Filter improvements (ladder, MS-20, etc)
- Eurorack send/return
- Generator waveform display
- Performance profiling
- Per-generator transpose
- Multitimbral mode

---

## Done (recent)
- ✅ **Imaginarium Phase 1** — Image → 8 diverse generators pipeline
- ✅ Pack System — Phase 1: Infrastructure
- ✅ Pack System — Phase 2: UI Integration
- ✅ Shift + -/+ for offset control
- ✅ FX System v1 — Inline FX strip with HEAT, ECHO, REVERB, FILTER modules
- ✅ TURBO presets (INI/T1/T2) for all FX modules
- ✅ Filter sync with tempo-synced LFO modulation
- ✅ EQ labels HI/MID/LO on channel strip
- ✅ Numeric keys work while arrows held
- ✅ Quadrature modulation (4 outputs per mod slot)
- ✅ NORM/INV → Invert terminology update
- ✅ Channel strips (volume, pan, mute, solo, EQ)
- ✅ Master section (fader, meters, EQ, compressor, limiter)
- ✅ 30+ new generators (classic synths, 808, atmospheric)
- ✅ MIDI frequency routing fix (userParams)
- ✅ CI/CD pipeline (207 tests)

## Pack Presets
- [ ] Save/load generator slot configurations at pack level (which generators in which slots)

## Frontend/SC State Sync on Restart
- [ ] Handle case where Python frontend restarts but SC still running with previous state
- Options to develop:
  1. **Warm restart**: Query SC state and restore frontend to match (generators, mod routes, etc.)
  2. **Cold restart**: Full reset of both Python and SC to clean state
- Considerations:
  - SC could expose `/state` OSC endpoint returning current config
  - Frontend stores last known state to disk (JSON) for recovery
  - Startup flag: `--resume` vs `--reset`
  - Auto-detect if SC has existing synths running

## Web-Based Manual
- [ ] Create documentation website for Noise Engine
- Consider: GitHub Pages, MkDocs, or simple HTML
- Sections: Getting started, Generators, Packs, Modulation, MIDI, API reference
- Include screenshots, audio examples
- Auto-generate generator list from pack manifests

## Housekeeping
- [ ] Merge dev → main (tests failing in main due to new tests not pushed)

## FX System v1.1
- [ ] P1: State sync on reconnect - create _sync_master_state() method to push UI→SC on connect/reconnect
- [ ] P2: fx_window.py uses hardcoded OSC paths - refactor to use OSC_PATHS for SSOT
- [ ] P2: master_passthrough LR4 comment doesn't match implementation - clarify or refactor EQ split

## FX System Future
- [ ] Per-channel echo/verb send knobs in mixer strip
- [ ] Reverb pre-delay parameter
- [ ] FX audio tuning (adjust default values, ranges, response curves)
- [ ] Fidelity FX - integrate with new FX system
