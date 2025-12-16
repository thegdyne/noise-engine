# Future Ideas

Captured ideas for potential future development.

---

## Routing & Control

- **LFO Modulation Routing** - turn on/off at target
- **Modulation routing system** - how to wire source → destination?

---

## External Audio Input

**Concept:** Route external audio (drum machines, synths, Eurorack) through the Noise Engine master section for processing and mixing.

**Use cases:**
- Drum machine through master compressor/EQ/limiter
- Eurorack through master effects chain
- Mix external gear with Noise Engine generators
- Use Noise Engine as a submixer with processing

**Implementation approach:**

### Option A: Dedicated Input Channels
Add 1-2 stereo input channel strips to the mixer:
```
┌─────────────────────────────────────────┐
│  1  2  3  4  5  6  7  8  │ IN1  IN2    │
│  ░  ░  ░  ░  ░  ░  ░  ░  │  ░    ░     │  ← Generators + External inputs
│  M  M  M  M  M  M  M  M  │  M    M     │
│  S  S  S  S  S  S  S  S  │  S    S     │
└─────────────────────────────────────────┘
```

### Option B: Generator Slot as Input
Special "External In" generator type selectable in any slot:
- Select input pair (1-2, 3-4, etc.) from dropdown
- Standard channel strip controls (vol, pan, mute, solo)
- Can use multiple slots for multiple inputs
- Appears in generator dropdown like any other generator

### Option C: Sidechain-Only Input
External audio only available as sidechain source for compressor:
- Simpler implementation
- Limited use case but solves "duck to kick drum" need

**Recommended: Option B** - Most flexible, fits existing architecture.

**UI for Option B:**
```
┌─────────────────────────────────────┐
│ [External In ▼]           GEN 5    │
│                                     │
│  INPUT: [1-2 ▼]    GAIN: [====●==] │
│                                     │
│  🔊 Signal Present                  │
└─────────────────────────────────────┘
```

**SuperCollider requirements:**
```supercollider
// External input generator
SynthDef(\external_in, {
    arg out=0, inBus=0, gain=1.0, gate=1;
    var sig = SoundIn.ar([inBus, inBus+1]);
    sig = sig * gain;
    Out.ar(out, sig);
}).add;
```

**Config (external_in.json):**
```json
{
    "name": "External In",
    "category": "input",
    "synthdef": "external_in",
    "custom_params": [
        {"id": "input_pair", "label": "INPUT", "type": "dropdown", 
         "options": ["1-2", "3-4", "5-6", "7-8"]},
        {"id": "gain", "label": "GAIN", "min": 0, "max": 2, "default": 1}
    ]
}
```

**Considerations:**
- Need to query available input channels from audio device
- Latency monitoring (input → output roundtrip)
- Input metering (show signal present indicator)
- DC blocking on input
- Phase invert option?

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

## Modulator System ✓ DESIGNED

**Design doc:** `docs/MOD_SOURCES.md`

4 mod source slots in left panel, each with 3 outputs (12 mod buses total). Uses same slot architecture as audio generators but stripped down for CV output.

**Initial mod generators:**
- **LFO** - TTLFO v2 style, 3 outputs with independent waveform/phase/polarity, shared RATE + SHAP
- **Sloth** - NLC Triple Sloth style chaos, X/Y/Z outputs, Torpor/Apathy/Inertia speed modes

**Per-slot scope** with auto-ranging time scale.

**Future mod generators:**
- Clockable envelope generator (ADSR triggered by clock division)
- Drift (slow smooth random)
- Step sequencer

---

## Mixer System (swappable modules)

- **Output Mixer** - basic levels, pan, mute/solo
- **Channel Strip Mixer** - Mackie style with EQ per channel
- **Matrix Mixer** - feedback routing between generators

---

## Effects

### Master Insert Chain (see `docs/MASTER_OUT.md`)
- Limiter (Phase 4)
- Compression (Phase 5)
- 3-Band EQ (Phase 6)

### FX Send Buses (see `docs/FXBUS.md`)
Architecture designed - 2 send/return buses with per-channel sends:
- Reverb (Room/Hall/Plate)
- Delay (clock synced, ping-pong)
- Chorus
- Phaser

### Additional Effects (future)
- Tape Delay (clock synced)
- Spring Reverb
- Saturation
- Global Filter

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
- ~~LFO visualisation~~ ✓ Designed (per-slot scope in MOD_SOURCES.md)
- ~~Level meters on mixer~~ ✓ Done (per-channel stereo meters)
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

## Per-Generator Theming

