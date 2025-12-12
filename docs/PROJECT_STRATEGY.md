# Noise Engine - Project Strategy

**Last Updated:** December 11, 2025

---

## Project Vision

A modular, physics-based noise instrument with hybrid audio/CV output capabilities for expressive real-time performance and composition.

---

## Core Architectural Principles

### 1. Component-Based Modular Design ✓

**Principle:** Each UI section = self-contained component

- Components are independent, self-contained modules
- Can be moved/resized/hidden without breaking functionality
- Like Eurorack: modules can be rearranged in the rack
- Clean separation of concerns

**Benefits:**
- Easy to test components individually
- Future layout customization
- Add/remove features without breaking system
- Clean, maintainable code

---

### 2. Frame + Center Layout ✓
```
┌─────────────────────────────────────┐
│ TOP: Presets/Connect/Settings      │
├──────┬───────────────────┬──────────┤
│ LEFT │     CENTER        │  RIGHT   │
│ MOD  │   GENERATORS      │  MIXER   │
│ 25%  │      60%          │   15%    │
├──────┴───────────────────┴──────────┤
│ BOTTOM: Sequencer (15%)            │
└─────────────────────────────────────┘
```

**Frame Sections:**
- **TOP:** Meta controls (presets, connection, settings)
- **LEFT:** Modulation parameters (physics metaphors)
- **CENTER:** Generator grid (the instruments)
- **RIGHT:** Mixer (per-generator volume, I/O status)
- **BOTTOM:** Sequencer (time-based control)

---

### 3. Everything Visible - No Menu Diving ✓

**Principle:** All controls visible on one screen

- Like a hardware synthesizer panel
- What you see is what you control
- Spatial memory - learn the geography
- Direct manipulation

**NOT:**
- No tabs
- No hidden menus
- No modal dialogs (except file choosers)
- No drilling down for basic functions

---

### 4. Vertical Orientation ✓

**Principle:** Vertical faders/sliders everywhere (except sequencer)

- **Modulation panel:** Vertical sliders
- **Mixer panel:** Vertical faders
- **Exception:** Sequencer uses horizontal timeline

**Benefits:**
- Consistent interaction model
- Natural for mixing metaphor
- Feels like hardware (mixers, modular panels)
- Better use of vertical screen space

---

### 5. Config-Based Routing ✓

**Principle:** Routing defined in configuration files, not UI

**Routing Config Example:**
```yaml
modulation:
  gravity:
    targets: [gen1, gen2]
  density:
    targets: all

generators:
  gen1:
    mixer_channel: 1
    audio_output: true
    midi_output: true
```

**Benefits:**
- Clean UI (no routing clutter)
- Flexible setups
- Version controllable
- Shareable presets
- Can be modified by sequencer

**Sequencer Routing Control:**
- Sequencer can trigger routing changes
- Load routing snapshots mid-pattern
- Enables evolving patches and compositional structure

---

## Current Status

### ✅ Complete

**Core Architecture:**
- Python GUI with PyQt5
- SuperCollider audio engine with OSC bridge
- Modular frame layout (left/center/right/bottom)
- Git repository: https://github.com/thegdyne/noise-engine

**Generator System (20 generators):**
- 8-slot generator grid with per-generator parameters
- Standard params: FRQ, CUT, RES, ATK, DEC + filter type (LP/HP/BP)
- Custom params: up to 5 per generator via JSON config
- pitch_target system: per-generator MIDI note routing
- Clock sync with 8 rate divisions
- Auto-loading SynthDefs from generators/ directory

**Generator Types:**
- Synthesis: Subtractive, Additive, Granular, FM, Wavetable, Karplus-Strong, Modal
- Relaxation: VCO Relax, CapSense, UJT Relax, Neon
- Sirens: 4060 Siren, FBI Siren
- Ring Mods: Diode Ring, 4-Quad Ring, VCA Ring
- Other: PT2399 Grainy, Geiger, Giant B0N0, Test Synth

**Effects:**
- Master bus architecture (generators → bus → effects → output)
- Effects chain with 4 slots
- Fidelity effect (bit crush, sample rate, bandwidth)

**Mixer:**
- Per-generator volume faders
- Mute/solo buttons
- Master fader

### 🔨 In Progress

- Testing and refining generator SynthDefs
- MIDI input preparation (pitch_target routing ready)

### ⏳ Future Phases

**Phase 3:** MIDI input (Akai MIDIMix CC mapping)
**Phase 4:** MIDI note → generator pitch routing
**Phase 5:** MIDI output (CV.OCD → Eurorack)
**Phase 6:** More effects (reverb, delay, etc.)
**Phase 7:** Sequencer
**Phase 8:** Visual layer (particles, physics-based graphics)

---

## Technical Stack

### Languages & Frameworks
- **Python 3.9+:** Control layer, GUI, MIDI, OSC
- **PyQt5:** GUI framework (vertical sliders, modular panels)
- **SuperCollider 3.14+:** Audio synthesis engine
- **OSC:** Communication protocol (Python ↔ SuperCollider)

