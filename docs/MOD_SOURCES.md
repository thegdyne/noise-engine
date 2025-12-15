# Mod Sources

**Status:** Design Complete  
**Created:** December 2025

## Overview

Modulation source system using the same slot-based architecture as audio generators. Four mod source slots in the left panel, each outputting to 3 mod buses (12 total). Mod generators are purpose-built for modulation duties - simpler than audio generators, focused on CV output.

---

## SSOT Architecture

Following the same pattern as audio generators, all mod source configuration lives in `src/config/__init__.py` with supporting JSON files.

### Config Additions (`src/config/__init__.py`)

```python
# === MOD SOURCE PARAMETERS ===
# Constants for mod source system
MOD_SLOT_COUNT = 4
MOD_OUTPUTS_PER_SLOT = 3
MOD_BUS_COUNT = MOD_SLOT_COUNT * MOD_OUTPUTS_PER_SLOT  # 12

# Mod generator cycle (like GENERATOR_CYCLE)
MOD_GENERATOR_CYCLE = [
    "Empty",
    "LFO",
    "Sloth",
]

# Waveforms for LFO (single source)
MOD_LFO_WAVEFORMS = ["Saw", "Ramp", "Sqr", "Tri", "Sin", "Rect+", "Rect-", "S&H"]
MOD_LFO_WAVEFORM_INDEX = {w: i for i, w in enumerate(MOD_LFO_WAVEFORMS)}

# Phase steps for LFO (single source)
MOD_LFO_PHASES = [0, 45, 90, 135, 180, 225, 270, 315]
MOD_LFO_PHASE_INDEX = {p: i for i, p in enumerate(MOD_LFO_PHASES)}

# Sloth speed modes (single source)
MOD_SLOTH_MODES = ["Torpor", "Apathy", "Inertia"]
MOD_SLOTH_MODE_INDEX = {m: i for i, m in enumerate(MOD_SLOTH_MODES)}

# Clock rates for mod sources (reuse CLOCK_RATES or define subset)
MOD_CLOCK_RATES = ["/4", "/2", "1", "x2", "x3", "x4"]
MOD_CLOCK_RATE_INDEX = {r: i for i, r in enumerate(MOD_CLOCK_RATES)}

# Polarity options
MOD_POLARITY = ["UNI", "BI"]
MOD_POLARITY_INDEX = {"UNI": 0, "BI": 1}

# Output labels by generator type
MOD_OUTPUT_LABELS = {
    "Empty": ["A", "B", "C"],
    "LFO": ["A", "B", "C"],
    "Sloth": ["X", "Y", "Z"],
}

# === MOD GENERATOR CONFIGS ===
# Loaded from supercollider/mod_generators/*.json
_MOD_GENERATOR_CONFIGS = {}

def _load_mod_generator_configs():
    """Load mod generator configs from JSON files."""
    # Same pattern as _load_generator_configs()
    ...

def get_mod_generator_synthdef(name):
    """Get SynthDef name for a mod generator."""
    ...

def get_mod_generator_custom_params(name):
    """Get custom params for a mod generator."""
    ...

def get_mod_generator_output_config(name):
    """Get output config type: 'waveform_phase' or 'fixed'."""
    ...

def get_mod_output_labels(name):
    """Get output labels for a mod generator."""
    return MOD_OUTPUT_LABELS.get(name, ["A", "B", "C"])
```

### OSC Paths (`src/config/__init__.py`)

```python
OSC_PATHS = {
    # ... existing paths ...
    
    # Mod sources (argument-based, not templated)
    'mod_generator': '/noise/mod/generator',        # args: slot, genName
    'mod_param': '/noise/mod/param',                # args: slot, key, value
    'mod_output_wave': '/noise/mod/out/wave',       # args: slot, output, waveIndex
    'mod_output_phase': '/noise/mod/out/phase',     # args: slot, output, phaseIndex
    'mod_output_polarity': '/noise/mod/out/pol',    # args: slot, output, polarity
    
    # Mod bus values (SC → Python for scope)
    'mod_bus_value': '/noise/mod/bus/value',        # args: busIndex, value
    'mod_scope_enable': '/noise/mod/scope/enable',  # args: slot, enabled
}
```

