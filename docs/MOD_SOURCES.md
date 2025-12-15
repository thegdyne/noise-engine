# Mod Sources

**Status:** Phase 7 Complete (Scope Display working)  
**Created:** December 2025  
**Last Updated:** December 15, 2025

## Overview

Modulation source system using the same slot-based architecture as audio generators. Four mod source slots arranged in a 2×2 grid aligned with the generator rows, each outputting to 3 mod buses (12 total). Mod generators are purpose-built for modulation duties - simpler than audio generators, focused on CV output.

---

## References & Inspirations

### LFO - Ginkosynthese TTLFO v2

The LFO is based on the **Ginkosynthese TTLFO v2** Eurorack module.

**Key features from TTLFO v2:**
- Clock-synced with division/multiplication
- 8 waveform types including Sample & Hold
- Shape control (waveform distortion / centre point shift)
- Phase offset per output

**Our implementation:**
- 3 independent outputs (A, B, C) vs TTLFO's single output
- Per-output waveform, phase, and polarity selection
- Uses master clock x32 rate for smooth sync at all divisions
- Added FREE mode (not clock-synced) - *planned*

**Reference:** https://ginkosynthese.com/product/ttlfo-v2

### Sloth - Nonlinear Circuits Triple Sloth

The Sloth is based on **Nonlinear Circuits (NLC) Triple Sloth** by Andrew F.

**Key features from Triple Sloth:**
- Three chaos circuits at drastically different speeds
- Torpor: 15-30 second cycles
- Apathy: 60-90 second cycles  
- Inertia: 30-40 minute cycles
- Outputs X, Y, Z from different circuit taps
- Z is inverted Y

**Our implementation:**
- Simplified Lorenz-like chaos (not full circuit emulation)
- Mode select (Torpor/Apathy/Inertia) instead of 3 separate circuits
- Bias control affects attractor weighting
- Per-output polarity control

**Reference:** https://www.nonlinearcircuits.com/modules/p/triple-sloth

**⚠️ Timing Review Needed:** Current implementation uses LFNoise2 with cross-modulation. The timings may not match the hardware accurately:
- Torpor: Currently ~20s (target 15-30s) ✓
- Apathy: Currently ~75s (target 60-90s) ✓
- Inertia: Currently ~33min (target 30-40min) ✓

The current implementation is a "Sloth-inspired" chaos source, not a direct circuit emulation.

---

## Architecture

### Slot Layout (2×2 Grid)

```
┌─────────────────┬─────────────────┐
│    MOD 1        │    MOD 2        │  ← Aligns with Generator Row 1
│    [LFO]        │    [Sloth]      │
├─────────────────┼─────────────────┤
│    MOD 3        │    MOD 4        │  ← Aligns with Generator Row 2
│    [LFO]        │    [Sloth]      │
└─────────────────┴─────────────────┘
```

Default configuration: LFO/Sloth/LFO/Sloth

### Bus Layout

| Slot | Outputs | Buses |
|------|---------|-------|
| MOD 1 | A, B, C | 0, 1, 2 |
| MOD 2 | A, B, C | 3, 4, 5 |
| MOD 3 | A, B, C | 6, 7, 8 |
| MOD 4 | A, B, C | 9, 10, 11 |

Formula: `bus_index = (slot - 1) * 3 + output`

---

## LFO

### Clock Sync

LFO uses the master clock x32 rate (32 ticks per quarter note) for smooth sync at all divisions.

**Rate table (12 rates):**

| Rate | Ticks | Duration (120 BPM) |
|------|-------|-------------------|
| /64 | 2048 | 16 bars (32 sec) |
| /32 | 1024 | 8 bars (16 sec) |
| /16 | 512 | 4 bars (8 sec) |
| /8 | 256 | 2 bars (4 sec) |
| /4 | 128 | 1 bar (2 sec) |
| /2 | 64 | 2 beats (1 sec) |
| 1 | 32 | 1 beat (0.5 sec) |
| x2 | 16 | 1/2 beat |
| x4 | 8 | 1/4 beat |
| x8 | 4 | 1/8 beat |
| x16 | 2 | 1/16 beat |
| x32 | 1 | 1/32 beat |

