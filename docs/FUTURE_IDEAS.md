# Future Ideas

Captured ideas for potential future development.

---

## Routing & Control

- **External Audio Processing** - Eurorack send/return via audio interface
- **LFO Modulation Routing** - turn on/off at target
- **Modulation routing system** - how to wire source → destination?

---

## Generator System

- ~~Adding customised control parameters to generators~~ ✓ Done (JSON custom_params)
- ~~MIDI pitch/gate to generators (not just clock-triggered)~~ ✓ Started (pitch_target system)
- MIDI channel assign per generator
- Central MIDI config (JSON, not visible in UI)

---

## New Generators

- ~~Granular sampler~~ ✓ Done (granular.scd)
- ~~FM noise~~ ✓ Done (fm.scd)
- ~~Physical modeling (resonant body)~~ ✓ Done (modal.scd)
- Sample-based (load audio files)
- ~~Karplus-Strong variations~~ ✓ Done (karplus_strong.scd)
- Tracking oscillator / sub osc (follows pitch, outputs square sub)

---

## Modulator System

- **Routing:** how do we wire modulators to targets? (dropdown? matrix? config file?)
- Chaos (Triple Sloths style)
- More LFO shapes
- Clockable envelope generator (ADSR triggered by clock division)

---

## Mixer System (swappable modules)

- **Output Mixer** - basic levels, pan, mute/solo
- **Channel Strip Mixer** - Mackie style with EQ per channel
- **Matrix Mixer** - feedback routing between generators

---

## Effects

- Tape Delay (clock synced)
- Spring Reverb
- Digital Reverb
- Stereo 90s Chorus/Flanger
- Saturation
- Global Filter
- Compressor/Limiter

---

## System

### Slider Resolution
How many steps between min/max. 1000 = adequate for most. 10000 = smoother sweeps, better for filter/pitch. Tradeoff: more CPU for finer resolution.

### Preset System
Save/load patches as JSON.

### MIDI Learn
Approach: "learn mode" button, click any control, move CC, mapping saved to JSON. Load mappings on startup. MIDIMix has 24 knobs + 9 faders = plenty.

### Project Template
A starter repo/folder structure we can clone for new projects. Contains: config/, theme.py, widgets.py, empty component stubs. Based on BLUEPRINT.md methodology.

---

## Visual Feedback

- Oscilloscope (switchable source)
- Waveform display per generator
- LFO visualisation
- Level meters on mixer
- Clock pulse indicator

---

## Skins

- Winamp
- ReBirth
- Windows 3.1
- Blade Runner
- Tron (Flynn's Arcade)
- Doom
- Terminator 1
- Terminator 2
- Golden Axe

---

## Open Questions

### Modulation routing UI
Three options:
1. Dropdown per modulator ("LFO1 → Filter Cutoff")
2. Matrix grid (sources down, destinations across)
3. Config file only (no UI, edit JSON)

### Mixer swapping
Tab system? Or separate "mixer type" in config?

### MIDI config
One global JSON or per-preset?

---