### Configuration
- **YAML/JSON:** Routing, presets, parameter definitions
- **Git:** Version control

### Hardware Integration
- **Akai MIDIMix:** Physical control surface (future)
- **CV.OCD (Sixty Four Pixels):** MIDI → CV converter for Eurorack (future)
- **MOTU M6:** Audio interface (6 in, 6 out)

---

## Generator System

### Generator Types (Planned)

**1. Synthesis Generators:**
- PT2399 Grainy (tape delay degradation)
- Filtered Noise
- Click/Pop Generator (Geiger-like)
- Bat Detector (high-frequency chirps)
- Sonar (pings, sweeps)

**2. Sample-Based Generators:**
- Sampler (folder-based, multiple modes)
  - One-shot
  - Loop
  - Granular
  - Scrub

**3. Hybrid Generators:**
- Sample + synthesis processing
- Multiple signal paths

### Generator Capabilities

**Each generator can output:**
1. **Audio:** Internal sound generation → audio interface
2. **MIDI:** Control signals → CV.OCD → Eurorack
3. **Both:** Simultaneous audio + MIDI output

**Each generator slot has:**
- Type selector (PT2399, Sampler, etc.)
- Audio on/off toggle
- MIDI on/off toggle
- MIDI channel assignment
- Activity indicator
- Mixer routing

---

## Modulation System

### Physics-Based Parameters (Planned)

**Forces:**
- Gravity (pull/weight)
- Buoyancy (lift/float)
- Water Displacement (viscosity/resistance)
- Tide Pull (cyclic modulation)
- Ice Friction (attack/smoothness)
- Surface Tension (resonance/snap)
- Rotational Frequency (spin/acceleration)
- Crystallization (structure/harmonics)

**Texture:**
- PT2399 Degradation (tape/bit crushing)
- Feedback (regeneration)
- Filter Cutoff
- Filter Resonance
- Grain Size
- Grain Spray/Randomness
- Bit Crushing
- Sample Rate Reduction

**Spatial:**
- X Position (left-right)
- Y Position (up-down)
- Z Depth (near-far)
- Reverb Size
- Reverb Decay
- Spatial Width
- Doppler Amount
- Distance Attenuation

### Parameter Routing

**Global by default:**
- Modulation parameters affect all active generators
- Config can specify selective routing
- Sequencer can change routing over time

---

## Mixer System

### Per-Generator Controls
- Volume fader (vertical)
- Mute button
- Solo button
- Pan control (future)
- Send effects (future)

### Master Section
- Master fader
- Master mute
- Output level meter
- CPU usage indicator

### I/O Status Display
- Audio output: ON/OFF
- MIDI output: ON/OFF
- CV.OCD connection: ON/OFF

---

## Sequencer System (Future)

### Capabilities
- Multiple horizontal lanes
- Time-based pattern programming
- Variable step resolution

### What Can Be Sequenced
1. **Generator Triggers:** Start/stop generators
2. **Parameter Modulation:** Automate modulation values
3. **MIDI Output:** Send notes/CC to external gear
4. **Routing Changes:** Load routing snapshots
5. **Preset Recall:** Trigger preset changes

### Input Methods (Planned)
- Draw with mouse
- Record from MIDI input
- Algorithmic/generative patterns
- Copy/paste/transform patterns

---

## MIDI System (Future)

### MIDI Input (Akai MIDIMix)
- 24 knobs (3 rows × 8)
- 8 channel faders
- 1 master fader
- Mute/Solo/Record-Arm buttons per channel
- Bank Left/Right buttons

### MIDI Output (CV.OCD)
- Convert MIDI → CV for Eurorack control
- Multiple output channels
- Note data (1V/octave pitch CV)
- CC data (modulation sources)
- Trigger/gate signals
- Clock/sync

---

## Visual System (Future)

### Synesthetic Graphics
- Real-time particle systems
- Physics-based animations
- Visual metaphors (crystals, water, stars, webs)
- Responds to same parameters as audio
- Tight audio ↔ visual coupling

### Aesthetic References
- Crystals in water
- Melting ice
- Spider webs with dew
- Charcoal in sand
- Stars in the milky way
- Water displacement/ripples

---

## Development Guidelines

### Code Style
1. **Components are self-contained:** Each panel/module is independent
2. **Config over code:** Routing and presets in config files
3. **OSC for communication:** Clean separation between Python and SuperCollider
4. **Test incrementally:** Build small pieces, test, integrate
5. **Git workflow:** Commit often, meaningful messages
6. **Use `cat > EOF`:** For all code snippets in documentation

### Claude Workflow

When Claude provides code fixes, the download should be named `noise-engine-updated.zip`. Save it to `~/Downloads/` then run:

```bash
cd ~/repos/noise-engine
~/repos/noise-engine/tools/update_from_claude.sh
git add -A
git commit -m "Brief description of what was fixed"
git push
```

