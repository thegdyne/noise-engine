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

- 90s Media Player (green LCD aesthetic)
- Acid TB (orange 303 style)
- Classic GUI (grey system dialogs)
- Dystopia (dark sci-fi red glow)
- Neon Grid (cyan wireframe)
- FPS HUD (game interface)
- Cyborg (chrome and red LEDs)
- Pixel Warrior (16-bit aesthetic)

---

## In-App Console (Logging) ✓ DONE

**Implemented:** `src/utils/logger.py` + `src/gui/console_panel.py`

- Central logger with Qt signal handler for thread-safe GUI updates
- Slide-out panel from right side (toggle: button or Ctrl+`)
- Color-coded log levels: DEBUG (grey), INFO (green), WARNING (orange), ERROR (red)
- Auto-scroll with pause option
- Max 500 lines (memory limit)
- Clear and copy buttons
- Level filter dropdown

**Usage:**
```python
from src.utils.logger import logger

logger.debug("Detailed info", component="OSC")
logger.info("Normal operation", component="APP")
logger.warning("Something unexpected", component="MIDI")
logger.error("Something failed", component="GEN", details=str(e))

# Convenience methods
logger.osc("OSC message")
logger.midi("MIDI event")
logger.gen(slot_id, "Generator action")
```

---

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
## Computer Keyboard Mode (CMD+K)

**Concept:** Toggle QWERTY keyboard into a musical keyboard for playing generators.

**Activation:**
- CMD+K toggles mode on/off (ESC also exits)
- Last clicked generator slot receives input
- Auto-switches slot to MIDI trigger mode if needed (restores on exit)

**Key mapping:**
```
 W E   T Y U   O P      (black keys)
A S D F G H J K L ;     (white keys - C to C)
```
- Z/X = octave down/up

**Visual feedback:**
- Status bar shows `⌨ 3` (targeted slot number)
- Subtle glow + keyboard icon on targeted slot

**Integration:**
- Sends same OSC messages as external MIDI (`/noise/slot/X/pitch`, `/noise/slot/X/gate`)
- Can play alongside running sequencer (last message wins)

**Design doc:** `docs/KEYBOARD_MODE.md`
