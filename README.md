# Noise Engine

A modular, physics-based noise instrument with hybrid audio/CV output capabilities for expressive real-time performance and composition.

## Overview

Noise Engine is a software instrument that combines:
- **Modular generator system** - Swappable sound generators (synthesis, sampling, processing)
- **Physics-based control** - Parameters inspired by natural forces (gravity, buoyancy, friction)
- **Hybrid output** - Both audio (internal synthesis) and MIDI (external CV control)
- **Component architecture** - Flexible, reconfigurable UI like a modular synthesizer

## Key Features

- **Real-time parameter control** via any MIDI controller
- **Multiple generator types** - Synthesis, sampling, hybrid processing
- **Config-based routing** - Flexible signal patching without UI clutter
- **Sequencer with routing control** - Evolving patches and compositional structure
- **MIDI → CV output** - Control Eurorack systems via CV.OCD or similar converters
- **Everything visible** - No menu diving, hardware-inspired interface

## Architecture

### Component-Based Design

Each UI section is a self-contained, modular component:
- **Modulation Panel** (left) - Physics-based parameters
- **Generator Grid** (center) - Sound generators/processors
- **Mixer Panel** (right) - Per-generator volume and routing
- **Sequencer** (bottom) - Time-based control and automation
- **Top Bar** - Presets, connection, settings

Components can be rearranged, hidden, or modified without breaking functionality.

### Tech Stack

- **Python 3.9+** - GUI (PyQt5), MIDI I/O, OSC communication, control logic
- **SuperCollider 3.14+** - Audio synthesis and DSP
- **OSC** - Communication bridge between Python and SuperCollider
- **YAML/JSON** - Configuration, routing, and presets

## Hardware Integration

### MIDI Controllers

**Works with any MIDI controller.** The system is controller-agnostic and uses standard MIDI CC messages.

**Tested/optimized for:**
- Akai MIDIMix (24 knobs + 9 faders)
- Any controller with continuous controls (knobs/faders/sliders)

**Configuration:**
- MIDI mapping defined in config files
- Easy to adapt to your controller
- Multiple controller profiles supported

### Audio Interface

- **Tested:** MOTU M6 (6 in / 6 out)
- **Compatible:** Any CoreAudio/JACK interface

### CV Output (Optional)

- **CV.OCD** by Sixty Four Pixels - MIDI to CV converter for Eurorack
- **Or any MIDI → CV converter**
- Enables control of modular synthesizers from generators

## Setup

### Prerequisites
```bash
# macOS
brew install supercollider

# Python 3.9+ required
python3 --version
```

### Installation
```bash
# Clone repository
git clone https://github.com/thegdyne/noise-engine.git
cd noise-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Quick Start

**Terminal 1 - SuperCollider:**
```bash
# Open SuperCollider
open /Applications/SuperCollider.app

# In SuperCollider IDE:
# File → Open → supercollider/init.scd
# Execute: Cmd+A, then Cmd+Return
```

**Terminal 2 - Python GUI:**
```bash
# Activate environment
source venv/bin/activate

# Run interface
python src/main.py

