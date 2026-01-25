# Bus Unification Rollout Plan

## Status: DRAFT
## Author: Claude + User
## Date: 2025-01-25
## Base Branch: consistency

---

## 1. Objective

Expand bus unification from 71 → 149 buses, bringing generator parameters into the unified system. This eliminates parallel modulation paths and enables boid/mod-matrix control of generator params.

**Design principle:** Only modulatable parameters go through unified buses. Mix controls remain as direct UI controls (manual only, not modulatable).

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

### Target State (149-bus system)
- 149 modulatable targets in `~targetMeta`
- Mix params excluded (manual UI control only)
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

### Phase 0: Test Cleanup (Before Any Code Changes)

**Goal:** Remove tests tied to 71-bus assumptions. Clean slate prevents cascading test fixes.

**Delete ALL tests touching unified bus system:**
- `tests/test_boid_bus.py` - hardcoded 71-bus layout, UNIFIED_BUS constants
- `tests/test_mod_routing.py` - target key format tied to old system
- `tests/test_mod_route_sync.py` - mod routing state serialization
- `tests/test_channel_fx_modulation.py` - channel/FX target routing
- `tests/test_presets_phase4.py` - preset mod routing

**Keep Unchanged:**
- `tests/conftest.py` - just PyQt5 mock infrastructure
- `tests/test_mod_architecture.py` - tests quadrature config, unrelated

**Test:**
- `pytest tests/` passes with remaining tests
- No import errors from deleted files

**Rationale:** The v1.3 attempt failed partly due to cascading test fixes. Fresh tests from frozen spec acceptance criteria are cleaner than patching old assumptions.

---

### Phase 1: Expand Bus Allocation (SC only)

**Goal:** Add 80 generator target definitions without breaking anything.

**Changes:**
- `bus_unification.scd`: Add to `~targetMeta`:
  - `gen_<1-8>_freq` (8 buses)
  - `gen_<1-8>_cutoff` (8 buses)
  - `gen_<1-8>_res` (8 buses)
  - `gen_<1-8>_attack` (8 buses)
  - `gen_<1-8>_decay` (8 buses)
  - `gen_<1-8>_custom<0-4>` (40 buses)
- Update `~unifiedBusCount` from 71 → 149
- Add `~boidScales` entries for new targets (default 0 = disabled)
- Update `~boidOffsets` array size from 71 → 149

**Bus Layout (canonical - 149 buses):**

| Index | Count | Keys | Description |
|-------|-------|------|-------------|
| 0-39 | 40 | `gen_1_freq` ... `gen_8_decay` | 8 slots × 5 core params (freq, cutoff, res, attack, decay) |
| 40-79 | 40 | `gen_1_custom0` ... `gen_8_custom4` | 8 slots × 5 custom params |
| 80-107 | 28 | `mod_1_p0` ... `mod_4_p6` | 4 slots × 7 params (p0-p6) |
| 108-131 | 24 | `chan_1_echo` ... `chan_8_pan` | 8 channels × 3 params (echo, verb, pan) |
| 132 | 1 | `fx_heat_drive` | Heat drive only |
| 133 | — | *(gap)* | mix excluded - manual UI only |
| 134-139 | 6 | `fx_echo_time`, `fx_echo_feedback`, `fx_echo_tone`, `fx_echo_wow`, `fx_echo_spring`, `fx_echo_verbSend` | Echo |
| 140-142 | 3 | `fx_reverb_size`, `fx_reverb_decay`, `fx_reverb_tone` | Reverb |
| 143-149 | 7 | `fx_dualFilter_drive`, `fx_dualFilter_freq1`, `fx_dualFilter_freq2`, `fx_dualFilter_reso1`, `fx_dualFilter_reso2`, `fx_dualFilter_syncAmt`, `fx_dualFilter_harmonics` | DualFilter |
| 150 | — | *(gap)* | mix excluded - manual UI only |

**Excluded from unified buses (manual UI control only):**
- `fx_heat_mix`
- `fx_dualFilter_mix`

**Test:**
- SC boots without errors
- `~targetMeta.size` == 149
- Existing targets still work (mod matrix, boids)
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
| freq | 400 | 20 | 8000 | exp |
| cutoff | 16000 | 20 | 16000 | exp |
| res | 1.0 | 0.1 | 1.0 | lin |
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
      \freqBus, ~busRegistry[\gen_1_freq].index,
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

### Phase 8: Recreate Tests from Frozen Spec

**Goal:** Comprehensive test coverage matching spec acceptance criteria.

**New test files:**

| File | Covers | Spec Sections |
|------|--------|---------------|
| `tests/test_unified_bus.py` | Target set, indexing, mix exclusion, defaults, curve constraints | A, B, C, D, G |
| `tests/test_unified_routing.py` | Apply tick atomicity, FIFO precedence, boid snapshot | E, F |
| `tests/test_generator_switching.py` | Legacy↔unified routing, switch timing, handoff | H |
| `tests/test_preset_loading.py` | Keyed presets, legacy array mapping, mix endpoints | I, J |