### JSON Config Location

```
supercollider/
    mod_generators/
        lfo.json        # LFO config
        sloth.json      # Sloth config
```

Configs loaded by `_load_mod_generator_configs()` on import, same pattern as audio generators.

---

## Architecture

### Slot Structure

`ModSourceSlot` subclasses `GeneratorSlot` pattern but with:
- No filter section (CUT, RES)
- No envelope section (ATK, DEC)
- No channel strip
- 3 dedicated outputs per slot → mod buses
- Per-output polarity toggle (UNI/BI)
- Integrated scope display

### Bus Layout

| Slot | Outputs | Buses |
|------|---------|-------|
| MOD 1 | A, B, C | 0, 1, 2 |
| MOD 2 | A, B, C | 3, 4, 5 |
| MOD 3 | A, B, C | 6, 7, 8 |
| MOD 4 | A, B, C | 9, 10, 11 |

Output labels are generator-specific (A/B/C for LFO, X/Y/Z for Sloth).

### Index Domains (SSOT)

**Critical:** These ranges are fixed across Python, OSC, and SC:

| Index | Domain | Notes |
|-------|--------|-------|
| slot | 1-4 | 1-indexed (matches UI display) |
| output | 0-2 | 0-indexed (A/X=0, B/Y=1, C/Z=2) |
| bus | 0-11 | Calculated: `(slot - 1) * 3 + output` |

**Output labels (A/B/C, X/Y/Z) are presentation only, not indexing.**

OSC messages use argument-based format:
- `/noise/mod/generator 1 "LFO"` (slot 1, set to LFO)
- `/noise/mod/out/wave 2 0 4` (slot 2, output 0, waveform 4 = Sin)
- `/noise/mod/bus/value 5 0.73` (bus 5, value 0.73)

---

## Mod Generator Cycle

```python
MOD_GENERATOR_CYCLE = [
    "Empty",
    "LFO",      # TTLFO-style with 3 independent waveform outputs
    "Sloth",    # NLC triple chaos with X/Y/Z outputs
]
```

Configs stored in `supercollider/mod_generators/*.json`

---

## LFO

**Reference:** Ginkosynthese TTLFO v2

Clock-synced LFO with 3 independent outputs. Each output has its own waveform and phase, all sharing the same rate and shape distortion.

### Slot Layout