**Implementation:**
- Clock source: `~clockTrigBus` index 12 (x32)
- Frequency derived from BPM: `freq = bpm / 60 * 32 / ticksPerCycle`
- Phase reset via `PulseDivider.kr`
- Smooth ramp via `Phasor.kr`

### Waveforms (8 types)

1. **Saw** - Ramp down (1→0)
2. **Ramp** - Ramp up (0→1)
3. **Sqr** - Square/pulse (shape = PWM)
4. **Tri** - Triangle (shape = symmetry)
5. **Sin** - Sine
6. **Rect+** - Full-wave rectified sine (bumps)
7. **Rect-** - Inverted full-wave rectified (inverse bumps)
8. **S&H** - Sample & Hold (random on reset)

### Shape Distortion

The SHAP control shifts the waveform centre point (0.0-1.0):
- 0.5 = Original waveform
- <0.5 = Pushed one direction
- >0.5 = Pushed other direction

Effect per waveform:
- **Sqr**: PWM (pulse width)
- **Tri**: Asymmetric ramp
- **Sin**: Skewed sine

### Phase Offsets

Default phases provide ~120° spacing:
- Output A: 0° (index 0)
- Output B: 135° (index 3)
- Output C: 225° (index 5)

8 phase steps: 0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°

### FREE Mode (Planned)

Currently LFO is always clock-synced. Planned addition:
- FREE mode: manual frequency control (0.01Hz - 100Hz)
- Syncs to clock when switched back to CLK mode

---

## Sloth

### Speed Modes

| Mode | Cycle Time | Frequency |
|------|-----------|-----------|
| Torpor | ~15-30s | 0.033-0.067 Hz |
| Apathy | ~60-90s | 0.011-0.017 Hz |
| Inertia | ~30-40min | 0.0004-0.0006 Hz |

Current implementation values:
- Torpor: 0.05 Hz (~20s)
- Apathy: 0.013 Hz (~75s)
- Inertia: 0.0005 Hz (~33min)

### Chaos Algorithm

Simplified Lorenz-like chaos using coupled LFNoise2 oscillators with cross-modulation:

```supercollider
x = LFNoise2.kr(freq * 1.1);
y = LFNoise2.kr(freq * 0.9);
x = (x + (y * 0.3 * bias)).clip(-1, 1);
y = (y + (x * 0.3 * (1 - bias))).clip(-1, 1);
z = y.neg;  // Z is inverted Y
```

**Note:** This is NOT a true Lorenz system or circuit emulation. It produces slowly-varying chaotic-like signals but differs from the actual NLC Triple Sloth circuit behavior.

### Bias Control

The BIAS parameter affects attractor weighting:
- 0.0 = Y influences X more
- 0.5 = Balanced coupling
- 1.0 = X influences Y more

Also scales frequency slightly (0.7x - 1.3x).

### Outputs

- **X** - Primary chaos signal
- **Y** - Secondary chaos signal (coupled to X)
- **Z** - Inverted Y (as per NLC design)

---

## Scope Display

Each slot has an integrated oscilloscope showing all 3 outputs.

### Features
- 3 traces, colour-coded (green/cyan/orange from skin)
- Circular buffer (128 samples)
- ~30fps update rate
- Bipolar (-1 to +1) or unipolar (0 to 1) display
- Grid with center line

### Auto-Ranging (Planned)

| Generator | Rate/Mode | Time Scale |
|-----------|-----------|-----------|
| LFO | x4 | ~0.5 seconds |
| LFO | 1 | ~2 seconds |
| LFO | /4 | ~8 seconds |
| Sloth Torpor | - | ~60 seconds |
| Sloth Apathy | - | ~3 minutes |
| Sloth Inertia | - | ~60 minutes |

---

## UI Controls

### LFO Slot

