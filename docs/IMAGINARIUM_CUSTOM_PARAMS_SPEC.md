# Imaginarium Custom Params Spec v1.2 (FROZEN)

*P1–P5 Parameter Support for Generated Packs*
*December 2025*

---

## Status

|         |                 |
| ------- | --------------- |
| Version | v1.2            |
| Status  | **FROZEN**      |
| Author  | Gareth + Claude |

---

## Problem

Generated Imaginarium packs have non-functional P1–P5 sliders because:

1. JSON `custom_params` is empty or incomplete
2. SynthDefs bake parameter values as literals instead of reading `customBus0-4`

Users cannot tweak generated sounds — sliders do nothing.

---

## Goals

| ID | Goal                                                |
| -- | --------------------------------------------------- |
| G1 | Generated packs have functional P1–P5 sliders       |
| G2 | Slider defaults reproduce the generated/baked sound |
| G3 | New methods cannot ship without compliant params    |
| G4 | Minimal changes to existing architecture            |

---

## Non-Goals

* Changing which parameters each method exposes
* Adding more than 5 custom params
* UI changes to Noise Engine

---

## Requirements

| ID  | Requirement                                                                               |
| --- | ----------------------------------------------------------------------------------------- |
| R1  | Every exposed `ParamAxis` must have `label` (3-char), `tooltip`, `unit`                   |
| R2  | Each exposed axis **must be wired** to `customBus0..N-1` using `ParamAxis.sc_read_expr()` |
| R3  | `generate_json()` outputs `custom_params` array of **exactly 5** entries                  |
| R4  | JSON defaults are normalized (0–1) versions of baked values                               |
| R5  | Validator catches non-compliant methods before generation                                 |
| R6  | Validator is integrated into `generate.py` as a hard gate                                 |
| R7  | `denormalize()` exists and round-trips with `normalize()` (within tolerance)              |
| R8  | Placeholder `custom_params` entries (unused slots) follow **GENERATOR_SPEC.md schema**    |
| R9  | `curve="exp"` requires `min_val > 0` and `max_val > 0`                                    |
| R10 | `label` is exactly 3 chars, uppercase A–Z/0–9, unique per method                          |
| R11 | Tooltip is **required non-empty** for exposed axes                                        |
| R12 | Validator checks wiring via **helper marker tokens** (not free-form SC parsing)           |
| R13 | Custom param `key` = `axis.name` for exposed axes (stable, no index prefix)               |

---

## Design

### ParamAxis Extensions

```python
@dataclass
class ParamAxis:
    # Existing
    name: str
    min_val: float
    max_val: float
    default: float
    curve: str = "lin"

    # Metadata (R1, R10, R11)
    label: str = ""      # 3-char, e.g., "WID"
    tooltip: str = ""    # non-empty for exposed axes
    unit: str = ""       # may be empty for unitless params

    # Helpers (R4, R7, R13)
    def normalize(self, value: float) -> float: ...
    def denormalize(self, norm: float) -> float: ...
    def to_custom_param(self, baked_value: float) -> dict: ...
    def sc_read_expr(self, bus_name: str, axis_index: int) -> str: ...
```

### Curve Math (Normative)

All curves must clamp inputs safely:

* Clamp baked `value` into `[min,max]` before `normalize()`
* Clamp `norm` into `[0,1]` before `denormalize()`

#### `lin`

* `denormalize(n) = min + n*(max-min)`
* `normalize(v) = (v-min)/(max-min)`

#### `exp` (R9 constraints apply: min>0, max>0)

* `denormalize(n) = min * (max/min) ** n`
* `normalize(v) = log(v/min) / log(max/min)`

### SC Mapping (Explicit)

For each axis, SC reads the normalized 0–1 bus and maps it to actual units:

| Curve | SC Expression                       |
| ----- | ----------------------------------- |
| `lin` | `In.kr(bus).linlin(0, 1, min, max)` |
| `exp` | `In.kr(bus).linexp(0, 1, min, max)` |

> `ParamAxis.sc_read_expr()` must generate the appropriate expression based on `curve`.

### Helper Marker Tokens (Wiring Validation)

To avoid brittle free-form scanning, `sc_read_expr()` must emit a deterministic marker token per axis that the validator can check.

**Marker format (exact):**

```
/// IMAG_CUSTOMBUS:<axis_index>
```

Example for axis 0:

```supercollider
/// IMAG_CUSTOMBUS:0
pw = In.kr(customBus0).linlin(0, 1, 0.1, 0.9);
```

Validator rule: for N exposed axes, SynthDef source must contain markers:

* `IMAG_CUSTOMBUS:0` … `IMAG_CUSTOMBUS:N-1`

This validates:

