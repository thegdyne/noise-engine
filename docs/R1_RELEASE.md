# Noise Engine — R1 Release Scope

*First Public Release Definition*

---

## Status

|             |                        |
|-------------|------------------------|
| Version     | v1.0                   |
| Status      | **LOCKED**             |
| Date        | 2025-12-24             |
| Author      | Gareth + Claude        |

---

## 1. Product Positioning

**Noise Engine = 8-layer texture instrument with playability layer**

Not competing with Pigments/Vital/Phase Plant. The best generative texture rack with deep modulation, safety, and pack workflow.

---

## 2. Component Inventory

**18 components across 7 layers**

### Generator Layer

| Component | Scope | R1 Status |
|-----------|-------|-----------|
| **Generators** | 8 slots, FRQ control, generator type selector, MIDI channel, transpose, portamento | ⚠️ Needs transpose + portamento |
| **Synthesis Methods** | DSP topology, P1-P5 custom params, 30 methods across 5 families | ✅ Done |
| **Filter System** | CUT, RES, filter type (LP/HP/BP/Notch/LP2/OFF), `~multiFilter` helper | ⚠️ Needs 3 modes |
| **Envelope System** | ATK, DEC, ENV source (OFF/CLK/MIDI), clock rate (13 divisions), `~envVCA` helper | ✅ Done |

### Modulation Layer

| Component | Scope | R1 Status |
|-----------|-------|-----------|
| **Modulators** | 4 slots, LFO/Sloth types, 5 params per slot, 4 outputs with wave/phase/polarity | ✅ Done |
| **Mod Routing** | Source→target connections, amount, offset, polarity (UNI/BI/INV) | ✅ Done |
| **Mod Matrix** | CMD+M overlay, number keys for amount/offset, arrow navigation, delete, clear all | ✅ Done |

### Performance Layer

| Component | Scope | R1 Status |
|-----------|-------|-----------|
| **Keyboard Overlay** | CMD+K toggle, QWERTY→MIDI, velocity (64/100/127), octave (Z/X), slot targeting | ✅ Done |
| **MIDI Input** | Note on/off, per-slot channel assignment (1-16), triggers envelope when ENV=MIDI | ✅ Done |

### Mixer Layer

| Component | Scope | R1 Status |
|-----------|-------|-----------|
| **Channel Strip** | ×8: fader, pan, 3-band EQ, mute/solo, echo/verb sends, lo/hi cut, gain (+0/+6/+12) | ✅ Done |
| **Master Section** | Fader, 3-band EQ with kills, compressor, limiter | ✅ Done |
| **FX System** | Echo, Reverb, state sync | ⚠️ Needs state sync fix |

### Content Layer

| Component | Scope | R1 Status |
|-----------|-------|-----------|
| **Packs** | Pack loading, manifest schema, generator file resolution, auto-preset on pack change | ✅ Done |
| **Pack Content** | Core generators, CQD_Forge sound libraries | ⚠️ Needs 10+ packs |
| **Imaginarium** | Image→SoundSpec extraction, candidate generation, safety gates, diversity selection, pack export | ✅ Done |

### Session Layer

| Component | Scope | R1 Status |
|-----------|-------|-----------|
| **Presets** | CMD+S/O save/load, generator + mixer state, file management | ⚠️ Needs unsaved indicator + init |
| **Clock** | BPM control (20-300), 13 divisions, audio-rate trigger buses | ✅ Done |

### System Layer

| Component | Scope | R1 Status |
|-----------|-------|-----------|
| **UI Shell** | Window, layout, theme, SC connection status, header disable until connected, keyboard shortcuts | ✅ Done |

---

## 3. R1 Gaps

### Generator Layer

| Gap | Component | Effort |
|-----|-----------|--------|
| Transpose (±2 octaves) | Generators | 1-2 hr |
| Portamento (OFF/SHORT/LONG) | Generators | 1-2 hr |
| Notch filter mode | Filter System | 1 hr |
| LP2 (12dB) filter mode | Filter System | 1 hr |
| OFF (bypass) filter mode | Filter System | 30 min |

### Mixer Layer

