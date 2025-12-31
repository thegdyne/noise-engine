# Noise Engine Quick Start Guide

A beginner-friendly guide to getting started with Noise Engine.

---

## 1. Installing the Preset Library

Run this command from your Noise Engine directory:

```bash
cd ~/repos/noise-engine  # or wherever you cloned it
python tools/forge_gen_preset.py --all --install
```

This copies the preset library to `~/noise-engine-presets/`.

---

## 2. Loading Your First Preset

1. Use the **Load** button in the application
2. Navigate to your presets folder
3. Select a preset file
4. ⚠️ **Turn up the master volume carefully** — all 8 generators may be active!

---

## 3. Generator Controls

Each of the 8 generator slots has:

### Top Section
- **Custom Parameters** — unique to each generator type (the top row of controls)

### Bottom Sliders
| Slider | Function |
|--------|----------|
| FREQ | Base frequency |
| CUTOFF | Filter cutoff frequency |
| RES | Filter resonance |
| ATK | Envelope attack time |
| DEC | Envelope decay time |

### Buttons
- **Filter Type** (top right) — cycles through available filter modes
- **ENV Mode** (second button down) — click to switch to **CLK** mode for clock-synced envelopes

### Clock Multiplier/Divider
When in CLK mode:
- **Press and hold** the CLK button
- **Drag up** → multiplier (faster)
- **Drag down** → divider (slower)

This is a fun way to create rhythmic textures with each generator!

---

## 4. Filter Button

The button on the **top right** of each generator cycles through filter types:
- Low Pass
- High Pass  
- Band Pass
- (and more)

---

## 5. MIDI Control

- Click the **MIDI button** to connect/disconnect
- This sets all generators to MIDI mode
- Currently **monophonic** (one note at a time per generator)

---

## 6. Mixer Section

Each generator has its own **channel strip** with:
- Volume fader
- Pan control
- Mute/Solo

### Master Section
- **Master EQ** at the bottom
- **Limiter** on the right
- **Master Volume** fader with pre/post metering

---

## 7. Modulation Matrix

### Opening the Matrices
| Shortcut | Matrix |
|----------|--------|
| **⌘+M** | Modulation Matrix |
| **⌘+X** | Cross Matrix |

### Using the Mod Matrix
- **Arrow keys** — navigate the matrix grid
- **Number keys 1-0** — set modulation amount
- **Left column** — access to modulators

### Available Modulators
| Type | Description |
|------|-------------|
| **2× LFOs** | Quadrature output (each waveform phase-shifted) |
| **2× Sloths** | Slow, chaotic modulation sources |

Each modulator provides **4 outputs**, giving you extensive modulation possibilities.

---

## 8. Design Philosophy

Noise Engine was designed around the **Arturia MatrixBrute** concept:
- All controls visible — no menu diving
- Hardware synth feel
- Vertical faders throughout
- Matrix-based modulation routing

---

## 9. Troubleshooting

If you run into issues:
- Make sure SuperCollider is installed and running
- Check that audio output is configured correctly
- Start with master volume **low** and bring up gradually
- Verify the preset path is correct

---

## Quick Reference Card

| Action | How |
|--------|-----|
| Load preset | Load button → navigate to preset |
| Change filter | Top-right button on generator |
| Clock sync envelope | Switch to CLK mode |
| Adjust clock rate | Hold CLK button + drag |
| Open mod matrix | ⌘+M |
| Open cross matrix | ⌘+X |
| Set mod amount | Arrow keys + 1-0 |
| MIDI mode | MIDI connect button |

---

*Happy droning!* 🎛️
