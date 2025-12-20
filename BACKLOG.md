# Noise Engine Backlog

*Updated: December 2025*

---

## Now
- [x] Pack System — Phase 1: Infrastructure ✅
- [x] Pack System — Phase 2: UI Integration ✅

---

## Next (spec approved, ready to plan)
- [ ] Pack System — Phase 3: Preset Integration

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