| Gap | Component | Effort |
|-----|-----------|--------|
| State sync on reconnect | FX System | 1 hr |

### Content Layer

| Gap | Component | Effort |
|-----|-----------|--------|
| 10+ CQD_Forge packs | Pack Content | 3-4 sessions |
| Imaginarium vs Forge naming unification | Packs | 1-2 hr |

### Session Layer

| Gap | Component | Effort |
|-----|-----------|--------|
| Unsaved changes indicator | Presets | 1 hr |
| Init preset | Presets | 30 min |
| Validate mod routing saved in presets | Presets | 15 min |

### Documentation

| Gap | Component | Effort |
|-----|-----------|--------|
| Update manual for new filter modes | Manual | 1 hr |
| Update IDEAS.md (remove done items) | Docs | 5 min |
| Update README.md for R1 | Docs | 1 hr |
| macOS install guide | Docs | 1 hr |
| Linux install guide (basic) | Docs | 30 min |

### Release Gates

| Gap | Component | Effort |
|-----|-----------|--------|
| LICENSE file (MIT) | Release | 5 min |
| CHANGELOG.md | Release | 30 min |
| index.html update (R1 summary) | Marketing | 1 hr |
| Discord announcement ready | Marketing | 30 min |
| GitHub release / tag | Release | 15 min |

---

## 4. R1 Effort Summary

| Category | Effort |
|----------|--------|
| Generator gaps (transpose, porta, filters) | 4-5 hours |
| Mixer gaps (FX sync) | 1 hour |
| Session gaps (presets + validation) | 1.75 hours |
| Content gaps (naming unification) | 1-2 hours |
| Content gaps (CQD_Forge packs) | 3-4 sessions |
| Documentation (manual, README, install guides) | 3.5 hours |
| Release gates (LICENSE, CHANGELOG, index.html, Discord, tag) | 2.5 hours |
| **Total** | **~7 sessions** |

---

## 4a. Polish (Pre Go-Live)

Not blocking R1 but should address before public release:

| Item | Effort |
|------|--------|
| UI font audit | 1 hr |
| Empty mod state polish | 30 min |

---

## 5. Explicitly Out of Scope (R1)

### Deferred to R1.1

| Item | Rationale |
|------|-----------|
| Preset expansion (Phase 2-4) | Current save/load works |
| Velocity/AT/pitchbend as mod sources | Enhancement, not broken |
| Unified param addressing | Architecture cleanup |
| Cross-platform testing | Need testers first |
| MIDI Learn | Power user feature |

### Deferred Indefinitely

| Item | Rationale |
|------|-----------|
| SC reconnect lifecycle | Restart app acceptable |
| CPU meter | SC handles externally |
| Undo/Redo | Massive scope |
| Error console panel | Terminal acceptable |
| Audio I/O settings | SC handles externally |

### Never (Architecture Decisions)

| Item | Rationale |
|------|-----------|
| Sampler/buffer generator | Scope creep, not this synth |
| Per-slot FX | Master chain is the design |
| Pseudo-poly allocator | 8-slot texture rack, not polysynth |
| New filter characters (ladder/MS-20/SEM) | Current filter works |
| Sequencer (note or parameter) | Deliberate design choice. External MIDI/DAW for sequencing. Texture instrument with clock-synced envelopes + modulation. |

---

## 6. Definition of Done

### R1 is complete when:

**Generator Layer**
- [ ] 8 slots functional with all core params
- [ ] Transpose selector (±2 octaves)
- [ ] Portamento selector (OFF/SHORT/LONG)
- [ ] Filter modes: LP, HP, BP, Notch, LP2, OFF
- [ ] 30 synthesis methods passing validation
- [ ] P1-P5 functional with labels and tooltips

**Modulation Layer**
- [ ] 4 modulator slots (LFO/Sloth)
- [ ] Mod routing with amount/offset/polarity
- [ ] Mod Matrix (CMD+M) fully functional

**Performance Layer**
- [ ] Keyboard Overlay (CMD+K) functional
- [ ] MIDI input with per-slot channel assignment

