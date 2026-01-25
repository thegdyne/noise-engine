# Test Suite Rebuild Plan

## Status: DRAFT
## Author: Claude + User
## Date: 2025-01-25
## Related: BUS_UNIFICATION_ROLLOUT_PLAN.md, FROZEN_SPEC (Bus Unification v4)

---

## 1. Objective

Delete all existing tests touching the unified bus system and recreate from the frozen specification acceptance criteria. Clean slate approach prevents cascading test fixes that plagued the v1.3 attempt.

---

## 2. Rationale

The v1.3 attempt failed partly due to:
- Tests hardcoded to 71-bus layout
- Target key format assumptions baked into assertions
- Cascading fixes where fixing one test broke others
- Time spent patching old tests instead of building new system

Fresh tests from spec acceptance criteria are:
- Aligned to the 149-bus target state
- Based on explicit behavioral contracts
- Easier to maintain long-term

---

## 3. Phase A: Delete All Affected Tests

**Execute BEFORE any implementation work begins.**

**Delete these files:**

| File | Reason |
|------|--------|
| `tests/test_boid_bus.py` | Hardcoded 71-bus layout, UNIFIED_BUS constants |
| `tests/test_mod_routing.py` | Target key format tied to old system |
| `tests/test_mod_route_sync.py` | Mod routing state serialization |
| `tests/test_channel_fx_modulation.py` | Channel/FX target routing |
| `tests/test_presets_phase4.py` | Preset mod routing |
| `tests/conftest.py` | PyQt5 mock infrastructure |
| `tests/test_mod_architecture.py` | Quadrature config tests |

**Verification:**
```bash
rm tests/test_boid_bus.py
rm tests/test_mod_routing.py
rm tests/test_mod_route_sync.py
rm tests/test_channel_fx_modulation.py
rm tests/test_presets_phase4.py
rm tests/conftest.py
rm tests/test_mod_architecture.py

# Remaining tests should still pass
pytest tests/
```

**Commit:** `test: Delete tests tied to 71-bus system (clean slate for rebuild)`

---

## 4. Phase B: Recreate Tests from Frozen Spec

**Execute AFTER implementation is complete and manually verified.**

### New Test Files

| File | Covers | Spec Sections |
|------|--------|---------------|
| `tests/conftest.py` | PyQt5 mock infrastructure, common fixtures | — |
| `tests/test_unified_bus.py` | Target set, indexing, mix exclusion, defaults, curve constraints | A, B, C, D, G |
| `tests/test_unified_routing.py` | Apply tick atomicity, FIFO precedence, boid snapshot | E, F |
| `tests/test_generator_switching.py` | Legacy↔unified routing, switch timing, handoff | H |
| `tests/test_preset_loading.py` | Keyed presets, legacy array mapping, mix endpoints | I, J |
| `tests/test_mod_architecture.py` | Quadrature config validation | — |

---

## 5. Acceptance Criteria to Implement

### (A) Target set and canonical indexing
- `TargetMeta.size == 149`
- `BusRegistry.keyByIndex.size == 149`
- Indices are exactly `0..148`, no duplicates
- Representative index checks:
  - `indexByKey['gen_1_freq'] == 0`
  - `indexByKey['gen_8_decay'] == 39`
  - `indexByKey['gen_1_custom0'] == 40`
  - `indexByKey['gen_8_custom4'] == 79`
  - `indexByKey['mod_1_p0'] == 80`
  - `indexByKey['mod_4_p6'] == 107`
  - `indexByKey['chan_1_echo'] == 108`
  - `indexByKey['chan_8_pan'] == 131`
  - `indexByKey['fx_heat_drive'] == 132`
  - `indexByKey['fx_dualFilter_harmonics'] == 148`