```
┌─────────────────────────────────────────┐
│  MOD 1                         [LFO ▼] │
├─────────────────────────────────────────┤
│  A [Saw▼] [0°  ▼] [BI]                 │
│  B [Saw▼] [135°▼] [BI]                 │
│  C [Saw▼] [225°▼] [BI]                 │
├─────────────────────────────────────────┤
│  RATE ═══════════════════════          │
│  SHAP ═══════════════════════          │
├─────────────────────────────────────────┤
│  ┌───────────────────────────────────┐  │
│  │         ~ scope ~                 │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Sloth Slot

```
┌─────────────────────────────────────────┐
│  MOD 2                       [Sloth▼]  │
├─────────────────────────────────────────┤
│  X                             [BI]    │
│  Y                             [BI]    │
│  Z                             [BI]    │
├─────────────────────────────────────────┤
│  MODE ═══════════════════════          │
│  BIAS ═══════════════════════          │
├─────────────────────────────────────────┤
│  ┌───────────────────────────────────┐  │
│  │         ~ scope ~                 │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## SSOT Compliance

### Python Config (`src/config/__init__.py`)

```python
MOD_SLOT_COUNT = 4
MOD_OUTPUTS_PER_SLOT = 3
MOD_BUS_COUNT = 12
MOD_GENERATOR_CYCLE = ["Empty", "LFO", "Sloth"]
MOD_LFO_WAVEFORMS = ["Saw", "Ramp", "Sqr", "Tri", "Sin", "Rect+", "Rect-", "S&H"]
MOD_LFO_PHASES = [0, 45, 90, 135, 180, 225, 270, 315]
MOD_SLOTH_MODES = ["Torpor", "Apathy", "Inertia"]
MOD_CLOCK_RATES = ["/64", "/32", "/16", "/8", "/4", "/2", "1", "x2", "x4", "x8", "x16", "x32"]
MOD_CLOCK_SOURCE_INDEX = 12  # x32 clock
MOD_CLOCK_TICKS_PER_QUARTER = 32
MOD_CLOCK_TICKS_PER_CYCLE = [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1]
MOD_POLARITY = ["UNI", "BI"]
MOD_OUTPUT_LABELS = {"Empty": [...], "LFO": ["A","B","C"], "Sloth": ["X","Y","Z"]}
```

### SC Config (`supercollider/config.scd`)

```supercollider
~modClockSourceIndex = 12;
~modClockTicksPerCycle = [2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4, 2, 1];
```

---

## Files

```
src/config/__init__.py          # All MOD_* constants
src/gui/mod_source_slot.py      # Single slot widget
src/gui/mod_source_panel.py     # 2×2 container
src/gui/mod_scope.py            # Oscilloscope widget

supercollider/config.scd        # ~modClockSourceIndex, ~modClockTicksPerCycle
supercollider/core/mod_buses.scd   # ~modBuses[12]
supercollider/core/mod_slots.scd   # ~startModSlot, ~freeModSlot
supercollider/core/mod_osc.scd     # OSC handlers
supercollider/core/mod_lfo.scd     # modLFO SynthDef
supercollider/core/mod_sloth.scd   # modSloth SynthDef
supercollider/mod_generators/lfo.json
supercollider/mod_generators/sloth.json
```

---

## Known Issues & TODOs

1. **LFO FREE mode** - Not implemented, always clock-synced
2. **Scope auto-ranging** - Not implemented, fixed time scale
3. **Sloth accuracy** - Simplified algorithm, not true circuit emulation
4. **Phase 8 polish** - Empty state, tooltips, edge cases incomplete

---

## Changelog

### December 15, 2025
- Clock upgraded from x12 to x32 (12 rates now possible)
- Default phases spread at ~120° (0°, 135°, 225°)
- Default generators: LFO/Sloth/LFO/Sloth
- State sync on connect (generators + parameters)
- Scope throttling (30fps, not per-message)
- Skin system integration (accent colours)
- CycleButton wrap=True by default

### December 14, 2025
- Initial implementation (Phases 1-7)
- LFO with clock sync, 8 waveforms, shape distortion
- Sloth with 3 speed modes, chaos algorithm
- Scope display with 3 traces
- 2×2 grid layout aligned with generators
