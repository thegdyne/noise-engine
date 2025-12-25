# Adding New Bus Parameters to Noise Engine

*Complete checklist to avoid the portamento nightmare*

---

## Overview

Adding a new control bus parameter (like `portamento`, `transpose`, etc.) requires changes across **6 layers**. Missing any layer causes subtle bugs:

| Layer | Files | Symptom if missed |
|-------|-------|-------------------|
| Python Config | `src/config/__init__.py` | OSC path undefined |
| Python GUI | `generator_slot.py`, `generator_slot_builder.py` | Knob does nothing |
| Python Presets | `preset_schema.py` | Value not saved/restored |
| SC Core | `supercollider/core/buses.scd` | Bus undefined |
| SC Generators | `supercollider/generators/*.scd` | Compilation error |
| Imaginarium | `imaginarium/methods/*/*.py`, `render.py` | 30s timeout, silent failure |
| Pack Generators | `packs/*/generators/*.scd` | Compilation error on load |
| Validation | `tools/forge_validate.py` | False validation failures |

---

## Complete Checklist

### 1. Python Config

**File:** `src/config/__init__.py`

```python
OSC_PATHS = {
    # ... existing paths ...
    'gen_portamento': '/noise/gen/portamento',  # ADD
}
```

---

### 2. Python GUI

**File:** `src/gui/generator_slot.py`

```python
# Signal (after other signals)
portamento_changed = pyqtSignal(int, float)  # slot_id, value

# Instance variable (in __init__)
self.portamento = 0.0

# In get_state()
return {
    # ... existing ...
    "portamento": self.portamento,
}

# In set_state()
port = state.get("portamento", 0.0)
self.portamento = port
if hasattr(self, 'portamento_knob'):
    self.portamento_knob.blockSignals(True)
    self.portamento_knob.set_value(port)
    self.portamento_knob.blockSignals(False)
self.portamento_changed.emit(self.slot_id, self.portamento)

# Handler method
def on_portamento_changed(self, value):
    self.portamento = value
    self.portamento_changed.emit(self.slot_id, self.portamento)
```

**File:** `src/gui/generator_slot_builder.py`

```python
# Create knob
slot.portamento_knob = MiniKnob(
    label="PORT",
    min_val=0.0,
    max_val=1.0,
    default=0.0,
    tooltip="Portamento glide time"
)
slot.portamento_knob.value_changed.connect(slot.on_portamento_changed)
# Add to layout
```

**File:** `src/gui/generator_grid.py`

```python
# Signal
generator_portamento_changed = pyqtSignal(int, float)

# Connection (in loop creating slots)
slot.portamento_changed.connect(self.on_portamento_changed)

# Handler
def on_portamento_changed(self, slot_id, value):
    self.generator_portamento_changed.emit(slot_id, value)
```

**File:** `src/gui/main_frame.py`

```python
# Connection
self.generator_grid.generator_portamento_changed.connect(self.on_generator_portamento)

# Handler
def on_generator_portamento(self, slot_id, value):
    if self.osc_connected:
        self.osc.client.send_message(OSC_PATHS['gen_portamento'], [slot_id, value])
```

---

### 3. Python Presets

**File:** `src/presets/preset_schema.py`

```python
@dataclass
class SlotState:
    # ... existing fields ...
    portamento: float = 0.0  # ADD

def to_dict(self) -> dict:
    return {
        # ... existing ...
        "portamento": self.portamento,  # ADD
    }

@classmethod
def from_dict(cls, data: dict) -> "SlotState":
    return cls(
        # ... existing ...
        portamento=data.get("portamento", 0.0),  # ADD with default
    )
```

---

### 4. SuperCollider Core Buses

**File:** `supercollider/core/buses.scd`

```supercollider
// In ~genParams loop (around line 50)
~genParams[slot][\portamento] = Bus.control(s, 1).set(0.0);

// In ~genUserParams loop (if using relative modulation)
~genUserParams[slot][\portamento] = Bus.control(s, 1).set(0.0);
```

---

### 5. SuperCollider Core Generators (34 files)

**Location:** `supercollider/generators/*.scd`

For EACH file:

```supercollider
// 1. Add to var declarations
var sig, freq, ..., portamento;

// 2. Add to SynthDef signature (after customBus4)
SynthDef(\name, { |out, freqBus, ..., customBus4, portamentoBus|

// 3. Read and apply
portamento = In.kr(portamentoBus);
freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
```