### (B) Mix exclusion + mix control availability
- `fx_heat_mix` and `fx_dualFilter_mix` absent from `TargetMeta`
- `/noise/bus/base "fx_heat_mix" 0.5` produces `ERR_UNKNOWN_TARGET`
- `/noise/fx/heat/mix 0.5` updates heat mix successfully
- `/noise/fx/dualFilter/mix 0.5` updates dualFilter mix successfully

### (C) Defaults and initialization
- After initialization (no UI updates):
  - `bus(gen_1_cutoff)` ≈ 16000
  - `bus(gen_1_attack)` ≈ 0.0001
  - `bus(gen_1_custom0)` ≈ 0.5

### (D) Generator custom param curve constraint
- For every `slot ∈ 1..8` and `k ∈ 0..4`:
  - `TargetMeta['gen_<slot>_custom<k>'].curve == \lin`
  - `minReal == 0.0`, `maxReal == 1.0`, `defaultReal == 0.5`

### (E) Apply tick atomicity and queue boundary
- Event enqueued before tick Step 0 swap → bus updates same tick
- Event enqueued after Step 0 swap → bus updates next tick
- FIFO precedence: later events override earlier for same target

### (F) Boid snapshot atomicity + contribution semantics
- Mid-tick boid update uses previous snapshot; next tick reflects new values
- `boidContribution = boidOffset * boidScale`
- If `boidScale = 0.0`, contribution is zero regardless of offset

### (G) Exponential curve denormalization safety
- `normToReal(n=0.0)` returns finite value in valid range
- `normToReal(n=1.0)` returns finite value in valid range
- Out-of-range norm (e.g., -0.1 or 1.1) still yields finite real after clamp

### (H) Generator routing rollout and switching timing
- With `genUnifiedSlots = {}`: generators read legacy buses
- With slot in `genUnifiedSlots`: slot reads unified buses
- Switch executes within one tick callback (bounded gap)
- Post-switch values match pre-switch within epsilon

### (I) Keyed preset application
- Preset `{ key: realValue }` restores unified targets via `/noise/bus/baseReal`
- Mix params restored via dedicated endpoints

### (J) Legacy preset array mapping (71-element)
- Index 0-27 → mod params
- Index 28-51 → channel params
- Index 52-70 → FX params (including mix → dedicated endpoints)
- No values silently dropped

---

## 6. Test Implementation Notes

### conftest.py
```python
# Minimal PyQt5 stub for ModRoutingState tests
class QObjectStub:
    def __init__(self, parent=None):
        pass

def pyqtSignal_stub(*args, **kwargs):
    signal = MagicMock()
    signal.emit = MagicMock()
    signal.connect = MagicMock()
    return signal

# Set up before any imports
sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtCore'] = mock_qt_core
# etc.
```

### test_unified_bus.py structure
```python
class TestTargetSetAndIndexing:
    """Spec section A"""
    def test_target_count_is_149(self): ...
    def test_indices_contiguous_0_to_148(self): ...
    def test_gen_core_param_indices(self): ...
    def test_gen_custom_param_indices(self): ...
    def test_mod_slot_indices(self): ...
    def test_channel_indices(self): ...
    def test_fx_indices(self): ...

class TestMixExclusion:
    """Spec section B"""
    def test_heat_mix_not_in_target_meta(self): ...
    def test_dualfilter_mix_not_in_target_meta(self): ...
    def test_heat_mix_endpoint_works(self): ...
    def test_dualfilter_mix_endpoint_works(self): ...

# etc.
```

---

## 7. Success Criteria

- [ ] All 7 test files deleted in Phase A
- [ ] `pytest tests/` passes after Phase A (remaining tests)
- [ ] All 6 new test files created in Phase B
- [ ] `pytest tests/` all pass after Phase B
- [ ] Coverage includes all 149 targets
- [ ] Edge cases covered (NaN, out-of-range, exp overflow)

---

## 8. Rollback

- **Phase A:** `git checkout HEAD~1 -- tests/` restores deleted files
- **Phase B:** Tests are additive; delete new files if needed