# Click "Connect to SuperCollider"
# Move sliders to control sound
```

### Shell Alias (Optional)

Add to `~/.zshrc` for quick activation:
```bash
alias noise="cd ~/repos/noise-engine && source venv/bin/activate"
```

Then just type `noise` to activate project environment.

## Current Status

### ✅ Working (December 2025)

**Core System:**
- Python GUI with PyQt5
- SuperCollider audio engine via OSC
- Robust connection with ping/pong verification and heartbeat monitoring
- 8-slot generator grid

**Generators (22 total):**
- Synthesis: Subtractive, Additive, FM, Wavetable, Granular
- Physical: Karplus-Strong, Modal
- Relaxation oscillators: VCO, UJT, Neon, CapSense
- Sirens: 4060, FBI, FBI Doppler  
- Ring Modulators: Diode, 4-Quad, VCA
- Effects/Chaos: PT2399 Grainy, PT2399 Chaos, Geiger, Giant B0N0
- Test synth

**Per-Generator Features:**
- 5 standard params (FRQ, CUT, RES, ATK, DEC)
- Up to 5 custom params per generator (JSON config)
- Multimode filter (LP/HP/BP)
- Envelope source: OFF (drone), CLK (clock sync), MIDI (note trigger)
- MIDI channel assignment per slot
- Sticky slot settings (persist when changing generator type)

**MIDI:**
- MIDI input device selection
- Per-slot MIDI channel
- MIDI note triggering with velocity
- MIDI retrig for Modal/Karplus (continuous strike while key held)

**Effects:**
- 4-slot effects chain
- Fidelity effect (bit crush, sample rate, bandwidth)

### 🔨 In Progress

- Modulation sources (LFOs) - UI visible but not connected
- Per-channel mixer - UI visible but not connected
- See `docs/TECH_DEBT.md` for known issues

### ⏳ Roadmap

- Preset save/load system
- MIDI CC mapping (MIDI Learn)
- More effects (reverb, delay, chorus)
- Sequencer
- Visual layer (physics-based graphics)

See `docs/FUTURE_IDEAS.md` for full feature wishlist.

## Configuration

### Parameter Mapping

Edit `config/parameters.yaml` to customize parameter definitions.

### Routing Configuration

Edit `config/routing.yaml` to define:
- Which parameters affect which generators
- Generator → mixer assignments
- MIDI output routing
- Sequencer targets

### MIDI Controller Setup

Edit `config/midi_mapping.yaml` to map your controller:
```yaml
# Example for any controller
controller:
  name: "Your Controller Name"
  knobs:
    1: gravity
    2: buoyancy
    3: friction
    # ... map to your layout
```

## Documentation

- **[Project Strategy](docs/PROJECT_STRATEGY.md)** - Architecture, principles, roadmap
- **[Architecture](docs/architecture.md)** - Technical implementation details (coming soon)

## Generator Types

### Available (22 generators)

**Synthesis:**
- Subtractive, Additive, FM, Wavetable, Granular

**Physical Modeling:**
- Karplus-Strong (plucked string)
- Modal (struck resonant body)

**Relaxation Oscillators:**
- VCO Relax, UJT Relax, Neon, CapSense

**Sirens:**
- 4060 Siren, FBI Siren, FBI Doppler

**Ring Modulators:**
- Diode Ring, 4-Quad Ring, VCA Ring

**Effects/Chaos:**
- PT2399 Grainy (tape degradation)
- PT2399 Chaos (extreme feedback)
- Geiger (random clicks)
- Giant B0N0 (Nonlinear Circuits chaos)

### Planned

- Sample-based (load audio files)
- Phase distortion
- Formant/speech synthesis
- Tracking oscillator / sub osc

## Output Capabilities

### Audio Output

- Internal synthesis → audio interface
- Stereo or multi-channel routing
- Per-generator volume control
- Master effects chain (future)

### MIDI Output

- MIDI notes (pitch CV)
- MIDI CC (modulation sources)
- MIDI triggers (gate/trigger signals)
- MIDI clock (sync)
- → CV converters → Eurorack modular systems

### Hybrid Mode

- Generators can output audio AND MIDI simultaneously
- Sync internal sound with external modular
- Use generators as control signal sources

## Philosophy

**Like a modular synthesizer:**
- Components are independent modules
- Flexible routing and patching
- Build your own signal flow
- Experiment and evolve

**Everything visible:**
- No hidden menus
- Direct manipulation
- Hardware-inspired interface
- Spatial memory and muscle memory

**Physics-based metaphors:**
- Natural, intuitive control
- Gravity, buoyancy, friction, etc.
- Synesthetic experience
- Expressive and performable

## Contributing

This is a personal project, but ideas and feedback are welcome:
- Open issues for bugs or feature requests
- Share your routing configurations
- Submit generator ideas
- Document your workflows

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

**Created by:** Gareth Millar  
**Repository:** https://github.com/thegdyne/noise-engine

**Built with:**
- SuperCollider by James McCartney and community
- PyQt5 by Riverbank Computing
- python-osc by attwad

**Generator concepts derived from:**
- Elektor Magazine articles (relaxation oscillators, sirens, ring modulators)
- Nonlinear Circuits by Andrew F (Giant B0N0)
- See [docs/REFERENCES.md](docs/REFERENCES.md) for full source documentation

**Inspired by:**
- Modular synthesis philosophy
- Mutable Instruments (open source precedent)
- Physics-based interaction design
- Hybrid computer/modular workflows