```
┌─────────────────────────────────────────┐
│  [LFO ▼]                               │
├─────────────────────────────────────────┤
│  A [Saw▼] [0°  ▼] [BI]                 │
│  B [Sqr▼] [90° ▼] [UNI]                │
│  C [Sin▼] [180°▼] [BI]                 │
├─────────────────────────────────────────┤
│  RATE ══════════════════════════════    │
│  SHAP ══════════════════════════════    │
├─────────────────────────────────────────┤
│  ┌───────────────────────────────────┐  │
│  │         ~ scope ~                 │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Per-Output Controls

| Control | Type | Options |
|---------|------|---------|
| Waveform | CycleButton | Saw, Ramp, Sqr, Tri, Sin, Rect+, Rect-, S&H |
| Phase | CycleButton | 0°, 45°, 90°, 135°, 180°, 225°, 270°, 315° |
| Polarity | Toggle | UNI (0→1) / BI (-1→+1) |

### Clock Sync Semantics

LFO uses **tick-based phase accumulation**, not free-running Hz.

Master clock sends ticks (e.g. 16ths). LFO advances phase on each tick based on RATE setting.

**RATE mapping (ticks per cycle):**

| RATE | Ticks/Cycle | Musical Duration (4/4) |
|------|-------------|------------------------|
| x4 | 1 | 1/16th (fastest) |
| x3 | 1.33 | dotted 1/16th |
| x2 | 2 | 1/8th |
| 1 | 4 | 1/4 (quarter note) |
| /2 | 8 | 1/2 (half note) |
| /4 | 16 | 1 bar |

**Phase accumulator:**
```supercollider
// On each clock tick:
phase = (phase + (1.0 / ticksPerCycle)) % 1.0;
```

This gives deterministic phase reset and tight sync, matching hardware clock-synced LFOs.

### Shared Parameters

| Param | Label | Description | Range |
|-------|-------|-------------|-------|
| rate | RATE | Clock division | /4, /2, 1, x2, x3, x4 |
| shape | SHAP | Waveform distortion (centre point shift) | 0.0-1.0 |

### Waveforms

1. **Saw** - Ramp down
2. **Ramp** - Ramp up
3. **Sqr** - Square/pulse
4. **Tri** - Triangle
5. **Sin** - Sine
6. **Rect+** - Full-wave rectified sine
7. **Rect-** - Inverted full-wave rectified sine
8. **S&H** - Sample & hold (random steps)

### Shape Distortion

SHAP control shifts the centre point of the waveform:
- 0.5 (centre) = original waveform
- 0.0 = pushed fully one direction
- 1.0 = pushed fully other direction

Effect varies by waveform:
- Saw/Ramp: changes slope ratio
- Sqr: becomes PWM
- Tri: becomes asymmetric ramp
- Sin: becomes skewed sine

### Config

JSON defines structure, Python constants define options:

```json
{
    "name": "LFO",
    "synthdef": "modLFO",
    "output_config": "waveform_phase",
    "outputs": ["A", "B", "C"],
    "custom_params": [
        {
            "key": "rate",
            "label": "RATE",
            "tooltip": "Clock division",
            "default": 0.5,
            "min": 0.0,
            "max": 1.0
        },
        {
            "key": "shape",
            "label": "SHAP",
            "tooltip": "Waveform distortion",
            "default": 0.5,
            "min": 0.0,
            "max": 1.0
        }
    ]
}
```

**SSOT references:**
- Waveforms: `MOD_LFO_WAVEFORMS` in config
- Phases: `MOD_LFO_PHASES` in config
- Clock rates: `MOD_CLOCK_RATES` in config
- Polarity: `MOD_POLARITY` in config

---

## Sloth

**Reference:** Nonlinear Circuits 8HP Triple Sloth (Andrew F)

Slow chaos circuit outputting 3 related-but-different signals. Travels around two strange attractors with unpredictable timing. Not clock-synced - deliberately organic and glacial.

### Slot Layout

```
┌─────────────────────────────────────────┐
│  [Sloth ▼]                             │
├─────────────────────────────────────────┤
│  X [BI]                                │
│  Y [UNI]                               │
│  Z [BI]                                │
├─────────────────────────────────────────┤
│  MODE ══════════════════════════════    │
│  BIAS ══════════════════════════════    │
├─────────────────────────────────────────┤
│  ┌───────────────────────────────────┐  │
│  │         ~ scope ~                 │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Per-Output Controls

| Control | Type | Options |
|---------|------|---------|
| Polarity | Toggle | UNI (0→1) / BI (-1→+1) |

No waveform/phase selection - X, Y, Z are fixed taps from the chaos circuit (Z is inverted Y).

### Parameters

| Param | Label | Description | Values |
|-------|-------|-------------|--------|
| mode | MODE | Speed mode (discrete) | Torpor / Apathy / Inertia |
| bias | BIAS | Attractor weight | 0.0-1.0 |

### Speed Modes

| Mode | Cycle Time | Character |
|------|------------|-----------|
| Torpor | 15-30 seconds | Slow drift |
| Apathy | 60-90 seconds | Glacial |
| Inertia | 30-40 minutes | Geological |

### Outputs

- **X** - First stage tap
- **Y** - Second stage tap (main output)
- **Z** - Inverted Y

All three outputs are related but different - they show the system state from different perspectives.

### Config

```json
{
    "name": "Sloth",
    "synthdef": "modSloth",
    "output_config": "fixed",
    "outputs": ["X", "Y", "Z"],
    "custom_params": [
        {
            "key": "mode",
            "label": "MODE",
            "tooltip": "Speed mode",
            "type": "discrete",
            "default": 0,
            "steps": 3
        },
        {
            "key": "bias",
            "label": "BIAS",
            "tooltip": "Attractor weight",
            "default": 0.5,
            "min": 0.0,
            "max": 1.0
        }
    ]
}
```