**Bulk fix script:**
```bash
#!/bin/bash
for f in supercollider/generators/*.scd; do
    # Add portamentoBus to signature
    sed -i '' 's/customBus4|/customBus4, portamentoBus|/' "$f"
    # Add to var (if not present)
    grep -q "portamento" "$f" || sed -i '' 's/var sig,/var sig, portamento,/' "$f"
done
```

---

### 6. Imaginarium Method Templates (30 files)

**Location:** `imaginarium/methods/*/*.py`

For EACH method file:

```python
# In generate_synthdef(), ensure signature includes portamentoBus
SIGNATURE = """{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0,
    clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus,
    seed=0|"""
```

**CRITICAL - File:** `imaginarium/render.py`

```python
def _transform_for_nrt(self, scd_code: str) -> str:
    # ... existing transforms ...
    
    # ADD: Replace portamentoBus read with fixed value
    code = re.sub(r'In\.kr\(portamentoBus\)', '0.0', code)
    
    return code
```

⚠️ **Why this matters:** NRT rendering uses fixed values instead of buses. If a bus read isn't replaced, the variable is undefined → SuperCollider hangs → 30-second timeout → all candidates fail silently.

---

### 7. Existing Pack Generators

**Location:** `packs/*/generators/*.scd`

Apply same pattern as core generators. Use patch script:

```bash
#!/bin/bash
for f in packs/*/generators/*.scd; do
    if grep -q "customBus4|" "$f" && ! grep -q "portamentoBus" "$f"; then
        sed -i '' 's/customBus4|/customBus4, portamentoBus|/' "$f"
        echo "Patched: $f"
    fi
done
```

---

### 8. Validation Tool

**File:** `tools/forge_validate.py`

```python
REQUIRED_BUS_ARGS = [
    "out", "freqBus", "cutoffBus", "resBus", "attackBus", "decayBus",
    "filterTypeBus", "envEnabledBus", "envSourceBus",
    "clockRateBus", "clockTrigBus",
    "midiTrigBus", "slotIndex",
    "customBus0", "customBus1", "customBus2", "customBus3", "customBus4",
    "portamentoBus",  # ADD
]
```

---

## Verification Commands

```bash
# 1. Check Python files
grep -r "portamento" src/ --include="*.py" | wc -l
# Expected: 8-12 occurrences

# 2. Check SC core
grep -n "portamento" supercollider/core/buses.scd
# Expected: 2 occurrences (genParams and genUserParams)

# 3. Check core generators
grep -l "portamentoBus" supercollider/generators/*.scd | wc -l
# Expected: 34

# 4. Check Imaginarium methods
grep -l "portamentoBus" imaginarium/methods/*/*.py | wc -l
# Expected: 30

# 5. Check render.py transform
grep "portamentoBus" imaginarium/render.py
# Expected: 1 occurrence in _transform_for_nrt

# 6. Check pack generators
grep -l "portamentoBus" packs/*/generators/*.scd | wc -l
# Expected: matches number of pack generators

# 7. Validation tool
grep "portamentoBus" tools/forge_validate.py
# Expected: in REQUIRED_BUS_ARGS
```

---

## Common Failure Modes

| Symptom | Likely Cause |
|---------|--------------|
| "Variable 'portamentoBus' not defined" | Missing from SynthDef signature |
| Knob does nothing | Missing OSC handler in main_frame.py |
| Preset doesn't restore value | Missing from `set_state()` or `from_dict()` |
| Imaginarium renders timeout (30s) | Missing replacement in `render.py` |
| Some packs error, others don't | Handcrafted packs not updated |
| Validation false failures | Missing from REQUIRED_BUS_ARGS |

---

## File Count Summary

| Layer | Files to Modify |
|-------|-----------------|
| Python Config | 1 |
| Python GUI | 4 |
| Python Presets | 1 |
| SC Core | 1 |
| SC Generators | 34 |
| Imaginarium Methods | 30 |
| Imaginarium Render | 1 |
| Pack Generators | Variable (all packs) |
| Validation | 1 |
| **Total** | **~75+ files** |

---

## Reference: Portamento Implementation

The portamento parameter was added in December 2025. See git history for the complete implementation across all layers.

**Lag.kr timing:**
- `0.0` → 1ms (essentially instant)
- `0.5` → ~70ms (short glide)
- `1.0` → 500ms (long glide)

**Mapping:** `portamento.linexp(0, 1, 0.001, 0.5)`

---

*Created after the Great Portamento Debugging Session of December 2025*
*Updated: 2025-12-25*