* the method used the helper for each axis
* each axis index is wired

---

## JSON Output

### Exposed Axis Entry (GENERATOR_SPEC.md compliant)

`ParamAxis.to_custom_param(baked_value)` produces:

```python
def to_custom_param(self, baked_value: float) -> dict:
    return {
        "key": self.name,           # R13: use axis.name directly
        "label": self.label,
        "tooltip": self.tooltip,
        "default": self.normalize(baked_value),
        "min": 0.0,
        "max": 1.0,
        "curve": "lin",
        "unit": self.unit,
    }
```

Example output:

```json
{
  "key": "pulse_width",
  "label": "WID",
  "tooltip": "Base pulse width",
  "default": 0.42,
  "min": 0.0,
  "max": 1.0,
  "curve": "lin",
  "unit": ""
}
```

Rules:

* `key` = `axis.name` (stable, unique within method) (R13)
* `default` is normalized: `axis.normalize(baked_value)` (R4)
* `min=0.0`, `max=1.0`, `curve="lin"` in JSON **always** (UI sliders operate in normalized space)
* `unit` may be `""` for unitless axes

### Placeholder Entry (Unused Slot) — Full Schema

For unused slots i = N..4:

```json
{
  "key": "unused_3",
  "label": "---",
  "tooltip": "",
  "default": 0.5,
  "min": 0.0,
  "max": 1.0,
  "curve": "lin",
  "unit": ""
}
```

Rules:

* `key` is `f"unused_{i}"` where `i` is the slot index (0–4)
* `default` fixed at `0.5`
* `label` = `"---"` and `tooltip` = `""`

### Always 5 Params (R3)

`custom_params` must always be length **5**:

* first N are real axes (N = min(len(param_axes), 5))
* remaining slots are placeholders

### Base `generate_json()` Implementation

```python
def generate_json(
    self,
    display_name: str,
    synthdef_name: str,
    params: Optional[Dict[str, float]] = None,
) -> dict:
    custom_params = []
    axes = self.definition.param_axes[:5]
    
    # Exposed axes
    for axis in axes:
        baked = params.get(axis.name, axis.default) if params else axis.default
        custom_params.append(axis.to_custom_param(baked))
    
    # Placeholders for unused slots
    for i in range(len(axes), 5):
        custom_params.append({
            "key": f"unused_{i}",
            "label": "---",
            "tooltip": "",
            "default": 0.5,
            "min": 0.0,
            "max": 1.0,
            "curve": "lin",
            "unit": "",
        })
    
    return {
        "name": display_name,
        "synthdef": synthdef_name,
        "custom_params": custom_params,
        "output_trim_db": -6.0,
        "midi_retrig": False,
        "pitch_target": None,
    }
```

---

## Shared Baked Values (G2)

The generation pipeline must ensure the **same baked values** are used for:

* SynthDef construction (as the target default sound through bus mapping)
* JSON `custom_params[].default` (normalized)

**Implementation:** `candidate.params` is the single source of truth.
Verification confirms no second sampling/recomputation occurs.

---

## Validator

**File:** `imaginarium/validate_methods.py`

Per-method checks:

### 1) Axis metadata (R1, R10, R11)

For each exposed axis (up to 5):

* `label` matches `[A-Z0-9]{3}`
* `label` unique within method
* `tooltip` non-empty
* `unit` allowed empty

### 2) Curve safety (R9)

* `min_val < max_val`
* if `curve=="exp"` then `min_val>0` and `max_val>0`

### 3) Round-trip tolerance (R7)

For each exposed axis, test representative values: `min`, `max`, `default`.

Tolerances:

* `lin`: absolute tolerance `1e-6 * (max-min)`
* `exp`: relative tolerance `1e-6`

### 4) JSON generation (R3, R8, R13)

* `custom_params` length is exactly 5
* For i < N:
  * required fields exist: `key,label,tooltip,default,min,max,curve,unit`
  * `key` equals `axis.name`
  * `default` within `[0,1]`
  * `min==0.0`, `max==1.0`, `curve=="lin"`
* For i >= N:
  * placeholder schema exactly matches:
    * `key == f"unused_{i}"`
    * `label == "---"`
    * `tooltip == ""`
    * `default == 0.5`
    * `min==0.0`, `max==1.0`, `curve=="lin"`, `unit==""`

### 5) SynthDef wiring via helper markers (R2, R12)

* `generate_synthdef()` output must contain markers:
  * `IMAG_CUSTOMBUS:0..N-1`
* Absence of any marker fails validation.

**Output:**

* per-method pass/fail + specific failures
* exit code 0 = all pass, 1 = any fail

---

## Integration Gate (R6)

`imaginarium/generate.py` must run the validator before generation:

