# Bus Unification Rollout Plan

## Status: DRAFT
## Author: Claude + User
## Date: 2025-01-25
## Base Branch: consistency

---

## 1. Objective

Expand bus unification from 71 → 151 buses, bringing generator parameters into the unified system. This eliminates parallel modulation paths and enables boid/mod-matrix control of generator params.

---

## 2. Current State

### What Works (71-bus system)
- 500Hz apply tick with queue-based updates
- Mod routing with full parameter set (depth, amount, offset, polarity, invert)
- Boid integration with per-target scales
- Targets: mod slots (28), channels (24), FX (19)

### What's Separate (to unify)
- Generator params use private buses (`~genParams[slot]`)
- `mod_apply.scd` uses 40 synths for gen param modulation
- UI writes directly to `~genUserParams` buses

### Target State (151-bus system)
- All 151 targets in `~targetMeta`
- Generators read from unified buses
- Single apply tick handles everything
- `mod_apply.scd` retired

---

## 3. Lessons from v1.3 Attempt

| Mistake | Prevention |
|---------|------------|
| 1700+ line rewrite in one commit | Incremental phases, each testable |
| SC var declarations scattered | Strict code review checklist |
| IdentityDictionary method dispatch bugs | Use standalone `~functions` |
| CPU overload with boids | Test with boids enabled at each phase |
| Cascading fix commits | Don't merge until phase is stable |

---

## 4. Rollout Phases

### Phase 1: Expand Bus Allocation (SC only)

**Goal:** Add 80 generator target definitions without breaking anything.

**Changes:**
- `bus_unification.scd`: Add to `~targetMeta`:
  - `gen_<1-8>_frequency` (8 buses)
  - `gen_<1-8>_cutoff` (8 buses)
  - `gen_<1-8>_resonance` (8 buses)
  - `gen_<1-8>_attack` (8 buses)
  - `gen_<1-8>_decay` (8 buses)
  - `gen_<1-8>_custom<0-4>` (40 buses)
- Update `~unifiedBusCount` from 71 → 151
- Add `~boidScales` entries for new targets (default 0 = disabled)
- Update `~boidOffsets` array size from 71 → 151

**Bus Layout (new):**
```
Block A:  0-39   gen_<slot>_<param>     (8 slots × 5 core params)
Block B: 40-79   gen_<slot>_custom<n>   (8 slots × 5 custom params)
Block C: 80-107  mod_<slot>_p<n>        (4 slots × 7 params) [existing]
Block D: 108-131 chan_<ch>_<param>      (8 channels × 3 params) [existing]
Block E: 132-133 fx_heat_*              (2) [existing]
Block F: 134-139 fx_echo_*              (6) [existing]
Block G: 140-142 fx_verb_*              (3) [existing]
Block H: 143-150 fx_fb_*                (8) [existing]
```

**Test:**
- SC boots without errors
- `~targetMeta.size` == 151
- Existing 71 targets still work (mod matrix, boids)
- No CPU increase

**Risk:** Bus index collision with existing `~genParams`. Mitigation: unified buses are at index 1000+, gen params are dynamically allocated (typically < 500).

---

### Phase 2: Initialize Generator Target State

**Goal:** Populate `~modTargetState` for gen targets with correct defaults.

**Changes:**
- `bus_unification.scd`: In `~setupBusUnification`, after allocating buses:
  - Create Bus objects for all 80 gen targets
  - Add to `~busRegistry`
  - Initialize `~modTargetState[key].baseValue` with defaults from `~targetMeta`
  - Set initial bus values

**Defaults (from buses.scd):**
| Param | Default | Min | Max | Curve |
|-------|---------|-----|-----|-------|
| frequency | 400 | 20 | 8000 | exp |
| cutoff | 16000 | 20 | 16000 | exp |
| resonance | 1.0 | 0.1 | 1.0 | lin |
| attack | 0.0001 | 0.0001 | 2.0 | exp |
| decay | 1.0 | 0.01 | 10.0 | exp |
| custom0-4 | 0.5 | 0 | 1 | lin |

**Test:**
- `~modTargetState[\gen_1_cutoff].baseValue` == 16000
- `~busRegistry[\gen_1_cutoff].getSynchronous` == 16000
- Apply tick runs without errors
- Existing functionality unchanged

---

### Phase 3: Wire One Generator to Unified Buses

**Goal:** Prove the concept with slot 1 only.

**Changes:**
- `helpers.scd`: Modify `~startGenerator` for slot 1 only:
  ```supercollider
  if(slotID == 1, {
      // Use unified buses
      \freqBus, ~busRegistry[\gen_1_frequency].index,
      \cutoffBus, ~busRegistry[\gen_1_cutoff].index,
      // ... etc
  }, {
      // Use legacy ~genParams
      \freqBus, params[\frequency].index,
      // ...
  });
  ```