**Mixer Layer**
- [ ] 8 channel strips with full controls
- [ ] Master section with EQ/comp/limiter
- [ ] FX (Echo/Reverb) with state sync working

**Content Layer**
- [ ] Pack loading infrastructure complete
- [ ] 10+ CQD_Forge packs shipped
- [ ] Imaginarium pipeline functional
- [ ] Imaginarium/Forge naming conventions unified

**Session Layer**
- [ ] Preset save/load (CMD+S/O)
- [ ] Unsaved changes indicator
- [ ] Init preset available
- [ ] Mod routing saved in presets (verify)

**System Layer**
- [ ] UI shell complete
- [ ] SC connection management working

**Documentation**
- [ ] Manual updated for new filter modes
- [ ] IDEAS.md cleaned up (remove done items)
- [ ] README.md updated for R1
- [ ] macOS install guide
- [ ] Linux install guide (basic)

**Release Gates**
- [ ] LICENSE file (MIT)
- [ ] CHANGELOG.md
- [ ] index.html updated (R1 summary)
- [ ] Discord announcement ready
- [ ] GitHub release / tag

---

## 7. Success Criteria

| Criterion | Measure |
|-----------|---------|
| Playable | Can make music within 5 minutes of launch |
| Content | 10+ packs with 80+ generators |
| Stable | No crashes during normal use |
| Complete | All R1 gaps closed |
| Documented | User can understand core workflow |

---

## 8. Timeline

| Phase | Sessions | Deliverable |
|-------|----------|-------------|
| Generator gaps | 1 | Transpose, portamento, filter modes |
| FX + Presets gaps | 1 | State sync, unsaved indicator, init, verify mod routing |
| Content gaps | 0.5 | Naming unification |
| CQD_Forge | 3-4 | 10+ packs |
| Documentation | 1 | Manual, README, install guides, IDEAS cleanup |
| Release prep | 0.5 | LICENSE, CHANGELOG, index.html, tag |
| Polish + Testing | 1 | Font audit, mod state, final verification |
| **Total** | **8-9 sessions** | **R1 Release** |

---

## 9. Post-R1 Roadmap Preview

### R1.1 (Enhancement Release)
- Preset expansion (mod routing, master, BPM in presets)
- Velocity/AT/pitchbend as mod sources
- Cross-platform support (Windows/Linux)
- Unified param addressing

### R2 (Future)
- Standalone packaging (bundled SC runtime)
- Plugin/VST investigation

---

## 10. R1 Delivery Status

### Current Completion: **49%**

| Layer | Done | Total | % |
|-------|------|-------|---|
| Generator | 3.5 | 6 | 58% |
| Modulation | 3 | 3 | 100% |
| Performance | 2 | 2 | 100% |
| Mixer | 2.5 | 3 | 83% |
| Content | 2 | 4 | 50% |
| Session | 1 | 4 | 25% |
| System | 2 | 2 | 100% |
| Documentation | 0.5 | 5 | 10% |
| Release Gates | 0 | 5 | 0% |
| **Total** | **16.5** | **34** | **49%** |

### By Category

| Category | Status |
|----------|--------|
| **Core functionality** | ~75% (most components working) |
| **R1 feature gaps** | ~40% (transpose, porta, filters, presets) |
| **Content** | ~20% (packs not yet created) |
| **Documentation** | ~10% (Windows guide exists) |
| **Release gates** | 0% (not started) |

### Remaining Work

| Item | Effort | Impact |
|------|--------|--------|
| CQD_Forge packs | 3-4 sessions | High — no content = no release |
| Generator gaps | 1 session | Medium — playability |
| Documentation | 1 session | Medium — onboarding |
| Everything else | 1-2 sessions | Low-Medium |

---

## 11. Focus Recommendation

**Next session priority:**

1. **CQD_Forge packs** — Biggest blocker, most effort, highest impact
2. **Generator gaps** — Quick wins (transpose, porta, filters)
3. **Documentation** — Can parallelize with pack creation

**Don't start until packs are done:**
- Release gates (LICENSE, CHANGELOG, index.html, tag)
- Polish items

---

**R1 SCOPE LOCKED — 2025-12-24**
