# Modulation System

**Status:** Concept  
**Created:** December 2025

## Overview

Two related features for modulation control and visualisation:

1. **Pin Matrix Window** - Second screen for connecting modulators to parameters
2. **Modulation Visualisation** - Korg wavestate-style indication on controls

---

## Part 1: Pin Matrix Window

### Concept

A dedicated second window showing a large connection matrix. Rows are modulation sources, columns are modulation destinations. Click intersections to create/break connections.

### Layout

```
                    │ GEN 1                      │ GEN 2                      │ ...
                    │ FRQ CUT RES ATK DEC P1-P5  │ FRQ CUT RES ATK DEC P1-P5  │
────────────────────┼────────────────────────────┼────────────────────────────┼────
LFO 1               │  ●       ○                 │      ●                     │
LFO 2               │      ○                     │  ●                         │
LFO 3               │                            │          ○   ○             │
ENV 1               │              ●             │                            │
ENV 2               │                            │                  ●         │
MIDI Velocity       │  ○                         │  ○                         │
MIDI Mod Wheel      │      ●   ●                 │      ●   ●                 │
MIDI Aftertouch     │                            │                            │
Random              │          ○                 │                            │
────────────────────┴────────────────────────────┴────────────────────────────┴────

● = Active connection (filled pin)
○ = Available but inactive (empty pin)
```

### Behaviour

- **Click empty cell** → Create connection (default depth ±50%)
- **Click filled cell** → Open depth editor or remove connection
- **Right-click** → Context menu (set depth, remove, copy to other gens)
- **Shift-click** → Quick toggle on/off without removing
- **Drag across row** → Assign same source to multiple destinations

### Depth Control at Target

**Key principle:** Modulation depth is set per-connection at the target, not globally at the source.

The same LFO can modulate:
- Gen 1 Cutoff at +80% depth (wide sweep)
- Gen 1 Resonance at -20% depth (subtle inverse)
- Gen 2 Frequency at +5% depth (gentle vibrato)

Each matrix intersection has its own depth value.

**Depth Editor (on cell click):**
```
┌─────────────────────────┐
│  LFO 1 → Gen 1 Cutoff   │
│                         │
│  Depth: [====●====] +80%│
│         -100%    +100%  │
│                         │
│  [Remove]      [Close]  │
└─────────────────────────┘
```

- Horizontal slider for depth (-100% to +100%)
- Centre = 0% (no modulation)
- Positive = modulation follows source
- Negative = modulation inverts source

**Visual indication in matrix:**
```
●   = connection exists, depth shown on hover/select
◐   = partial depth (e.g. 50%)
●●  = full depth (100%)
○   = connected but disabled
```

Or simply show depth as cell intensity/size - larger pin = deeper modulation.

### Connection Data

Each connection stores:
```python
{
    'source': 'lfo1',           # Modulation source ID
    'target': 'gen1_cutoff',    # Parameter ID
    'depth': 0.5,               # -1.0 to +1.0 (bipolar)
    'enabled': True             # Can disable without removing
}
```

### Sources (Rows)

Internal:
- LFO 1, LFO 2, LFO 3
- ENV 1, ENV 2 (if we add envelopes)
- Random / S&H
- Master Clock phase

External (MIDI):
- Velocity
- Mod Wheel (CC1)
- Aftertouch
- Expression (CC11)
- Breath (CC2)
- Custom CC assignments

### Destinations (Columns)

Per active generator:
- FRQ, CUT, RES, ATK, DEC (standard params)
- P1-P5 (custom params, labelled with actual names when loaded)

Global:
- Master Volume
- Master EQ bands
- Effect parameters

### Window Management

- Opens as separate window (not tab/panel)
- Can be moved to second monitor
- Stays on top option
- Remembers position/size
- Keyboard shortcut to toggle (Cmd+M?)

### Persistence

Matrix state saved in preset JSON:
```json
{
    "modulation": {
        "connections": [
            {"source": "lfo1", "target": "gen1_cutoff", "depth": 0.5},
            {"source": "midi_velocity", "target": "gen1_frequency", "depth": 0.3}
        ]
    }
}
```

---

## Part 2: Modulation Visualisation

