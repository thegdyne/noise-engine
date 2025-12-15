# Channel EQ Specification

**Status:** ✅ Complete  
**Created:** December 2025

---

## Overview

Per-channel 3-band DJ isolator EQ on each channel strip. Quick tone shaping with full kill capability - same style as master EQ for consistency.

---

## Implementation Summary

The channel EQ is implemented as part of the channel strip SynthDef using the shared `~djIsolator` helper function. This ensures identical frequency response between channel and master EQ.

### Signal Flow
```
Generator → [Trim] → [EQ] → [Mute] → [Solo] → [Gain] → [Pan] → [Volume] → Master Bus
```

### Crossover Frequencies (SSOT)
- **LO**: < 250 Hz
- **MID**: 250 Hz - 2500 Hz  
- **HI**: > 2500 Hz

These are defined in `~eqLoXover` and `~eqHiXover` variables for consistency across channel strips and master EQ.

### Gain Range
- **0.0** = Full kill (-∞ dB)
- **1.0** = Unity (0 dB)
- **2.0** = +6 dB boost

---

## UI Controls

Mini knobs (18×18px) in the channel strip mixer panel:
- **H** - HI band
- **M** - MID band  
- **L** - LO band

Controls:
- Drag up/down to adjust
- Double-click to reset to unity
- Tooltip shows current dB value

---

## Files

| File | Role |
|------|------|
| `supercollider/core/channel_strips.scd` | `~djIsolator` helper + SynthDef |
| `supercollider/core/osc_handlers.scd` | `/noise/gen/eq/*` handlers |
| `src/gui/mixer_panel.py` | MiniKnob UI in ChannelStrip |
| `src/gui/widgets.py` | MiniKnob widget class |
| `src/config/__init__.py` | OSC path definitions |

---

## OSC Messages

```
/noise/gen/eq/lo   <slot> <float 0-2>
/noise/gen/eq/mid  <slot> <float 0-2>
/noise/gen/eq/hi   <slot> <float 0-2>
```

---

## State Persistence

EQ state is stored in arrays and preserved across generator changes:
```supercollider
~stripEqLoState = Array.fill(8, { 1.0 });
~stripEqMidState = Array.fill(8, { 1.0 });
~stripEqHiState = Array.fill(8, { 1.0 });
```
