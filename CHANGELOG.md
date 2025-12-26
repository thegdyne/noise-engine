# Changelog

All notable changes to Noise Engine will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [R1] - 2025-12-26

### Added

**Synthesis**
- 8 independent generator slots with shared post-processing chain
- 30 synthesis methods across 5 families (subtractive, FM, additive, noise, spectral)
- Custom parameters (P1-P5) per generator with contextual labels and tooltips
- Transpose control (±2 octaves) per slot
- Portamento with 3 modes (OFF / SHORT / LONG)
- 6 filter modes: LP (24dB), HP, BP, Notch, LP2 (12dB), OFF (bypass)
- Envelope with attack/decay and clock-synced triggering
- 13 clock divisions from 1/32 to 8 bars

**Modulation**
- 4 modulator slots with quadrature output (A/B/C/D per slot)
- LFO with 4 waveforms (SIN/SAW/SQR/S&H) and 6 phase presets
- Sloth chaos generator with 3 modes (Torpor/Apathy/Inertia)
- Full mod matrix with amount/offset control per routing
- NORM/INV polarity per modulator output

**Mixer**
- 8 channel strips: fader, pan, 3-band EQ, mute/solo, gain staging
- Lo/Hi cut filters per channel
- Echo and Reverb send controls per channel
- Master section with fader, 3-band EQ, compressor, limiter

**Effects**
- Echo (tape-style delay with feedback and tone control)
- Reverb (room/hall with size and damping)
- FX state synchronisation on reconnect

**Presets**
- Save/Load presets (CMD+S / CMD+O)
- Full state persistence: generators, mixer, mod routing, FX
- Unsaved changes indicator (● in title bar)
- Init preset for fresh start (CMD+N)

**Packs**
- Pack system with manifest-based discovery
- Core generator pack included
- 19 CQD_Forge sound packs:
  - Arctic Henge, Astro Command, Barbican Hound
  - Beacon Vigil, Block Walk, Boneyard
  - Dew Sphere, Drangarnir, Emerald Canopy
  - Fuego Celeste, Icarus, Leviathan
  - Maratus, Moss Root, Nerve Glow
  - Rakshasa, Seagrass Bay, Summer of Love
  - Wax Print

**Imaginarium**
- Deterministic image-to-sound pack generation
- Spatial analysis with tile-based feature extraction
- Role-based candidate selection (accent/foreground/motion/bed)
- Quality gating and diversity selection
- Reproducible output via seed control

**Performance**
- MIDI input with per-slot channel assignment
- Trigger modes: OFF / CLK (clock-synced) / MIDI
- Keyboard mode for computer keyboard input (CMD+K)
- BPM control (20-300) with tap tempo

**Interface**
- Eurorack-inspired dark theme
- Real-time level meters and mod scopes
- Keyboard shortcuts for common actions
- SuperCollider connection status indicator

### Documentation
- User manual with filter mode reference
- Windows installation guide
- Architecture and generator authoring docs

---

## [Unreleased]

### Planned
- macOS installation guide
- Linux installation guide
- README updates for R1

---

*For feature requests and bug reports, see [IDEAS.md](docs/IDEAS.md) and [GitHub Issues](https://github.com/your-repo/noise-engine/issues).*
