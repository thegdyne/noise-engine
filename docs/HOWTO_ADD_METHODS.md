# How to Add Imaginarium Synthesis Methods

*Guide to creating new synthesis methods for the Imaginarium pipeline*

---

## Overview

Each synthesis method consists of a single Python file that defines:
- Parameter axes (P1-P5 sliders)
- Macro controls (grouped parameter presets)
- SuperCollider SynthDef generation

Methods are validated automatically and must pass all checks before use.

---

## File Location

```
imaginarium/methods/{family}/{method_name}.py
```

Families: `fm`, `physical`, `spectral`, `subtractive`, `texture`

---

## Template Structure

```python
"""
imaginarium/methods/{family}/{method_name}.py
Brief description of the synthesis method

Character: Keywords describing the sound
Tags: FAMILY_TAG, technique, character
"""

from typing import Dict

from ..base import (
    MethodTemplate,
    MethodDefinition,
    ParamAxis,
    MacroControl,
)


class MyMethodTemplate(MethodTemplate):
    """Docstring explaining the synthesis approach."""
    
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="{family}/{method_name}",  # Must match file path
            family="{family}",
            display_name="Human Readable Name",
            template_version="1",
            param_axes=[
                # Up to 5 ParamAxis definitions (P1-P5)
            ],
            macro_controls=[
                # Optional macro definitions
            ],
            default_tags={"topology": "...", "character": "..."},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        """Return tags based on current parameter values."""
        tags = {
            "family": "{family}",
            "method": self._definition.method_id,
            # Add dynamic tags based on params
        }
        return tags
    
    def generate_synthdef(
        self,
        synthdef_name: str,
        params: Dict[str, float],
        seed: int,
    ) -> str:
        """Generate SuperCollider SynthDef code."""
        # Get axis read expressions
        axes = {a.name: a for a in self._definition.param_axes}
        param1_read = axes["param1"].sc_read_expr("customBus0", 0)
        # ... etc for each axis
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    // Declare custom param vars

    // Seed for determinism
    RandSeed.ir(1, seed);

    // Read standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\\amplitude]);

    // === READ CUSTOM PARAMS ===
    {param1_read}
    // ... etc

    // === YOUR SYNTHESIS CODE ===
    sig = ...;

    // === OUTPUT CHAIN (REQUIRED) ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
```

---

## ParamAxis Definition

```python
ParamAxis(
    name="param_name",      # Internal identifier
    min_val=0.0,            # Minimum value
    max_val=1.0,            # Maximum value  
    default=0.5,            # Default value
    curve="lin",            # "lin" or "exp"
    label="LBL",            # 3-char label for UI
    tooltip="Description",  # Hover text
    unit="",                # Optional unit (Hz, s, dB, x, etc.)
)
```

### Validation Rules

| Rule | Requirement |
|------|-------------|
| `label` | Exactly 3 characters, uppercase A-Z and 0-9 only |
| `tooltip` | Required, non-empty |
| `curve="exp"` | **min_val must be > 0** (common gotcha!) |
| `min_val < max_val` | Always required |
| Round-trip | `denormalize(normalize(x)) ≈ x` must hold |

### Common Labels

Avoid these (conflict with core params): `CUT`, `RES`, `ATK`, `DEC`, `FRQ`

Good examples: `WID`, `DRV`, `MIX`, `DPT`, `RAT`, `FBK`, `DMG`, `SHP`

---

## Reading Parameters in SynthDef

Use `sc_read_expr()` to generate the bus read code:

```python
axes = {a.name: a for a in self._definition.param_axes}
width_read = axes["width"].sc_read_expr("customBus0", 0)
drive_read = axes["drive"].sc_read_expr("customBus1", 1)
# ... up to customBus4 for P5
```

This generates code like:
```supercollider
/// IMAG_CUSTOMBUS:0
width = In.kr(customBus0).linlin(0, 1, 0.0, 1.0);
```

The marker comment (`IMAG_CUSTOMBUS:N`) is required for validation.

---

## SynthDef Requirements

### Required Arguments

```supercollider
|out, freqBus, cutoffBus, resBus, attackBus, decayBus,
 filterTypeBus, envEnabledBus, envSourceBus=0,
 clockRateBus, clockTrigBus,
 midiTrigBus=0, slotIndex=0,
 customBus0, customBus1, customBus2, customBus3, customBus4,
 seed={seed}|
```

### Required First Line (after var declarations)

```supercollider
RandSeed.ir(1, seed);
```

### Required Output Chain

```supercollider
sig = ~multiFilter.(sig, filterType, filterFreq, rq);
sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
sig = ~ensure2ch.(sig);
Out.ar(out, sig);
```

### Optional Helpers

```supercollider
sig = ~stereoSpread.(sig, rate, width);  // Mono to stereo with movement
```

---

## F-String Gotchas