**Concept:** Each generator type can define its own visual theme (accent colors, label colors, etc.) in its JSON config, overriding the default `GENERATOR_THEME`.

**Current state (Dec 2025):**
- `GENERATOR_THEME` dict in `theme.py` centralises all generator slot styling
- `build_param_column()` in `generator_slot_builder.py` references theme only (no inline styles)
- Ready for per-generator overrides

**Implementation approach:**
```python
# In generator JSON config (e.g. fm.json)
{
    "name": "FM",
    "synthdef": "fm_noise",
    "theme": {
        "param_label_color": "#ff8844",      # Orange accent
        "param_label_color_active": "#ffaa66",
        "slot_border_active": "#ff6622"
    }
}

# In config/__init__.py
def get_generator_theme(name):
    """Get theme for generator, falling back to default."""
    from src.gui.theme import GENERATOR_THEME
    custom = _GENERATOR_CONFIGS.get(name, {}).get('theme', {})
    return {**GENERATOR_THEME, **custom}

# In generator_slot_builder.py
gt = get_generator_theme(slot.generator_type)
```

**Use cases:**
- Acid/303-style generators → orange/yellow accent
- FM generators → blue/cyan accent
- Noise/chaos generators → red accent
- Physical modeling → green accent

**Files involved:**
- `src/gui/theme.py` - GENERATOR_THEME base dict
- `src/config/__init__.py` - get_generator_theme() loader
- `src/gui/generator_slot_builder.py` - applies theme to UI
- `supercollider/generators/*.json` - per-generator theme overrides

---

## Modulation Routing (Dec 2025)

**Concept:** Comprehensive modulation routing with visual feedback.

### Part 1: Pin Matrix Window
Second screen with large connection matrix. Rows = mod sources (from `MOD_SOURCES.md` - 12 buses), columns = destinations (all generator params). Click intersections to connect. Each connection has its own depth (-100% to +100%) set at the target - same LFO output can modulate cutoff at +80% and resonance at -20%.

### Part 2: Modulation Visualisation  
Korg wavestate-style indicators on modulated controls. Shows:
- Static bracket for min/max modulation range
- Moving line for current modulated value in real-time

**Design docs:** 
- `docs/MOD_SOURCES.md` - Mod source slots and generators (LFO, Sloth)
- `docs/MODULATION_SYSTEM.md` - Routing matrix and visualisation

---

## UI Scaling Improvements (Dec 2025)

**Current state:**
Fader scaling system implemented with per-context min/max constraints and height-ratio sensitivity. Core architecture is solid but needs refinement.

**Outstanding issues:**

1. **Mixer/Master vertical split** - MASTER section is squashed, compressor row barely readable. Need better vertical space distribution between MIXER and MASTER sections.

2. **Generator slider row heights** - P1-P5 vs FRQ-DEC rows still slightly uneven at some window sizes. May need layout tweaks in `generator_slot_builder.py`.

3. **Fine-tune min/max constraints** - Current values in `config/__init__.py` SIZES dict may need adjustment based on real usage across different screen sizes.

**Files involved:**
- `src/gui/mixer_panel.py` - Mixer section layout
- `src/gui/master_section.py` - Master section layout  
- `src/gui/main_frame.py` - Overall panel proportions
- `src/gui/generator_slot_builder.py` - Generator slot layout
- `src/config/__init__.py` - SIZES constraints

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
See `docs/MOD_SOURCES.md` for mod source architecture and `docs/MODULATION_SYSTEM.md` for routing matrix design.

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
## Generator Lock & Power Off

**Concept:** Two controls per slot for protecting generator selection and quick power cycling.

**🔒 Lock:**
- Disables generator dropdown only
- Params, channel strip, trigger mode all still editable
- Prevents accidental generator changes while tweaking

**⏻ Power Off:**
- Stops audio, dims slot, stores full state
- Auto-locks generator dropdown
- Press again to restore exactly as it was
- Stores: generator, params, trigger mode, channel strip, previous lock state

**UI:** Both icons top right of slot, next to generator dropdown

**Storage:** Central config (SSOT) - not per-generator

**Design doc:** `docs/GENERATOR_POWER.md`
## Server Control Panel

**Concept:** Lockable panel near Connect button with "dangerous" SC controls.

**Controls:**
- 🔓/🔒 toggle to reveal/hide panel
- `s.freeAll` - panic button, stops all synths
- `s.reboot` - full server restart

**Improved connection detection:**
- Check port 57120 availability
- Scan for running `sclang`/`scsynth` processes
- Clear error messages: "SuperCollider IDE is running on port 57120. Close it and try again."

**Design doc:** `docs/SERVER_CONTROLS.md`
