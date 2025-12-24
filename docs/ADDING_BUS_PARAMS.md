# Adding New Bus Parameters to Noise Engine

*Checklist to avoid the portamento nightmare*

---

## Overview

Adding a new control bus parameter (like `portamento`, `transpose`, etc.) requires changes across **5 layers**. Missing any layer causes subtle bugs:

| Layer | Symptom if missed |
|-------|-------------------|
| Python GUI/OSC | Knob does nothing |
| Core SC generators | SC compilation error |
| Imaginarium templates | Generated packs don't respond |
| Imaginarium NRT render | **Silent 30s timeouts** |
| Existing pack generators | SC compilation error on load |

---

## Checklist

### 1. Python Side

- [ ] **`src/config/__init__.py`** — Add OSC path to `OSC_PATHS` dict
- [ ] **`src/presets/preset_schema.py`** — Add field to `SlotState` dataclass, `to_dict()`, and `from_dict()`
- [ ] **`src/gui/generator_slot.py`** — Add signal, instance variable, `get_state()`, `set_state()`, handler method
- [ ] **`src/gui/generator_slot_builder.py`** — Add UI widget (knob/button) with signal connection
- [ ] **`src/gui/generator_grid.py`** — Add signal definition, connection, and handler
- [ ] **`src/gui/main_frame.py`** — Add signal connection and OSC send handler

### 2. SuperCollider Core Buses

- [ ] **`supercollider/core/buses.scd`** — Add bus to `~genParams[slot]` loop
- [ ] **`supercollider/core/buses.scd`** — Add bus to `~genUserParams[slot]` loop

### 3. Core SC Generators (34 files)

For each file in `supercollider/generators/*.scd`:

- [ ] Add to `var` declaration list
- [ ] Add `{paramName}Bus` to SynthDef signature (after `customBus4`)
- [ ] Add `In.kr({paramName}Bus)` read
- [ ] Apply parameter (e.g., `Lag.kr()` for portamento)

**Bulk fix script:**
```python
import re
from pathlib import Path

for f in Path("supercollider/generators").glob("*.scd"):
    content = f.read_text()
    # Add to signature
    content = re.sub(r'customBus4\|', 'customBus4, newParamBus|', content)
    # Add var
    content = re.sub(r'var sig,', 'var sig, newParam,', content)
    # Add read (after freq read)
    content = re.sub(
        r'freq = In\.kr\(freqBus\);',
        'freq = In.kr(freqBus);\n    newParam = In.kr(newParamBus);',
        content
    )
    f.write_text(content)
```

### 4. Imaginarium Method Templates (30 files)

For each file in `imaginarium/methods/*/*.py`:

- [ ] Add bus to `SYNTHDEF_SIGNATURE` constant (if exists)
- [ ] Add to `generate_synthdef()` output

**Bulk fix script:**
```python
import re
from pathlib import Path

for f in Path("imaginarium/methods").rglob("*.py"):
    if f.name == "__init__.py" or f.name == "base.py":
        continue
    content = f.read_text()
    if "customBus4|" in content:
        content = content.replace("customBus4|", "customBus4, newParamBus|")
        f.write_text(content)
```

### 5. Imaginarium NRT Render ⚠️ CRITICAL

- [ ] **`imaginarium/render.py`** — Add replacement in `_transform_for_nrt()`:

```python
# In _transform_for_nrt(), add after other bus replacements:
code = re.sub(r'In\.kr\(newParamBus\)', 'DEFAULT_VALUE', code)
```

**Why this matters:** NRT rendering uses fixed values instead of buses. If a bus read isn't replaced, the variable is undefined → SuperCollider hangs → 30-second timeout → all candidates fail silently.

### 6. Existing Pack Generators

For all `.scd` files in `packs/*/generators/`:

- [ ] Add bus to SynthDef signature
- [ ] Add var declaration
- [ ] Add bus read

**Fix script:**
```python
import re
from pathlib import Path

for f in Path("packs").glob("*/generators/*.scd"):
    content = f.read_text()
    has_read = "In.kr(newParamBus)" in content
    has_arg = "newParamBus|" in content
    
    if has_read and not has_arg:
        content = re.sub(r'customBus4\s*\|', 'customBus4, newParamBus|', content)
        f.write_text(content)
        print(f"Fixed: {f}")
```

---

## Verification

After all changes:

```bash
# 1. Python syntax check
python -m py_compile src/gui/generator_slot.py
python -m py_compile src/presets/preset_schema.py

# 2. Count affected files
grep -r "newParamBus" supercollider/ --include="*.scd" | wc -l
grep -r "newParamBus" imaginarium/ --include="*.py" | wc -l
grep -r "newParamBus" packs/ --include="*.scd" | wc -l

# 3. Load Noise Engine - check for compilation errors
python src/main.py

# 4. Test Imaginarium generation (NRT render)
python3 -m imaginarium generate --image test.jpg --name test_pack --seed 42
```

---

## Common Failure Modes

| Symptom | Likely Cause |
|---------|--------------|
| "Variable 'xBus' not defined" | Missing from SynthDef signature |
| Knob does nothing | Missing OSC handler in main_frame.py |
| Preset doesn't restore value | Missing from `set_state()` or `from_dict()` |
| Imaginarium renders timeout | Missing replacement in `render.py` |
| Some packs error, others don't | Handcrafted packs not updated |

---

## Reference: Portamento Implementation

See commit history from 2025-12-24 for a complete example of adding the `portamento` bus parameter across all layers.

Files changed: ~110 files total
- 6 Python files
- 34 core generators
- 30 Imaginarium templates
- 1 render.py
- 34+ pack generators

---

*Created after the Great Portamento Debugging Session of December 2025*