**SSOT references:**
- Speed modes: `MOD_SLOTH_MODES` in config (maps discrete steps to labels)
- Output labels: `MOD_OUTPUT_LABELS["Sloth"]` in config
- Polarity: `MOD_POLARITY` in config

---

## Scope

Each mod source slot has an integrated scope showing all 3 outputs.

### Display

- 3 traces overlaid, colour-coded by output
- Time scale auto-ranging based on rate/mode
- Horizontal = time, vertical = output value

### Auto-Ranging

| Generator | Rate | Approx Time Scale |
|-----------|------|-------------------|
| LFO | x4 | ~0.5 seconds |
| LFO | 1 | ~2 seconds |
| LFO | /4 | ~8 seconds |
| Sloth Torpor | - | ~60 seconds |
| Sloth Apathy | - | ~3 minutes |
| Sloth Inertia | - | ~60 minutes |

Scope adjusts automatically to show ~2-3 full cycles.

---

## UI Structure

### ModSourceSlot Widget

Subclass of GeneratorSlot pattern:

```python
class ModSourceSlot(QWidget):
    """Single mod source slot with 3 outputs."""
    
    # Signals
    generator_changed = pyqtSignal(int, str)  # slot_id, generator_name
    parameter_changed = pyqtSignal(int, str, float)  # slot_id, param_key, value
    output_waveform_changed = pyqtSignal(int, int, str)  # slot_id, output_idx, waveform
    output_phase_changed = pyqtSignal(int, int, int)  # slot_id, output_idx, phase_degrees
    output_polarity_changed = pyqtSignal(int, int, bool)  # slot_id, output_idx, is_bipolar
```

**SSOT usage in widgets:**

```python
from src.config import (
    MOD_GENERATOR_CYCLE,
    MOD_LFO_WAVEFORMS, 
    MOD_LFO_PHASES,
    MOD_POLARITY,
    MOD_OUTPUTS_PER_SLOT,
    get_mod_output_labels,
    get_mod_generator_custom_params,
)

# Generator dropdown - from config, not hardcoded
self.gen_dropdown = CycleButton(MOD_GENERATOR_CYCLE)

# Waveform buttons - from config
for i in range(MOD_OUTPUTS_PER_SLOT):
    wave_btn = CycleButton(MOD_LFO_WAVEFORMS)
    phase_btn = CycleButton([f"{p}°" for p in MOD_LFO_PHASES])
    polarity_btn = CycleButton(MOD_POLARITY)

# Output labels - from config, generator-specific
labels = get_mod_output_labels(self.current_generator)  # ["A","B","C"] or ["X","Y","Z"]
```

### ModSourcePanel Widget

Container for MOD_SLOT_COUNT ModSourceSlot widgets:

```python
from src.config import MOD_SLOT_COUNT

class ModSourcePanel(QWidget):
    """Left panel containing mod source slots."""
    
    def __init__(self):
        self.slots = {}
        for i in range(1, MOD_SLOT_COUNT + 1):
            self.slots[i] = ModSourceSlot(i)
```
```

---

## File Structure

```
src/config/
    __init__.py            # SSOT: MOD_GENERATOR_CYCLE, MOD_LFO_WAVEFORMS, 
                           #       MOD_LFO_PHASES, MOD_SLOTH_MODES, etc.
                           #       + loader functions for mod generator configs

supercollider/
    mod_generators/
        lfo.json           # LFO config (synthdef, custom_params, output_config)
        sloth.json         # Sloth config
    core/
        mod_buses.scd      # 12 mod bus definitions
        mod_synths.scd     # modLFO, modSloth SynthDefs

src/gui/
    mod_source_slot.py     # Single slot widget (uses config for all options)
    mod_source_panel.py    # Container for 4 slots
    mod_scope.py           # Scope widget