* any failure aborts generation with clear report

---

## Phases

### Phase 1: Infrastructure

Update `imaginarium/methods/base.py`:

* Add `label`, `tooltip`, `unit` fields to `ParamAxis`
* Implement `normalize()` + `denormalize()` with curve clamping
  * `lin`: standard linear
  * `exp`: enforce `min_val > 0`, `max_val > 0`
* Implement `to_custom_param(baked_value)` using `key=self.name`
* Implement `sc_read_expr(bus_name, axis_index)` emitting:
  * `/// IMAG_CUSTOMBUS:<axis_index>` marker
  * `linlin` or `linexp` based on curve
* Default `generate_json()` builds 5 entries with placeholders

**Files:** `imaginarium/methods/base.py`

### Phase 2: Shared baked-default plumbing

* Ensure `candidate.params` feeds both `generate_synthdef()` and `generate_json()`
* Pass `params=candidate.params` to `generate_json()` call in export.py

**Files:** `imaginarium/export.py` (1 line change)

### Phase 3: Validator

* Create `imaginarium/validate_methods.py` with all checks
* Run against all methods — expect 14 failures

**Files:** `imaginarium/validate_methods.py` (new)

### Phase 4: Reference Implementation

* Update `dark_pulse.py`:
  * Add axis labels/tooltips/units
  * Replace baked literals with `sc_read_expr()` calls
* Run validator — expect 1 pass, 13 fail
* Manual test in Noise Engine: P1–P5 affect sound, defaults match baked

**Files:** `imaginarium/methods/subtractive/dark_pulse.py`

### Phase 5: Roll Out Remaining Methods

* Fix remaining 13 methods until validator passes all
* Batch by family: subtractive (3) → fm (5) → physical (4) → spectral (1)

**Files:** 13 method files

### Phase 6: Integration Gate

* Wire validator into `generate.py` as hard gate
* Test: intentionally broken method blocks generation

**Files:** `imaginarium/generate.py`

---

## Verification

| Phase | Verification                                                   |
| ----- | -------------------------------------------------------------- |
| 1     | Unit tests for normalize/denormalize round-trip per curve      |
| 2     | Assert: same `candidate.params` used for JSON + synthdef paths |
| 3     | Validator runs, reports failures with actionable messages      |
| 4     | Validator: 1 pass; Manual: sliders work + defaults match       |
| 5     | Validator: 14 pass                                             |
| 6     | `generate` fails on intentionally broken method                |

---

## Success Criteria

* [ ] `python -m imaginarium.validate_methods` exits 0
* [ ] Generated pack JSON has exactly 5 `custom_params` entries per generator
* [ ] P1–P5 sliders audibly affect sound for exposed axes
* [ ] Default slider positions reproduce original generated sound
* [ ] Any non-compliant method blocks generation

---

## Files Changed

| File                                                | Change                                 |
| --------------------------------------------------- | -------------------------------------- |
| `imaginarium/methods/base.py`                       | ParamAxis extensions + default methods |
| `imaginarium/export.py`                             | Pass params to generate_json           |
| `imaginarium/validate_methods.py`                   | New validator script                   |
| `imaginarium/generate.py`                           | Validator gate                         |
| `imaginarium/methods/subtractive/dark_pulse.py`     | Reference impl                         |
| `imaginarium/methods/subtractive/bright_saw.py`     | Labels + bus reads                     |
| `imaginarium/methods/subtractive/supersaw.py`       | Labels + bus reads                     |
| `imaginarium/methods/subtractive/noise_filtered.py` | Labels + bus reads                     |
| `imaginarium/methods/fm/simple_fm.py`               | Labels + bus reads                     |
| `imaginarium/methods/fm/feedback_fm.py`             | Labels + bus reads                     |
| `imaginarium/methods/fm/ratio_stack.py`             | Labels + bus reads                     |
| `imaginarium/methods/fm/ring_mod.py`                | Labels + bus reads                     |
| `imaginarium/methods/fm/hard_sync.py`               | Labels + bus reads                     |
| `imaginarium/methods/physical/karplus.py`           | Labels + bus reads                     |
| `imaginarium/methods/physical/modal.py`             | Labels + bus reads                     |
| `imaginarium/methods/physical/bowed.py`             | Labels + bus reads                     |
| `imaginarium/methods/physical/formant.py`           | Labels + bus reads                     |
| `imaginarium/methods/spectral/additive.py`         | Labels + bus reads                     |

**Total: 17 files** (4 infra + 14 methods)

---

## Estimated Effort

| Phase | Sessions     |
| ----- | ------------ |
| 1-4   | 1 session    |
| 5     | 1-2 sessions |
| 6     | 15 min       |

**Total: 2-3 sessions**
