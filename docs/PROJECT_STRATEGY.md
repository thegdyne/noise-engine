# Noise Engine - Project Strategy

**Last Updated:** December 10, 2024

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

### ✅ Working (Iteration 1-2 Complete)

- Python GUI with PyQt5
- 4 vertical sliders (Gravity, Density, Filter Cutoff, Amplitude)
- SuperCollider test synth (pulsing filtered noise)
- OSC bridge (Python → SuperCollider)
- Real-time parameter control
- Expanded parameter ranges
- Git repository established: https://github.com/thegdyne/noise-engine

### 🔨 Next (Phase 1 - In Progress)

**Build the Frame:**
1. Create modular frame layout (left/center/right/bottom/top)
2. Build mixer panel component (right frame)
3. Place current test generator into first slot
4. Verify frame + mixer + generator integration

### ⏳ Future Phases

**Phase 2:** Expand modulation panel, add more parameters
**Phase 3:** Add more generator types (PT2399, Sampler, Clicks, etc.)
**Phase 4:** Build sequencer functionality
**Phase 5:** Add MIDI input (Akai MIDIMix)
**Phase 6:** Add MIDI output (CV.OCD → Eurorack)
**Phase 7:** Visual layer (particles, physics-based graphics)

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
