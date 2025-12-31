# Noise Engine – macOS Guide

> Tested on macOS Sonoma / Ventura (12+)

---

## Installation

### 1. SuperCollider

**Option A: Homebrew**
```bash
brew install --cask supercollider
```

**Option B: Direct Download**
https://supercollider.github.io/downloads
Download the `.dmg`, drag to Applications.

### 2. Python 3.11+

**Option A: Homebrew**
```bash
brew install python@3.11
```

**Option B: Direct Download**
https://www.python.org/downloads/
Tick "Add Python to PATH" during install.

### 3. Noise Engine

**Option A: Git clone**
```bash
git clone https://github.com/thegdyne/noise-engine.git
cd noise-engine
```

**Option B: ZIP download**
https://github.com/thegdyne/noise-engine
Green "Code" button → Download ZIP → Extract to Desktop

### 4. Python Environment

```bash
cd ~/Desktop/noise-engine-main   # or wherever you extracted
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If requirements.txt fails, install manually:
```bash
python3 -m pip install PyQt5 python-osc python-rtmidi pyyaml numpy Pillow scipy librosa
```

### 5. Install Presets

```bash
python3 tools/forge_gen_preset.py --all --install
```

This copies presets to `~/noise-engine-presets/`

> ⚠️ **Type `--all --install` manually!** Chat apps convert `--` to `—` which breaks the command.

---

## Running

### Step 1: Start SuperCollider

1. Open SuperCollider
2. File → Open → `noise-engine/supercollider/init.scd`
3. Cmd+A (select all)
4. Cmd+Enter (run)
5. Wait for "Noise Engine ready!" in console

### Step 2: Start the GUI

```bash
cd ~/Desktop/noise-engine-main
source venv/bin/activate
python3 src/main.py
```

### Step 3: Connect

Click "Connect to SuperCollider" (top right). Green = connected.

### Step 4: Load a Preset

Click Load → select a preset (try `harga` to start).
**Turn up Master Volume carefully** — all 8 generators may be active!

---

## Panic Controls

If it gets too loud:

1. **Mute buttons** on channel strips
2. **Master Volume** fader → drag down
3. In SuperCollider: type `s.freeAll;` then Cmd+Enter
4. Quit SuperCollider entirely

---

## Generator Controls

Each of the 8 slots has:

**Top row** — Custom parameters (unique per generator)

**Bottom sliders:**
- FREQ — Base frequency
- CUTOFF — Filter cutoff
- RES — Filter resonance
- ATK — Envelope attack
- DEC — Envelope decay

**Buttons:**
- Filter type (top right) — cycles LP/HP/BP etc.
- ENV/CLK (2nd button) — switch envelope mode

**Clock mode:**
Hold CLK button + drag up (multiply) or down (divide) for rhythmic textures.

---

## Mixer

Each generator has a channel strip: Volume, Pan, EQ, Mute/Solo

**Master section:**
- Master EQ
- Limiter
- Master Volume with pre/post meters

---

## Modulation

| Shortcut | Opens |
|----------|-------|
| Cmd+M | Modulation Matrix |
| Cmd+X | Cross Matrix |

**Using the matrix:**
- Arrow keys to navigate
- Number keys 1-0 to set amount
- Left column shows mod sources

**Modulators:**
- 2× LFOs (quadrature — 4 phase-shifted outputs each)
- 2× Sloths (slow chaotic sources)

---

## MIDI

Click MIDI button to connect. Sets all generators to MIDI mode (monophonic).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `python` not found | Use `python3` instead |
| Missing module | `python3 -m pip install ModuleName` |
| "Unrecognized arguments —all" | Type flags manually, don't copy-paste |
| No presets | Re-run with both flags: `--all --install` |
| sclang not found | `export PATH="/Applications/SuperCollider.app/Contents/MacOS:$PATH"` |
| SC blocked by Gatekeeper | `xattr -cr /Applications/SuperCollider.app` |
| No sound | Check System Settings → Sound output |
| PyQt5 import error | `pip install PyQt5` in your venv |

---

## Quick Reference

```bash
# Full Homebrew setup
brew install --cask supercollider && brew install python@3.11

# Run Noise Engine
cd noise-engine
source venv/bin/activate
python3 src/main.py
```

| Action | How |
|--------|-----|
| Load preset | Load button → select file |
| Change filter | Top-right button on generator |
| Clock sync | Switch to CLK mode |
| Adjust clock rate | Hold CLK + drag |
| Mod matrix | Cmd+M |
| Cross matrix | Cmd+X |
| Set mod amount | Arrow keys + 1-0 |

---

*Last updated: 2025-01-01*
