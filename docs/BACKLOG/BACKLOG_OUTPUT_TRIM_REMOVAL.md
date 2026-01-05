# Remove output_trim_db from Method Definitions

*Feasibility Investigation — No Code*

---

## Summary

**Goal:** Remove `output_trim_db` from Imaginarium method definitions and rely solely on the existing auto-trim feature (RMS-based calculation at export time).

**Feasibility:** ✅ **High** — The auto-trim feature already calculates and overwrites the method value. Removal is a simplification, not a new capability.

**Effort:** Small (1 session or less)

---

## Current State

### Where `output_trim_db` Lives Today

| Location | Current Value | Purpose |
|----------|---------------|---------|
| `methods/base.py` → `generate_json()` | `-6.0` hardcoded | Default returned by method |
| `export.py` → auto-trim | Calculated from RMS | Overwrites method default |
| Generator JSON files | Varies (-12 to +18 dB) | Runtime value sent to SC |
| Core generators (saw, drone, etc.) | **Not present** | Core gens don't have this field |
| IMAGINARIUM_SPEC.md §6.1 | `-6.0` in schema | Documentation |
| IMAGINARIUM_CUSTOM_PARAMS_SPEC.md | `-6.0` in example | Documentation |

### Current Data Flow

```
1. method.generate_json()
   └── Returns {"output_trim_db": -6.0, ...}

2. export.py auto-trim calculation
   ├── IF candidate.features.rms_db > -60:
   │   └── json_config["output_trim_db"] = TARGET_RMS - rms_db (clamped ±18dB)
   └── ELSE: keeps the method's -6.0 default

3. JSON written to pack/generators/*.json
   └── Contains final calculated output_trim_db

4. Runtime: get_generator_output_trim_db(name)
   └── Reads from loaded generator config

5. OSC: /noise/gen/trim [slot_id, trim_db]
   └── SC applies trim to slot output
```

### Key Insight

The method's hardcoded `-6.0` is **always overwritten** by auto-trim when features are valid. It only serves as a fallback when:
- RMS measurement failed (`rms_db < -60`)
- Unknown method (fallback block)

---

## Proposed Change

### Remove from Method Definitions

**Before:**
```python
def generate_json(self, display_name, synthdef_name, params=None):
    return {
        "name": display_name,
        "synthdef": synthdef_name,
        "custom_params": [...],
        "output_trim_db": -6.0,  # ← Remove this
        "midi_retrig": False,
        "pitch_target": None,
    }
```

**After:**
```python
def generate_json(self, display_name, synthdef_name, params=None):
    return {
        "name": display_name,
        "synthdef": synthdef_name,
        "custom_params": [...],
        # output_trim_db calculated by export.py based on RMS
        "midi_retrig": False,
        "pitch_target": None,
    }
```

### Update export.py to Always Set Trim

**Current:**
```python
# Only sets trim if features are valid
if candidate.features and candidate.features.rms_db > -60:
    json_config["output_trim_db"] = calculated_trim
# Otherwise keeps method's -6.0
```

**After:**
```python
# Always set trim with fallback for missing features
if candidate.features and candidate.features.rms_db > -60:
    trim = TARGET_RMS_DB - candidate.features.rms_db
    trim = max(-18.0, min(18.0, trim))
    json_config["output_trim_db"] = round(float(trim), 1)
else:
    json_config["output_trim_db"] = 0.0  # Fallback: no trim adjustment
```

---

## Files to Modify

| File | Change |
|------|--------|
| `imaginarium/methods/base.py` | Remove `output_trim_db` from `generate_json()` return |
| `imaginarium/export.py` | Add explicit fallback in else branch |
| Each method file with custom generate_json | Remove `output_trim_db` if present |
| `IMAGINARIUM_SPEC.md` §6.1 | Update to note trim is calculated, not specified |
| `IMAGINARIUM_CUSTOM_PARAMS_SPEC.md` | Update generate_json example |

**Not affected:**
- Core generators (don't have output_trim_db)
- SC side (unchanged)
- Runtime loading (unchanged)
- OSC paths (unchanged)
- `get_generator_output_trim_db()` (unchanged)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Fallback produces different sound | Low | Low | Use `0.0` (no adjustment) as fallback, same as core generators |
| Tests fail | Low | Low | Update `test_get_generator_output_trim_db_range` if needed |
| Methods override generate_json | Medium | Low | Audit all methods for custom generate_json |

### Methods to Audit

Check if any methods override `generate_json()` with custom output_trim:

```bash
grep -rn "output_trim" imaginarium/methods/
```

Based on IMAGINARIUM_CUSTOM_PARAMS_SPEC.md, the base implementation handles this centrally. Individual methods likely don't override.

---

## Decision: Fallback Value

When RMS measurement fails, what trim value should we use?

| Option | Value | Rationale |
|--------|-------|-----------|
| A | `0.0` | Unity gain, same as core generators (no adjustment) |
| B | `-6.0` | Original default, some headroom built in |
| C | Error/Fail | Force RMS measurement to succeed |

**Recommendation:** Option A (`0.0`)

Reasoning:
- Core generators work fine without output_trim
- `0.0` means "don't adjust" rather than "attenuate by 6dB"
- Simpler mental model: trim only applied when measured
- If RMS fails, something is wrong with the render anyway

---

## Benefits

1. **Simpler method definitions** — One less field to maintain
2. **Single source of truth** — All trim logic in export.py
3. **Consistency** — All generators use the same calculation
4. **Less duplication** — 14 methods × 1 hardcoded value = removed
5. **Clearer contract** — Methods don't pretend to know their loudness

---

## Success Criteria

- [ ] All generated packs have `output_trim_db` in JSON (calculated)
- [ ] No method defines `output_trim_db` in its code
- [ ] Fallback uses `0.0` when RMS unavailable
- [ ] Existing tests pass (adjust range test if needed)
- [ ] Loudness normalization still works (A/B test)

---

## Recommendation

**Proceed with implementation.**

This is a cleanup/simplification task with low risk. The auto-trim feature already does all the work — we're just removing the vestigial hardcoded value that gets overwritten anyway.

**Estimated effort:** 30-60 minutes including doc updates and testing.
