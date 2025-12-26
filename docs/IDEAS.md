# IDEAS.md — Noise Engine Backlog

*Updated: 2025-12-26*

> **Note:** This file contains only **not-yet-done** work.  
> Completed features live in R1_RELEASE.md and the codebase.

---

## Quick Reference

| # | Feature | Category | Effort |
|---|---------|----------|--------|
| 1 | Master output routing | Output | Medium |
| 2 | Recording / bounce | Export | Large |
| 3 | Preset browser | UX | Medium |
| 4 | MIDI Learn | Control | Medium |
| 5 | Mod matrix enhancements | Modulation | Small |
| 6 | Keyboard mode hardening | Performance | Small |
| 7 | Character FX modules | FX | Medium |
| 8 | Send system improvements | FX | Small |
| 9 | Forge validation upgrades | Tooling | Small |
| 10 | Pack build artefacts | Tooling | Small |
| 11 | Buffer-based methods | Synthesis | Large |
| 12 | Sequencer panel | Composition | Large |
| 13 | Performance mode | UI | Medium |

---

## Output & Routing

### 1. Master Output Routing + Multi-Out

Route master to selectable hardware outputs; optionally expose per-slot direct outs for DAW mixing.

**Features**
- Output device selection in UI
- Phones / Monitors A/B quick switch
- Per-slot stereo direct outs (8 × L/R bus pairs)

**Hooks**
- SC: `supercollider/effects/master_passthrough.scd` (parameterise `outBus`)
- SC: `supercollider/core/audio_device.scd`
- Py: `src/gui/master_section.py`, `src/gui/audio_device_selector.py`

---

## Recording & Export

### 2. Recording / Bounce-to-Disk

Record what you hear, and/or offline bounce N bars with deterministic clock.

**Modes**
- Realtime record (live performance capture)
- Offline bounce (N bars @ BPM, optionally per-slot stems)

**Hooks**
- SC: Recorder SynthDef using `DiskOut` or `RecordBuf`
- Py: Controls in `src/gui/main_frame.py` (Record/Stop, file path, status)

---

## Preset UX

### 3. Preset Browser + Tags + Search

Fast preset auditioning and management without file dialogs.

**Features**
- Save As / duplicate / rename / delete
- Search box + pack filter + "recent" list
- Tags, rating, notes fields
- Optional: embedded audio preview per preset

**Hooks**
- Py: New panel `src/gui/preset_browser.py`
- Schema: Extend `src/presets/preset_schema.py` with metadata fields

---

## MIDI & Controllers

### 4. MIDI Learn (CC-First)

Map hardware controls to any on-screen param with a learn gesture.

**Scope**
- CC mapping only (skip NRPN/MPE initially)
- Click param → move CC → mapped
- Visual indication of mapped params

**Hooks**
- Py: Learnable-param mixin in `src/gui/widgets.py`
- Py: Learn mode toggle in `src/gui/main_frame.py`
- Persist: `~/.config/noise-engine/midi_maps.json` or in preset

---

## Modulation

### 5. Mod Matrix Enhancements

Make routing edits faster and reduce "oops" moments in performance.

**Features**
- Per-routing INV toggle in cell/popup
- Lock parameters from randomisation
- Auto-allocation presets ("gentle", "textural", "rhythmic")

**Hooks**
- Py: `src/gui/mod_depth_popup.py`, `src/gui/mod_matrix_cell.py`
- State: `src/gui/mod_routing_state.py`

---

## Keyboard & Performance

### 6. Keyboard Mode Hardening

Make the overlay unbreakable and obvious in performance.

**Features**
- Always display + sync "focused slot" state
- Hold/latch gate toggle (spacebar)
- Optional: chord mode (triad/7th) + scale quantise

**Hooks**
- Py: `src/gui/keyboard_overlay.py`, `src/gui/main_frame.py`

---

## FX System

### 7. Character FX Modules

Widen the palette without adding lots of generic FX.

**Candidates**
- Chorus / Ensemble
- Shimmer (reverb + pitch feedback)
- Frequency Shifter

**Hooks**
- SC: New `supercollider/effects/<name>.scd`
- Py: `src/gui/fx_window.py`, `src/gui/inline_fx_strip.py`

### 8. Send System Improvements

More usable send/return behaviour for Echo/Reverb.

**Features**
- Pre/Post send toggle per channel
- Ducking on returns (sidechain from dry sum)
- Tempo divisions + clock sync

**Hooks**
- SC: `supercollider/core/channel_strips.scd`, `supercollider/effects/tape_echo.scd`
- Py: `src/gui/mixer_panel.py`, `src/gui/inline_fx_strip.py`

---

## Tooling & Validation

### 9. Forge Validation Upgrades

Fewer false positives + catch silent/broken generators early.

**Features**
- Strip comments before scanning for helper usage
- Match call tokens rather than bare helper names
- Render-and-measure checks (RMS, DC, crest, silence)

**Hooks**
- `tools/forge_validate.py`, `tools/forge_audio_validate.py`

### 10. Pack Build Artefacts

Reproducible builds + easy auditioning.

**Features**
- Embed build metadata in `manifest.json` (git hash, date, versions)
- Generate preview WAV set per pack (8–16 files)

**Hooks**
- `imaginarium/export.py`, `tools/forge_gate.py`

---

## Big Bets (Parking Lot)

### 11. Buffer-Based Methods

Unlock sample playback + buffer granular as first-class synthesis methods.

**Features**
- One-shot + loop playback with envelope/filter
- GrainBuf/TGrains on user buffers
- Modulatable via mod matrix

**Hooks**
- New templates in `imaginarium/methods/*`
- Pack generator `.scd` + JSON axis definitions

### 12. Sequencer Panel

Clock-driven patterns + per-slot trigger modes, integrated with routing.

**Notes**
- Bottom panel placeholder exists in UI
- Deliberate R1 decision to defer (external MIDI/DAW for sequencing)

### 13. Performance Mode

Full-screen minimal UI with big controls + panic/kill switches.

**Features**
- Large faders and meters
- Essential controls only
- Panic button (silence all)
- Clock-synced scene transitions

---

*Last updated: 2025-12-26 — R1 release prep*
