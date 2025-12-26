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
| **Generators** | 8 slots, FRQ control, generator type selector, MIDI channel, transpose, portamento | ✅ Done |
| **Synthesis Methods** | DSP topology, P1-P5 custom params, 30 methods across 5 families | ✅ Done |
| **Filter System** | CUT, RES, filter type (LP/HP/BP/Notch/LP2/OFF), `~multiFilter` helper | ✅ Done |
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
| **FX System** | Echo, Reverb, state sync | ✅ Done |

### Content Layer

| Component | Scope | R1 Status |
|-----------|-------|-----------|
| **Packs** | Pack loading, manifest schema, generator file resolution, auto-preset on pack change | ✅ Done |
| **Pack Content** | Core generators, CQD_Forge sound libraries | ✅ Done (19 packs) |
| **Imaginarium** | Image→SoundSpec extraction, candidate generation, safety gates, diversity selection, pack export | ✅ Done |

### Session Layer

| Component | Scope | R1 Status |
|-----------|-------|-----------|
| **Presets** | CMD+S/O save/load, generator + mixer + FX state, file management | ✅ Done |
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
| ~~Transpose (±2 octaves)~~ | ~~Generators~~ | ~~1-2 hr~~ ✅ |
| ~~Portamento (OFF/SHORT/LONG)~~ | ~~Generators~~ | ~~1-2 hr~~ ✅ |
| ~~Notch filter mode~~ | ~~Filter System~~ | ~~1 hr~~ ✅ |
| ~~LP2 (12dB) filter mode~~ | ~~Filter System~~ | ~~1 hr~~ ✅ |
| ~~OFF (bypass) filter mode~~ | ~~Filter System~~ | ~~30 min~~ ✅ |

### Mixer Layer

| Gap | Component | Effort |
|-----|-----------|--------|
| ~~State sync on reconnect~~ | ~~FX System~~ | ~~1 hr~~ ✅ |

### Content Layer

| Gap | Component | Effort |
|-----|-----------|--------|
| ~~Move core generators to packs/core/~~ | ~~Packs~~ | ~~1-2 hr~~ ✅ |
| ~~10+ CQD_Forge packs~~ | ~~Pack Content~~ | ~~3-4 sessions~~ ✅ (19 packs!) |
| ~~Imaginarium vs Forge naming unification~~ | ~~Packs~~ | ~~1-2 hr~~ ✅ |

### Session Layer

| Gap | Component | Effort |
|-----|-----------|--------|
| ~~Unsaved changes indicator~~ | ~~Presets~~ | ~~1 hr~~ ✅ |
| ~~Init preset~~ | ~~Presets~~ | ~~30 min~~ ✅ |
| ~~Validate mod routing saved in presets~~ | ~~Presets~~ | ~~15 min~~ ✅ |
| ~~FX state saved in presets~~ | ~~Presets~~ | ~~1-2 hr~~ ✅ |

### Documentation

| Gap | Component | Effort |
|-----|-----------|--------|
| ~~Update manual for new filter modes~~ | ~~Manual~~ | ~~1 hr~~ ✅ |
| ~~Update IDEAS.md (remove done items)~~ | ~~Docs~~ | ~~5 min~~ ✅ |
| ~~Update README.md for R1~~ | ~~Docs~~ | ~~1 hr~~ ✅ |
| ~~macOS install guide~~ | ~~Docs~~ | ~~1 hr~~ ✅ |
| ~~Linux install guide (basic)~~ | ~~Docs~~ | ~~30 min~~ ✅ |

### Release Gates

| Gap | Component | Effort |
|-----|-----------|--------|
| ~~LICENSE file (MIT)~~ | ~~Release~~ | ~~5 min~~ ✅ |
| ~~CHANGELOG.md~~ | ~~Release~~ | ~~30 min~~ ✅ |
| ~~index.html update (R1 summary)~~ | ~~Marketing~~ | ~~1 hr~~ ✅ |
| ~~Discord announcement ready~~ | ~~Marketing~~ | ~~30 min~~ ✅ |
| ~~GitHub release / tag~~ | ~~Release~~ | ~~15 min~~ ✅ |

---

## 4. R1 Effort Summary

