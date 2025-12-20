# Noise Engine Backlog

*Updated: December 20, 2025*

---

## Now
- [ ] Expand Presets — add channel EQ, BPM, master settings to preset schema

## Next (spec approved, ready to plan)
- [ ] Cross-Platform Testing — Windows & Linux compatibility
- [ ] Integration Tests — tests that boot SuperCollider

---

## Cross-Platform Testing

**Goal:** Ensure Noise Engine runs on Windows and Linux, not just macOS.

**Tasks:**
- [ ] Recruit Windows tester (Discord?)
- [ ] Recruit Linux tester (Discord?)
- [ ] Document platform-specific setup (SC paths, Python env)
- [ ] Test PyQt5 rendering on Windows
- [ ] Test PyQt5 rendering on Linux (X11/Wayland)
- [ ] Verify OSC communication works cross-platform
- [ ] Check file paths (presets dir, pack loading)
- [ ] Create Windows install guide
- [ ] Create Linux install guide

**Known Risks:**
- SuperCollider paths differ per OS
- Audio device APIs vary (CoreAudio vs WASAPI vs ALSA/Jack)
- Font rendering may differ
- Keyboard shortcuts (Cmd vs Ctrl)

---

## Needs Spec (Large/Medium)
- [ ] MIDI Learn
- [ ] Mod Matrix Expansion
- [ ] SC State Sync on Restart

---

## Mopup (Small — just do it)
- [ ] UI font audit — improve visibility across all labels
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
- ✅ Preset System — Save/Load with Ctrl+S/O (Dec 20)
- ✅ Generator Envelope Compliance — All 16 pack generators fixed (Dec 20)
- ✅ Doc Reorganization — archive/, ideas/, demos/ (Dec 20)
- ✅ Pack System — Phase 1-3 complete
- ✅ FX System v1 — Inline FX strip with HEAT, ECHO, REVERB, FILTER
- ✅ TURBO presets (INI/T1/T2) for all FX modules
- ✅ Channel strips (volume, pan, mute, solo, EQ)
- ✅ Master section (fader, meters, EQ, compressor, limiter)
- ✅ Mod Matrix — 16×40 routing grid
- ✅ Mod Sources — LFO + Sloth
- ✅ 53 generators total
- ✅ CI/CD pipeline (280 tests)

---

## Web-Based Manual
- [ ] Create documentation website for Noise Engine
- Consider: GitHub Pages, MkDocs, or simple HTML
- Sections: Getting started, Generators, Packs, Modulation, MIDI, API reference
- Include screenshots, audio examples
- Auto-generate generator list from pack manifests

## FX System v1.1
- [ ] P1: State sync on reconnect - create _sync_master_state() method
- [ ] P2: fx_window.py uses hardcoded OSC paths - refactor to use OSC_PATHS
- [ ] P2: master_passthrough LR4 comment doesn't match implementation

## FX System Future
- [ ] Per-channel echo/verb send knobs in mixer strip
- [ ] Reverb pre-delay parameter
- [ ] FX audio tuning (adjust default values, ranges, response curves)
