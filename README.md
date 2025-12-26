# Noise Engine

**8-slot modular texture synthesizer — Python + SuperCollider**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![SuperCollider 3.13+](https://img.shields.io/badge/SuperCollider-3.13+-red.svg)](https://supercollider.github.io/)

![Noise Engine Screenshot](docs/screenshot.png)

---

## What is Noise Engine?

Noise Engine is a performance-oriented drone and ambient synthesizer combining:

- **8 independent generator slots** with 30 synthesis methods
- **Quadrature modulation system** with LFO and chaos sources
- **SSL-inspired mixer** with per-channel EQ, sends, and master processing
- **19 curated sound packs** generated via the Imaginarium image-to-sound pipeline

Built for **texture, atmosphere, and evolving soundscapes** — not a general-purpose polysynth.

---

## Features

### Synthesis
- 30 generators across 5 families (subtractive, FM, additive, noise, spectral)
- Custom parameters (P1-P5) per generator with contextual labels
- Transpose (±2 octaves) and portamento per slot
- 6 filter modes: LP (24dB), HP, BP, Notch, LP2 (12dB), OFF
- Clock-synced envelopes with 13 divisions (1/32 to 8 bars)

### Modulation
- 4 mod slots with quadrature output (A/B/C/D)
- LFO: SIN/SAW/SQR/S&H with 6 phase presets
- Sloth chaos: Torpor/Apathy/Inertia modes
- Full mod matrix with amount/offset per routing

### Mixer
- 8 channel strips: fader, pan, 3-band EQ, mute/solo
- Echo and Reverb sends per channel
- Master section: EQ, compressor, limiter

### Performance
- MIDI input with per-slot channel assignment
- Trigger modes: OFF / CLK / MIDI
- Keyboard mode (CMD+K) for computer input
- BPM control (20-300) with tap tempo

### Presets & Packs
- Save/load full state (CMD+S / CMD+O)
- 19 CQD_Forge sound packs included
- Pack system for organizing generators

---

## Installation

### Requirements

| Component | Version |
|-----------|---------|
| Python | 3.11+ |
| SuperCollider | 3.13+ (3.14 recommended) |

### Quick Start (Fedora/Linux)

```bash
# Install dependencies
sudo dnf install supercollider supercollider-sc3-plugins python3-pip python3-virtualenv

# Clone and setup
git clone https://github.com/thegdyne/noise-engine.git
cd noise-engine
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python main.py
```

### Platform Guides

- **[Linux Installation](docs/LINUX_INSTALL.md)** — Fedora (tested), Ubuntu, Arch
- **[Windows Installation](docs/WINDOWS_INSTALL.md)** — Windows 10/11
- **macOS** — Coming soon

---

## Usage

### Basic Workflow

1. **Select a pack** from the dropdown (or use Core)
2. **Load generators** by clicking slot dropdowns
3. **Set trigger mode** — CLK for clock-synced, MIDI for external control
4. **Shape sound** with FRQ, CUT, RES, ATK, DEC and P1-P5
5. **Add modulation** — route LFO/Sloth to any parameter
6. **Mix** — balance levels, add echo/reverb
7. **Save** your preset (CMD+S)

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| CMD+S | Save preset |
| CMD+O | Open preset |
| CMD+N | Init (new) preset |
| CMD+K | Toggle keyboard mode |
| CMD+M | Open mod matrix |
| Space | Tap tempo |

---

## Sound Packs

19 CQD_Forge packs included, each with 8 generators designed around a visual theme:

| Pack | Character |
|------|-----------|
| Arctic Henge | Frozen, crystalline textures |
| Astro Command | Retro sci-fi bleeps and drones |
| Barbican Hound | Brutalist, concrete atmospheres |
| Beacon Vigil | Lighthouse signals, coastal fog |
| Boneyard | Skeletal, decayed resonances |
| Drangarnir | Nordic sea stacks, wind and waves |
| Emerald Canopy | Rainforest, organic layers |
| Fuego Celeste | Volcanic, smoldering heat |
| Icarus | Solar winds, melting wax |
| Leviathan | Deep ocean, pressure and darkness |
| Maratus | Peacock spider, iridescent chirps |
| Moss Root | Forest floor, fungal networks |
| Nerve Glow | Bioluminescent, neural pulses |
| Rakshasa | Mythological, shape-shifting |
| Seagrass Bay | Underwater meadows, gentle currents |
| Summer of Love | Psychedelic warmth, vintage haze |
| Wax Print | African textiles, rhythmic patterns |
| + 2 more | ... |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Python GUI                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Gen 1-8 │ │ Mod 1-4 │ │  Mixer  │ │ Master  │           │
│  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │
└───────┼───────────┼───────────┼───────────┼─────────────────┘
        │    OSC    │           │           │
        ▼           ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────┐
│                     SuperCollider                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │SynthDefs│ │ Mod Bus │ │ Ch Strip│ │ Master  │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Project Structure

```
noise-engine/
├── src/
│   ├── gui/           # PyQt5 interface
│   ├── presets/       # Preset management
│   └── imaginarium/   # Image-to-sound pipeline
├── supercollider/
│   ├── core/          # Engine setup, buses, helpers
│   ├── generators/    # SynthDef implementations
│   └── effects/       # FX processors
├── packs/             # Sound packs (core + CQD_Forge)
├── docs/              # Documentation
└── tools/             # Validation and build scripts
```

### Creating Generators

See [Generator Authoring Guide](docs/GENERATOR_SPEC.md) for the SynthDef contract and JSON config format.

---

## License

MIT License — see [LICENSE](LICENSE)

---

## Links

- **Documentation:** [docs/](docs/)
- **Changelog:** [CHANGELOG.md](CHANGELOG.md)
- **Ideas & Roadmap:** [docs/IDEAS.md](docs/IDEAS.md)

---

*Built with Python, PyQt5, and SuperCollider*