| Category | Effort |
|----------|--------|
| ~~Generator gaps (filters)~~ | ~~2.5 hours~~ ✅ |
| ~~Mixer gaps (FX sync)~~ | ~~1 hour~~ ✅ |
| ~~Session gaps (unsaved indicator)~~ | ~~1 hour~~ ✅ |
| ~~Session gaps (init preset)~~ | ~~30 min~~ ✅ |
| ~~Session gaps (verify mod routing)~~ | ~~15 min~~ ✅ |
| ~~Session gaps (FX save in presets)~~ | ~~1-2 hr~~ ✅ |
| ~~Content gaps (core restructure)~~ | ~~1-2 hours~~ ✅ |
| ~~Content gaps (naming unification)~~ | ~~1-2 hours~~ ✅ |
| ~~Content gaps (CQD_Forge packs)~~ | ~~3-4 sessions~~ ✅ (19 packs!) |
| ~~Documentation (manual, IDEAS, Linux, README, macOS)~~ | ~~3.5 hours~~ ✅ |
| ~~Release gates (LICENSE, CHANGELOG, index.html, Discord, tag)~~ | ~~2.5 hours~~ ✅ |
| **Total** | **COMPLETE** |

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
- [x] 8 slots functional with all core params
- [x] Transpose selector (±2 octaves)
- [x] Portamento selector (OFF/SHORT/LONG)
- [x] Filter modes: LP, HP, BP, Notch, LP2, OFF
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
- [x] 8 channel strips with full controls
- [x] Master section with EQ/comp/limiter
- [x] FX (Echo/Reverb) with state sync working

**Content Layer**
- [x] Core generators moved to packs/core/
- [x] Pack loading infrastructure complete
- [x] 10+ CQD_Forge packs shipped (19 delivered!)
- [x] Imaginarium pipeline functional
- [x] Imaginarium/Forge naming conventions unified

**Session Layer**
- [x] Preset save/load (CMD+S/O)
- [x] Unsaved changes indicator
- [x] Init preset available
- [x] Mod routing saved in presets (verify)
- [x] FX state saved in presets

**System Layer**
- [ ] UI shell complete
- [ ] SC connection management working

**Documentation**
- [x] Manual updated for new filter modes
- [x] IDEAS.md cleaned up (remove done items)
- [x] README.md updated for R1
- [x] macOS install guide
- [x] Linux install guide (basic)

**Release Gates**
- [x] LICENSE file (MIT)
- [x] CHANGELOG.md
- [x] index.html updated (R1 summary)
- [x] Discord announcement ready
- [x] GitHub release / tag

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
| ~~Generator gaps~~ | ~~0.5~~ | ~~Filter modes~~ ✅ |
| ~~Presets gaps~~ | ~~0.5~~ | ~~Unsaved indicator~~ ✅ |
| ~~Presets gaps~~ | ~~0.25~~ | ~~Init preset~~ ✅ |
| ~~Presets gaps~~ | ~~0.1~~ | ~~Verify mod routing~~ ✅ |
| ~~Presets gaps~~ | ~~0.5~~ | ~~FX save in presets~~ ✅ |
| ~~Content gaps~~ | ~~0.5~~ | ~~Core restructure~~ ✅ |
| ~~Content gaps~~ | ~~0.5~~ | ~~Naming unification~~ ✅ |
| ~~CQD_Forge~~ | ~~3-4~~ | ~~10+ packs~~ ✅ (19 delivered!) |
| ~~Documentation~~ | ~~1~~ | ~~Manual, README, IDEAS, Linux, macOS~~ ✅ |
| ~~Release prep~~ | ~~0.5~~ | ~~LICENSE, CHANGELOG, index.html, Discord, tag~~ ✅ |
| ~~Polish + Testing~~ | ~~1~~ | ~~Font audit, mod state, final verification~~ ✅ |
| **Total** | **COMPLETE** | **R1 Released 2025-12-26** |

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

### Current Completion: **100%** 🎉

| Layer | Done | Total | % |
|-------|------|-------|---|
| Generator | 6 | 6 | 100% |
| Modulation | 3 | 3 | 100% |
| Performance | 2 | 2 | 100% |
| Mixer | 3 | 3 | 100% |
| Content | 5 | 5 | 100% |
| Session | 5 | 5 | 100% |
| System | 2 | 2 | 100% |
| Documentation | 5 | 5 | 100% |
| Release Gates | 5 | 5 | 100% |
| **Total** | **36** | **36** | **100%** |

### By Category

| Category | Status |
|----------|--------|
| **Core functionality** | 🟢 **100%** |
| **R1 feature gaps** | 🟢 **100%** |
| **Content** | 🟢 **100%** |
| **Documentation** | 🟢 **100%** |
| **Release gates** | 🟢 **100%** |

### 🎉 R1 RELEASED — 2025-12-26 🎉

---

## 11. Focus Recommendation

**R1 SHIPPED!**

- GitHub: https://github.com/thegdyne/noise-engine
- Landing Page: https://thegdyne.github.io/noise-engine/
- Discord: Announced

**~1 session to R1!**

---

**🎉 R1 RELEASED — 2025-12-26 🎉**