**Commit message style:**
- Start with component name if specific: `Additive: fix envelope triggering`
- Or describe the fix: `All generators: add MIDI trigger support`
- Keep it brief but descriptive

### File Structure
```
noise-engine/
├── src/
│   ├── gui/              # PyQt5 components
│   │   ├── modulation_panel.py
│   │   ├── mixer_panel.py
│   │   ├── generator_grid.py
│   │   ├── sequencer_panel.py
│   │   └── main_frame.py
│   ├── audio/            # OSC bridge
│   ├── midi/             # MIDI I/O
│   └── config/           # Config loaders
├── supercollider/
│   ├── init.scd
│   └── generators/       # Generator SynthDefs
├── config/
│   ├── parameters.yaml
│   ├── routing.yaml
│   └── presets/
├── docs/
│   ├── PROJECT_STRATEGY.md  (this file)
│   └── architecture.md
└── presets/              # User presets
```

---

## Design Mantras

1. **"Like Eurorack"** - Modular, patchable, flexible
2. **"Everything visible"** - No menu diving
3. **"Vertical only"** - Consistent interaction (except sequencer)
4. **"Config-based routing"** - Clean UI, maximum flexibility
5. **"Components as modules"** - Self-contained, reusable, testable

---

## Success Criteria

### Phase 1 Complete When:
- [ ] Frame layout displays correctly
- [ ] Mixer panel controls test generator volume
- [ ] Test generator sits in first slot
- [ ] All components are modular/movable
- [ ] Audio routing works through mixer

### Project Complete When:
- [ ] Multiple generator types working
- [ ] Full modulation system operational
- [ ] Sequencer functional with routing control
- [ ] MIDI input from MIDImix
- [ ] MIDI output to CV.OCD
- [ ] Visual layer integrated
- [ ] Preset system robust
- [ ] Expressive and performable

---

## Notes

- Keep this document updated as decisions are made
- Reference this when questions arise about direction
- Use as onboarding for future contributors
- Reflects current consensus, not set in stone
- Update "Last Updated" date when modified

---

**This is our north star. When in doubt, return to these principles.**

---

## Known Technical Issues & Solutions

### PyQt5 Slider Ghosting on macOS

**Problem:** QSlider widgets show visual artifacts/ghosting when dragged on macOS.

**Solution:** Apply custom stylesheet + repaint on release
```python
# Custom stylesheet for sliders
slider.setStyleSheet("""
    QSlider::groove:vertical {
        border: 1px solid #999999;
        width: 10px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
            stop:0 #B1B1B1, stop:1 #c4c4c4);
        margin: 0 2px;
        border-radius: 5px;
    }
    QSlider::handle:vertical {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
            stop:0 #d4d4d4, stop:1 #8f8f8f);
        border: 1px solid #5c5c5c;
        height: 20px;
        margin: 0 -5px;
        border-radius: 10px;
    }
    QSlider::handle:vertical:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, 
            stop:0 #f4f4f4, stop:1 #afafaf);
    }
""")

# Force repaint on release
slider.sliderReleased.connect(lambda s=slider: s.repaint())
```

**When to apply:** Every QSlider in every component.

**Window-level fix:**
```python
# In main window __init__
self.setAttribute(Qt.WA_AcceptTouchEvents, False)
```


---

## Phase Updates

### Phase 1: COMPLETE ✓ (2025-12-10)
- Frame architecture built and working
- All components integrated (modulation, generators, mixer, effects)
- Responsive layout
- OSC connection functional
- Test generator and PT2399 working
- Generator cycling (click to switch types)

### Phase 2: Effects Chain - COMPLETE ✓ (2025-12-10)
- Built effects chain with 4 slots (bottom section)
- Master bus routing architecture implemented
- Fidelity effect working (bit crushing, sample rate reduction, bandwidth limiting)
- Always-on passthrough system (audio flows even without effects)
- Effect amount controls work in real-time

**Architecture Decision:**
```
Generators → Master Bus (internal) → [Effects Chain] → Output (speakers)
```
- Generators write to internal stereo bus (~masterBus)
- Master passthrough synth reads from bus, applies effects, outputs to speakers
- Always-on passthrough at 100% = transparent (no degradation)
- Effect slots modulate the passthrough parameters

### Phase 2.5: Generator System - COMPLETE ✓ (2025-12-11)
- 20 generators with JSON configs and SynthDefs
- Per-generator custom parameters (up to 5 per generator)
- pitch_target system for MIDI note routing
- LP/HP/BP filter support via shared ~multiFilter helper
- Auto-loader for SynthDefs from generators/ directory
- MIT License added, source attributions documented

---

## Code Principles

### DRY (Don't Repeat Yourself)
- Use helper functions for repeated operations
- Standard interfaces for similar components
- Single point of change for shared behavior

### Standard Generator Interface
All generators in SuperCollider receive the same parameter buses:
- FRQ, CUT, RES, ATK, DEC, FilterType
- Each generator interprets these appropriately for its sound
- Adding new generators = implement interface, don't repeat wiring
