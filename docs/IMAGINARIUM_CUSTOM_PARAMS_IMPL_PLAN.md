gave the following to claude aftre reseting to a good place.. 
git reset --hard d7b13cb

Infrastructure (3 files):

imaginarium/methods/base.py
imaginarium/cli.py
imaginarium/export.py

Methods (14 files):
4. imaginarium/methods/subtractive/dark_pulse.py
5. imaginarium/methods/subtractive/bright_saw.py
6. imaginarium/methods/subtractive/supersaw.py
7. imaginarium/methods/subtractive/noise_filtered.py
8. imaginarium/methods/fm/simple_fm.py
9. imaginarium/methods/fm/feedback_fm.py
10. imaginarium/methods/fm/ratio_stack.py
11. imaginarium/methods/fm/ring_mod.py
12. imaginarium/methods/fm/hard_sync.py
13. imaginarium/methods/physical/karplus.py
14. imaginarium/methods/physical/modal.py
15. imaginarium/methods/physical/bowed.py
16. imaginarium/methods/physical/formant.py
17. imaginarium/methods/spectral/additive.py
New files I'll create:
18. imaginarium/validate_methods.py
19. tests/test_imaginarium_custom_params.py

rm -rf ./packs/pizza-pup/generators ./packs/pizza-pup/manifest.json ./packs/pizza-pup/reports
python3 -m imaginarium generate --image ./packs/pizza-pup/reference.jpg --name pizza-pup --output ./packs --seed 42


# Imaginarium Custom Params Implementation Plan

*Surgical implementation of IMAGINARIUM_CUSTOM_PARAMS_SPEC.md*

---

## Baseline

Commit: `d7b13cb` — spec doc added, no implementation
Architecture: `MethodTemplate` with registry pattern (unchanged)

---

## Phase 1: Extend ParamAxis + Tests

**File: `imaginarium/methods/base.py`**

Add to existing `ParamAxis` dataclass:
- Fields: `label: str = ""`, `tooltip: str = ""`, `unit: str = ""`
- Method: `normalize(value: float) -> float`
- Method: `denormalize(norm: float) -> float`
- Method: `to_custom_param(baked_value: float) -> dict`
- Method: `sc_read_expr(bus_name: str, axis_index: int) -> str`

No changes to `MethodTemplate`, `MethodDefinition`, `MacroControl`.

**File: `tests/test_imaginarium_custom_params.py`**

Tests:
- `test_lin_normalize_min` — value at min → 0.0
- `test_lin_normalize_max` — value at max → 1.0
- `test_lin_roundtrip` — denormalize(normalize(v)) == v
- `test_exp_normalize_min` — value at min → 0.0
- `test_exp_normalize_max` — value at max → 1.0
- `test_exp_roundtrip` — denormalize(normalize(v)) == v
- `test_normalize_clamps` — out of range values clamped
- `test_to_custom_param_schema` — all required fields present
- `test_to_custom_param_normalized_default` — default is normalized
- `test_sc_read_expr_marker` — contains `IMAG_CUSTOMBUS:N`
- `test_sc_read_expr_lin` — uses `linlin`
- `test_sc_read_expr_exp` — uses `linexp`

**Verification:**
```bash
python -m pytest tests/test_imaginarium_custom_params.py -v
```

---

## Phase 2: Update generate_json + Tests

**File: `imaginarium/methods/base.py`**

Change `MethodTemplate.generate_json()` signature:
```python
def generate_json(
    self,
    display_name: str,
    synthdef_name: str,
    params: Optional[Dict[str, float]] = None,
) -> dict:
```

Add default implementation that:
1. Takes first 5 axes from `self.definition.param_axes`
2. Calls `axis.to_custom_param(baked_value)` for each
3. Adds placeholders for unused slots (up to 5 total)
4. Returns complete JSON config

**Tests to add:**
- `test_generate_json_has_5_custom_params`
- `test_generate_json_placeholder_format`
- `test_generate_json_baked_defaults`

**Verification:**
```bash
python -m pytest tests/test_imaginarium_custom_params.py -v
```

---

## Phase 3: dark_pulse Reference Implementation + Tests

**File: `imaginarium/methods/subtractive/dark_pulse.py`**

Update each `ParamAxis` with:
- `label` — 3-char uppercase (e.g., "WID", "PWM", "RAT")
- `tooltip` — non-empty description
- `unit` — where applicable (e.g., "Hz")

Update `generate_synthdef()`:
- Replace baked literals with `axis.sc_read_expr()` calls
- Ensure all 5 axes read from customBus0-4

Update `generate_json()`:
- Call parent implementation or build custom_params array

**Tests to add:**
- `test_dark_pulse_synthdef_has_markers` — all 5 IMAG_CUSTOMBUS markers present
- `test_dark_pulse_json_custom_params` — 5 entries with valid schema