**Acceptance criteria to implement as tests:**

- **(A)** Target set: 149 targets, indices 0-148, canonical key→index mapping
- **(B)** Mix exclusion: `fx_heat_mix` / `fx_dualFilter_mix` not in targetMeta, dedicated OSC endpoints work
- **(C)** Defaults: bus values match spec after initialization
- **(D)** Custom param constraints: curve=lin, range=0-1, default=0.5
- **(E)** Apply tick atomicity: queue boundary, FIFO precedence
- **(F)** Boid snapshot: double-buffer swap, contribution formula
- **(G)** Exp curve safety: normToReal/realToNorm produce finite values
- **(H)** Generator routing: instantiation-time switching, bounded gap
- **(I)** Keyed preset load: unified + mix params restored correctly
- **(J)** Legacy preset mapping: 71-element array → correct targets

**Test:**
- `pytest tests/` all pass
- Coverage includes all 149 targets
- Edge cases from spec covered (NaN, out-of-range, exp overflow)

---

## 5. File Change Summary

| File | Phase | Changes |
|------|-------|---------|
| `tests/test_boid_bus.py` | 0 | DELETE |
| `tests/test_mod_routing.py` | 0 | DELETE |
| `tests/test_mod_route_sync.py` | 0 | DELETE |
| `tests/test_channel_fx_modulation.py` | 0 | DELETE |
| `tests/test_presets_phase4.py` | 0 | DELETE |
| `supercollider/core/bus_unification.scd` | 1, 2, 7 | Expand targetMeta, modTargetState, boidScales |
| `supercollider/core/bus_unification_osc.scd` | 4 | Verify/add gen param handlers |
| `supercollider/core/helpers.scd` | 3, 5 | Wire generators to unified buses |
| `supercollider/core/buses.scd` | 6 | Remove legacy gen param buses |
| `supercollider/core/mod_apply.scd` | 6 | Remove or gut |
| `src/gui/*.py` (gen controls) | 4, 5 | Route through /noise/bus/base |
| `src/utils/boid_bus.py` | 7 | Update zone mapping for gen targets |
| `tests/test_unified_bus.py` | 8 | NEW - target set, indexing, defaults |
| `tests/test_unified_routing.py` | 8 | NEW - apply tick, boid snapshot |
| `tests/test_generator_switching.py` | 8 | NEW - routing switch procedure |
| `tests/test_preset_loading.py` | 8 | NEW - preset application |

---

## 6. Rollback Strategy

Each phase is independently revertable:

- **Phase 0:** `git checkout` deleted test files from previous commit
- **Phase 1-2:** Revert SC changes, 71-bus system restored
- **Phase 3:** Revert helpers.scd, slot 1 uses legacy
- **Phase 4-5:** Revert Python + SC, all slots use legacy
- **Phase 6:** Cannot easily rollback - don't merge until confident
- **Phase 7:** Set boid scales to 0, effectively disabled
- **Phase 8:** Tests are additive, can delete if needed

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

## 8. Design Decisions

1. **Normalization:** Normalized (0-1) over OSC, real values in presets
   - Python sends normalized 0-1 to SC
   - SC denormalizes using `~targetMeta` ranges in apply tick
   - Presets store real values (human-readable: 440 Hz, not 0.23)
   - On preset load: convert real → normalized
   - On preset save: convert normalized → real
   - **Rationale:** Consistent with existing bus_unification (71 targets already use normalized). Modulation math simpler when everything is 0-1 scale.

2. **Curve handling:** SC side (in apply tick)
   - `~targetMeta` stores curve type (lin/exp) per target
   - Apply tick applies curve when denormalizing
   - Python stays simple - just sends linear 0-1
   - **Rationale:** Single source of truth. Current mod_apply already does this. Easier to maintain in one place.

3. **Preset format:** No migration needed
   - Presets continue to store real values
   - Conversion happens at load/save boundary
   - Existing presets work unchanged
   - **Rationale:** Presets remain human-readable and backward compatible.

4. **Custom param ranges:** Keep 0-1 for all
   - All custom params use normalized 0-1 range
   - Generators that need different ranges (e.g., 0-7 for harmonics) map internally in SynthDef
   - **Rationale:** Keeps bus system uniform. Complexity stays in generators where it's generator-specific anyway.

---

## 9. Success Criteria

- [ ] 149 buses allocated and stable
- [ ] All gen params controllable via mod matrix
- [ ] Boid modulation works on gen params
- [ ] No increase in CPU usage (should decrease)
- [ ] Presets load/save correctly
- [ ] No audio glitches during normal operation
- [ ] mod_apply.scd removed or inactive