```

### SSOT Compliance

| Data | Source | NOT duplicated in |
|------|--------|-------------------|
| Mod generator list | `MOD_GENERATOR_CYCLE` | JSON, widgets |
| LFO waveforms | `MOD_LFO_WAVEFORMS` | JSON, widgets |
| LFO phases | `MOD_LFO_PHASES` | JSON, widgets |
| Sloth modes | `MOD_SLOTH_MODES` | JSON, widgets |
| Clock rates | `MOD_CLOCK_RATES` | JSON, widgets |
| Output labels | `MOD_OUTPUT_LABELS` | JSON, widgets |
| Slot count | `MOD_SLOT_COUNT` | hardcoded anywhere |
| Bus count | `MOD_BUS_COUNT` | hardcoded anywhere |
| OSC paths | `OSC_PATHS` | widgets, SC code |

Widgets read from config, never define their own lists.

---

## SuperCollider Integration

### Mod Buses

```supercollider
// Bus count from Python config (MOD_BUS_COUNT = 12)
// 4 slots × 3 outputs = 12 control buses
~modBuses = Array.fill(12, { Bus.control(s, 1) });

// Bus index calculation (matches Python):
// slot 1: buses 0, 1, 2
// slot 2: buses 3, 4, 5
// slot 3: buses 6, 7, 8
// slot 4: buses 9, 10, 11
~modBusIndex = { |slot, output| ((slot - 1) * 3) + output };
```

**SSOT Validation:** Python sends `/noise/mod/init` with bus count at boot. SC logs error if mismatch with hardcoded 12.

### Mod Slot Manager

```supercollider
// Per-slot synth node tracking
~modNodes = Array.fill(4, { nil });

~freeModSlot = { |slot|
    var idx = slot - 1;
    if(~modNodes[idx].notNil) {
        ~modNodes[idx].free;
        ~modNodes[idx] = nil;
    };
    // Zero the buses on free (not hold)
    3.do { |out|
        ~modBuses[~modBusIndex.(slot, out)].set(0);
    };
};

~startModSlot = { |slot, genName|
    var base = (slot - 1) * 3;
    var busA = ~modBuses[base + 0].index;
    var busB = ~modBuses[base + 1].index;
    var busC = ~modBuses[base + 2].index;
    
    ~freeModSlot.(slot);
    
    case
    { genName == "LFO" } {
        ~modNodes[slot - 1] = Synth(\modLFO, [
            \outA, busA, \outB, busB, \outC, busC
        ]);
    }
    { genName == "Sloth" } {
        ~modNodes[slot - 1] = Synth(\modSloth, [
            \outX, busA, \outY, busB, \outZ, busC
        ]);
    }
    { /* Empty - node stays nil, buses already zeroed */ };
};
```

### SynthDef Pattern

```supercollider
SynthDef(\modLFO, {
    |outA, outB, outC,          // 3 output buses
     rate=0.5, shape=0.5,       // shared params
     waveA=0, phaseA=0, polarityA=1,  // output A
     waveB=0, phaseB=0, polarityB=1,  // output B
     waveC=0, phaseC=0, polarityC=1|  // output C
    
    var freq, sigA, sigB, sigC;
    
    // ... generate 3 waveforms at same rate
    // ... apply shape distortion
    // ... apply phase offsets
    // ... apply polarity (uni/bi)
    
    Out.kr(outA, sigA);
    Out.kr(outB, sigB);
    Out.kr(outC, sigC);
}).add;
```

---

## Routing (Future)

Mod buses connect to generator parameters via routing matrix (separate feature). Each of the 12 mod buses can target any generator parameter with per-connection depth.

See `docs/MODULATION_SYSTEM.md` for routing matrix design.

---

## References

- **Ginkosynthese TTLFO v2** - Clock-synced LFO with waveform, multiplier, shape controls
- **Nonlinear Circuits Triple Sloth** - 3 chaos circuits at different speeds (Torpor/Apathy/Inertia)
- **Existing GeneratorSlot** - UI patterns and architecture to subclass

---

## Open Questions (Resolved)

| Question | Decision |
|----------|----------|
| Slot count | 4 |
| Outputs per slot | 3 |
| Phase steps | 8 (0°-315° in 45° increments) |
| SHAP scope | Shared across all outputs |
| Polarity scope | Per-output |
| Activity indicators | Scope only |
| Scope time scale | Auto-ranging |
| Sloth speed | Discrete modes (Torpor/Apathy/Inertia) |