**Verification:**
```bash
python -m pytest tests/test_imaginarium_custom_params.py -v
```

---

## Phase 4: Validator + Tests

**File: `imaginarium/validate_methods.py`** (new)

Validator checks per method:
1. Axis metadata (R1, R10, R11) — label format, tooltip non-empty
2. Curve safety (R9) — exp requires positive min/max
3. Round-trip tolerance (R7) — normalize/denormalize precision
4. JSON generation (R3, R8, R13) — 5 entries, proper schema
5. SynthDef wiring (R2, R12) — IMAG_CUSTOMBUS markers present

CLI: `python -m imaginarium.validate_methods`

**Tests to add:**
- `test_validator_passes_valid_method`
- `test_validator_catches_bad_label`
- `test_validator_catches_empty_tooltip`
- `test_validator_catches_missing_marker`

**Verification:**
```bash
python -m imaginarium.validate_methods
python -m pytest tests/test_imaginarium_custom_params.py -v
```

---

## Phase 5: Update Remaining 13 Methods

**Files:**
- `imaginarium/methods/subtractive/bright_saw.py`
- `imaginarium/methods/subtractive/supersaw.py`
- `imaginarium/methods/subtractive/noise_filtered.py`
- `imaginarium/methods/fm/simple_fm.py`
- `imaginarium/methods/fm/feedback_fm.py`
- `imaginarium/methods/fm/ratio_stack.py`
- `imaginarium/methods/fm/ring_mod.py`
- `imaginarium/methods/fm/hard_sync.py`
- `imaginarium/methods/physical/karplus.py`
- `imaginarium/methods/physical/modal.py`
- `imaginarium/methods/physical/bowed.py`
- `imaginarium/methods/physical/formant.py`
- `imaginarium/methods/spectral/additive.py`

Same pattern as dark_pulse:
1. Add label/tooltip/unit to each ParamAxis
2. Update generate_synthdef() to use sc_read_expr()
3. Update generate_json() to build custom_params

**Tests to add:**
- `test_all_methods_pass_validator`

**Verification:**
```bash
python -m imaginarium.validate_methods
```

---

## Phase 6: Integration Gate

**File: `imaginarium/cli.py`** (or wherever generate command lives)

Add validation gate before generation:
```python
from .validate_methods import validate_all_methods

def generate_command(...):
    passed, failed, results = validate_all_methods()
    if failed > 0:
        print("Generation blocked: methods non-compliant")
        return 1
    # ... proceed with generation
```

**Tests to add:**
- `test_generation_blocked_on_invalid_method`

**Verification:**
```bash
python -m imaginarium generate --help
# Intentionally break a method, verify generation blocked
```

---

## Success Criteria

- [ ] `python -m pytest tests/test_imaginarium_custom_params.py` — all pass
- [ ] `python -m imaginarium.validate_methods` — 14/14 pass
- [ ] Generated pack JSON has exactly 5 `custom_params` per generator
- [ ] P1–P5 sliders affect sound (IMAG_CUSTOMBUS markers wired)
- [ ] Default slider positions reproduce baked sound
- [ ] Generation blocked when any method non-compliant

---

## Files Changed Summary

| File | Change |
|------|--------|
| `imaginarium/methods/base.py` | Extend ParamAxis, update generate_json signature |
| `imaginarium/validate_methods.py` | New validator |
| `imaginarium/cli.py` | Add validation gate |
| `imaginarium/methods/subtractive/dark_pulse.py` | Reference impl |
| `imaginarium/methods/subtractive/bright_saw.py` | Labels + bus reads |
| `imaginarium/methods/subtractive/supersaw.py` | Labels + bus reads |
| `imaginarium/methods/subtractive/noise_filtered.py` | Labels + bus reads |
| `imaginarium/methods/fm/simple_fm.py` | Labels + bus reads |
| `imaginarium/methods/fm/feedback_fm.py` | Labels + bus reads |
| `imaginarium/methods/fm/ratio_stack.py` | Labels + bus reads |
| `imaginarium/methods/fm/ring_mod.py` | Labels + bus reads |
| `imaginarium/methods/fm/hard_sync.py` | Labels + bus reads |
| `imaginarium/methods/physical/karplus.py` | Labels + bus reads |
| `imaginarium/methods/physical/modal.py` | Labels + bus reads |
| `imaginarium/methods/physical/bowed.py` | Labels + bus reads |
| `imaginarium/methods/physical/formant.py` | Labels + bus reads |
| `imaginarium/methods/spectral/additive.py` | Labels + bus reads |
| `tests/test_imaginarium_custom_params.py` | New test file |

**Total: 18 files** (3 infra + 14 methods + 1 test)