**Test:**
- Load generator in slot 1
- Verify audio works
- Verify UI knob changes work (need Phase 4 for this)
- Slots 2-8 still use legacy path

**Note:** UI won't control slot 1 yet - that's Phase 4.

---

### Phase 4: Route Slot 1 UI Through Unified System

**Goal:** UI writes to unified buses via OSC for slot 1.

**Changes:**
- Python side: When setting gen params for slot 1:
  - Send `/noise/bus/base gen_1_cutoff <normalized_value>`
  - Instead of direct `/noise/gen/1/cutoff <real_value>`

- `bus_unification_osc.scd`: Add OSC handlers if not present:
  - `/noise/bus/base [targetKey, value]` - already exists
  - Verify it handles gen_* keys correctly

- Value normalization: Python must send normalized (0-1), SC denormalizes using `~targetMeta` ranges.

**Test:**
- Move cutoff knob for slot 1
- Verify sound changes
- Verify mod matrix can route to `gen_1_cutoff`
- Verify boids can affect `gen_1_cutoff` (if scale > 0)

---

### Phase 5: Expand to All 8 Slots

**Goal:** All generators use unified buses.

**Changes:**
- `helpers.scd`: Remove slot 1 conditional, use unified for all
- Python: Route all gen param changes through `/noise/bus/base`
- Remove legacy OSC handlers for gen params (or keep as aliases)

**Test:**
- All 8 slots work
- Preset load/save works
- Mod matrix routes to any gen param
- No audio glitches during slot changes

---

### Phase 6: Remove Legacy Systems

**Goal:** Clean up redundant code.

**Changes:**
- `buses.scd`: Remove `~genParams` and `~genUserParams` (or keep as aliases for safety)
- `mod_apply.scd`: Remove `\modRoute` synths and related code
- Keep backward-compat OSC aliases if external tools depend on them

**Test:**
- Full regression test
- Memory/CPU profiling (should be lower)
- No orphaned buses

---

### Phase 7: Enable Boid Modulation for Gen Params

**Goal:** Boids can modulate generator parameters.

**Changes:**
- `bus_unification.scd`: Set non-zero `~boidScales` for gen targets:
  ```supercollider
  ~boidScales[\gen_1_cutoff] = 0.5;  // etc
  ```
- Python boid system: Include gen targets in zone mapping

**Test:**
- Enable boids
- Verify gen params move with boid activity
- Verify no CPU overload (the v1.3 bug)
- Tune scales for musicality

---

## 5. File Change Summary

| File | Phase | Changes |
|------|-------|---------|
| `supercollider/core/bus_unification.scd` | 1, 2, 7 | Expand targetMeta, modTargetState, boidScales |
| `supercollider/core/bus_unification_osc.scd` | 4 | Verify/add gen param handlers |
| `supercollider/core/helpers.scd` | 3, 5 | Wire generators to unified buses |
| `supercollider/core/buses.scd` | 6 | Remove legacy gen param buses |
| `supercollider/core/mod_apply.scd` | 6 | Remove or gut |
| `src/gui/*.py` (gen controls) | 4, 5 | Route through /noise/bus/base |
| `src/utils/boid_bus.py` | 7 | Update zone mapping for gen targets |

---

## 6. Rollback Strategy

Each phase is independently revertable:

- **Phase 1-2:** Revert SC changes, 71-bus system restored
- **Phase 3:** Revert helpers.scd, slot 1 uses legacy
- **Phase 4-5:** Revert Python + SC, all slots use legacy
- **Phase 6:** Cannot easily rollback - don't merge until confident
- **Phase 7:** Set boid scales to 0, effectively disabled

---

## 7. Code Quality Checklist

Before merging each phase:

- [ ] All SC `var` declarations at top of function blocks
- [ ] No IdentityDictionary method calls (use standalone `~functions`)
- [ ] Boid offset array bounds checked
- [ ] CPU tested with boids enabled
- [ ] No orphaned synths or buses
- [ ] OSC handlers have error reporting
- [ ] Backward-compat aliases if removing endpoints

---

## 8. Open Questions

1. **Normalization:** Should Python always send normalized 0-1, or real values?
   - Spec says normalized, but current gen OSC uses real values
   - Decision needed before Phase 4

2. **Curve handling:** Exponential params (freq, cutoff) need special mapping
   - Apply in SC (current) or Python?
   - Decision needed before Phase 4

3. **Preset format:** Do gen param presets need migration?
   - If stored as real values, no change
   - If stored as normalized, need conversion

4. **Custom param ranges:** Are all custom params 0-1, or per-generator?
   - Current: all 0-1
   - Some generators might want different ranges

---

## 9. Success Criteria

- [ ] 151 buses allocated and stable
- [ ] All gen params controllable via mod matrix
- [ ] Boid modulation works on gen params
- [ ] No increase in CPU usage (should decrease)
- [ ] Presets load/save correctly
- [ ] No audio glitches during normal operation
- [ ] mod_apply.scd removed or inactive