SuperCollider uses `{` and `}` for blocks. In Python f-strings, these must be escaped:

**Problem:**
```python
# This breaks!
modes = modeFreqs.collect({ |mf, i| ... });
```

**Solutions:**

1. **Escape braces:** `{{` and `}}`
```python
modes = modeFreqs.collect({{ |mf, i| ... }});
```

2. **Unroll loops manually** (recommended for clarity):
```python
mode1 = Ringz.ar(exciter, modeFreqs[0], decay);
mode2 = Ringz.ar(exciter, modeFreqs[1], decay);
# etc.
```

---

## Registration

After creating the method file, register it in two places:

### 1. Family `__init__.py`

`imaginarium/methods/{family}/__init__.py`:

```python
from .my_method import MyMethodTemplate

__all__ = [
    # ... existing ...
    "MyMethodTemplate",
]

# In the FAMILY_METHODS dict:
"{family}/my_method": MyMethodTemplate,
```

### 2. Main `__init__.py`

`imaginarium/methods/__init__.py` in `_register_builtins()`:

```python
# Add import
from .{family}.my_method import MyMethodTemplate

# Add registration
register_method(MyMethodTemplate())
```

---

## Validation

Run the validator before committing:

```bash
python -m imaginarium.validate_methods
```

### Common Failures

| Error | Fix |
|-------|-----|
| `exp curve requires min_val > 0` | Change `min_val=0.0` to `min_val=0.01` (or similar small positive) |
| `label must be uppercase A-Z/0-9` | Use only letters and numbers, no symbols like `/` |
| `round-trip failed` | Check min/max values and curve type |
| `IMAG_CUSTOMBUS:N marker missing` | Use `axis.sc_read_expr()` instead of manual bus reads |

---

## Example: Minimal Method

```python
"""imaginarium/methods/texture/simple_noise.py"""

from typing import Dict
from ..base import MethodTemplate, MethodDefinition, ParamAxis, MacroControl


class SimpleNoiseTemplate(MethodTemplate):
    def __init__(self):
        self._definition = MethodDefinition(
            method_id="texture/simple_noise",
            family="texture",
            display_name="Simple Noise",
            template_version="1",
            param_axes=[
                ParamAxis(
                    name="color",
                    min_val=0.0, max_val=1.0, default=0.5,
                    curve="lin", label="CLR",
                    tooltip="Noise color (dark to bright)", unit="",
                ),
                ParamAxis(
                    name="density",
                    min_val=0.01, max_val=1.0, default=0.5,  # Note: 0.01 not 0.0!
                    curve="exp", label="DNS",
                    tooltip="Noise density", unit="",
                ),
            ],
            macro_controls=[],
            default_tags={"topology": "noise", "character": "textural"},
        )
    
    @property
    def definition(self) -> MethodDefinition:
        return self._definition
    
    def get_tags(self, params: Dict) -> Dict[str, str]:
        return {"family": "texture", "method": self._definition.method_id}
    
    def generate_synthdef(self, synthdef_name: str, params: Dict[str, float], seed: int) -> str:
        axes = {a.name: a for a in self._definition.param_axes}
        color_read = axes["color"].sc_read_expr("customBus0", 0)
        density_read = axes["density"].sc_read_expr("customBus1", 1)
        
        return f'''
SynthDef(\\{synthdef_name}, {{ |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                               filterTypeBus, envEnabledBus, envSourceBus=0,
                               clockRateBus, clockTrigBus,
                               midiTrigBus=0, slotIndex=0,
                               customBus0, customBus1, customBus2, customBus3, customBus4,
                               seed={seed}|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var color, density;

    RandSeed.ir(1, seed);

    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\\amplitude]);

    {color_read}
    {density_read}

    sig = PinkNoise.ar * density;
    sig = LPF.ar(sig, color.linexp(0, 1, 200, 10000));

    sig = ~stereoSpread.(sig, 0.1, 0.3);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}}).add;

"  * {synthdef_name} loaded".postln;
'''
```

---

## Checklist

- [ ] File in correct location: `imaginarium/methods/{family}/{name}.py`
- [ ] `method_id` matches path: `"{family}/{name}"`
- [ ] All ParamAxis have valid labels (3 chars, A-Z/0-9)
- [ ] All ParamAxis have non-empty tooltips
- [ ] Exp curves have `min_val > 0`
- [ ] SynthDef has `RandSeed.ir(1, seed)` first
- [ ] SynthDef uses `sc_read_expr()` for custom params
- [ ] SynthDef ends with `~multiFilter`, `~envVCA`, `~ensure2ch`, `Out.ar`
- [ ] No unescaped `{` `}` in f-string (SuperCollider blocks)
- [ ] Registered in family `__init__.py`
- [ ] Registered in main `imaginarium/methods/__init__.py`
- [ ] `python -m imaginarium.validate_methods` passes

---

*Last updated: December 2025 — 30 methods*