### Concept

Inspired by Korg wavestate MK2 software interface. Each modulated control shows:
1. **Static range indicators** - Lines showing min/max modulation range
2. **Moving indicator** - Real-time line showing current modulated value

### Visual Design

```
Standard slider:          Modulated slider:
                         
    ┃                        ┃  ╭─ max mod range
    ┃                        ┃  │
    ┃                        ╞══╡ ← current mod value (moves)
    ●━━                      ●━━│ ← base value (user setting)
    ┃                        ┃  │
    ┃                        ┃  ╰─ min mod range
    ┃                        ┃
```

### Elements

1. **Base value indicator** (existing handle) - Where user set the control
2. **Modulation range bracket** - Shows how far mod can push the value
3. **Current value line** - Animated, shows real-time modulated value
4. **Colour coding**:
   - Base handle: normal grey
   - Mod range: subtle colour (e.g. cyan outline)
   - Current value: brighter version of mod colour

### Implementation Approach

Option A: **Overlay widget**
- Transparent widget layered over slider
- Draws mod indicators
- Receives mod values via signal

Option B: **Extended slider class**
- ModulatedSlider extends FaderSlider
- Has `setModulationRange(min, max)` and `setModulatedValue(value)`
- Draws indicators in `paintEvent()`

Option C: **Separate indicator widget**
- Small widget next to slider
- Shows just the mod range and current value
- Doesn't overlay the slider itself

**Recommendation:** Option B - cleaner integration, single widget to manage.

### Data Flow

```
SC calculates modulated value
         │
         ▼
OSC message: /noise/gen/1/cutoff/modulated 0.73
         │
         ▼
Python receives, routes to correct slider
         │
         ▼
slider.setModulatedValue(0.73)
         │
         ▼
Slider repaints with current mod indicator
```

### Update Rate

- Mod visualisation needs ~30fps for smooth animation
- Could batch updates to reduce CPU
- Only update visible sliders (skip if window minimised)

### Range Calculation

When connection made in matrix:
```python
base_value = slider.value()  # e.g. 0.5
depth = connection['depth']   # e.g. 0.3

mod_min = max(0, base_value - depth)  # 0.2
mod_max = min(1, base_value + depth)  # 0.8

slider.setModulationRange(mod_min, mod_max)
```

Range updates when:
- User moves base value
- Depth changed in matrix
- Connection added/removed

---

## Integration Between Parts

The matrix and visualisation work together:

1. **User creates connection in matrix** → Target slider shows mod range
2. **LFO runs in SC** → Sends modulated values → Slider animates
3. **User adjusts depth in matrix** → Slider range indicators update
4. **User disconnects in matrix** → Slider returns to normal appearance

---

## Files Involved

### New Files
- `src/gui/modulation_matrix.py` - Matrix window
- `src/gui/modulated_slider.py` - Extended slider with visualisation (or extend existing)

### Modified Files
- `src/gui/widgets.py` - Add modulation visualisation to sliders
- `src/gui/generator_slot_builder.py` - Use modulated sliders
- `src/gui/main_frame.py` - Menu item / shortcut to open matrix
- `src/audio/osc_bridge.py` - Handle modulated value messages
- `supercollider/core/osc_handlers.scd` - Send modulated values

### Config
- `src/config/__init__.py` - Modulation source/destination definitions
- Preset JSON schema for connections

---

## Open Questions

1. **Modulation calculation location** - SC or Python? SC is more efficient for audio-rate mod, but Python needs values for visualisation.

2. **Bipolar vs unipolar** - Should all mod depths be bipolar (-1 to +1) or allow unipolar (0 to +1)?

3. **Multiple sources per destination** - Allow multiple modulators on same param? If so, how do they combine (add, multiply, max)?

4. **Mod depth per-destination or per-connection?** - Matrix cell click sets depth, but should there be a global "mod amount" per source too?

5. **MIDI learn for matrix** - Click cell, move CC, auto-assign?

---

## References

- Korg wavestate software editor - modulation visualisation
- Bitwig Studio modulation system - matrix + per-control indicators  
- VCV Rack - cable-based but similar visual feedback concept
- Ableton Live - macro mapping visualisation
