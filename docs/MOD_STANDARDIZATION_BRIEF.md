# Modulator Standardization Issue - Technical Brief

## Problem Statement

We cannot extend the mod matrix grid to include modulator cross-modulation targets because modulators lack parameter standardization. Unlike generators (which use P1-P5), each modulator type has unique parameter names, making it impossible to create a meaningful grid without knowing which modulator type is loaded in each slot.

---

## Current Architecture

### Generators (Standardized ✅)
**All generator types use the same parameter structure:**
- Common params: cutoff, resonance, frequency, attack, decay
- Custom params: P1, P2, P3, P4, P5
- **Benefit:** Mod matrix grid works regardless of which generator is loaded
- **Example:** "G3 P1" column works whether G3 has BrightSaw, SubHarm, or any other generator

### Modulators (NOT Standardized ❌)
**Each modulator type has unique parameter names:**

**LFO (13 params):**
- rate, mode, shape, pattern, rotate
- wave_1, wave_2, wave_3, wave_4
- pol_1, pol_2, pol_3, pol_4

**ARSeq+ (14 params):**
- rate, mode, clockMode
- atk_1, atk_2, atk_3, atk_4
- rel_1, rel_2, rel_3, rel_4
- pol_1, pol_2, pol_3, pol_4

**SauceOfGrav (18 params):**
- rate, depth, grav, reso, excur, calm
- tens_1, tens_2, tens_3, tens_4
- mass_1, mass_2, mass_3, mass_4
- pol_1, pol_2, pol_3, pol_4

**Sloth (minimal params):**
- type selection, invert, normalize (not really modulatable)

**Problem:** Cannot create "M1 Wave A" grid column because:
- If M1 has LFO loaded → works
- If M1 has ARSeq+ loaded → does nothing
- If M1 has Sauce loaded → does nothing
- If M1 has Sloth loaded → does nothing

---

## Goal: Extended Mod Matrix Grid

We want to extend the mod matrix from 80 columns to ~298 columns:

**Current Grid:**
- 16 rows (M1.A through M4.D)
- 80 columns (8 generators × 10 params each)

**Target Grid:**
- 16 rows (same)
- 298 columns:
  - 80 generator columns (existing) ✅
  - ~180 modulator columns (BLOCKED ❌)
  - 22 FX columns (ready) ✅
  - 16 send columns (ready) ✅

**Why FX/Send columns work but Mod columns don't:**
- FX units are global (only one HEAT, one ECHO, etc.) - not type-dependent
- Sends are per-channel (always CH1-8 echo/verb) - not type-dependent
- Modulators vary by slot (M1 might be LFO, M2 might be Sauce) - type-dependent!

---

## Backend Status (Complete ✅)

The backend implementation is DONE and WORKS:

**SuperCollider Files:**
- `supercollider/core/mod_snapshot.scd` - 50Hz snapshot system
- `supercollider/core/ext_mod.scd` - Extended modulation engine (430 lines)
- `supercollider/core/ext_mod_osc.scd` - OSC handlers
- `supercollider/init.scd` - Integration complete

**Contract Testing:**
- `contracts/mod_matrix_expansion.yaml` - 36/36 tests PASSING
- All OSC paths verified: `/noise/extmod/{add_route, remove_route, set_user_param, clear_all}`
- Wire key → synth arg mapping complete
- Base value tracking works

**Python Integration:**
- `src/config/__init__.py` - OSC paths added
- `src/gui/mod_routing_state.py` - Extended ModConnection dataclass with target_str
- `src/gui/controllers/modulation_controller.py` - Routes to correct OSC paths based on connection type

**What works NOW:**
```python
# This works in the backend RIGHT NOW:
conn = ModConnection(
    source_bus=0,  # M1.A
    target_str='fx:heat:drive',  # Route to HEAT drive
    amount=0.7
)
# OSC message sent: /noise/extmod/add_route [0, "fx:heat:drive", 1.0, 0.7, 0.0, 0, 0]
# Result: M1.A modulates HEAT drive ✅
```

**Backend supports these target types:**
- `fx:heat:drive` ✅
- `fx:echo:feedback` ✅
- `fx:reverb:size` ✅
- `fx:dual_filter:freq1` ✅
- `mod:1:rate` ✅ (but UI can't present this well)
- `send:3:ec` ✅

---

## Frontend Issue (BLOCKED on Standardization ❌)

### What We Tried (Failed Approach)

**Attempt 1: Popup-based UI**
- Added "+ Add Extended Route" button
- Popup with tabs: FX / Mod / Send
- User selects target from dropdowns
- **Problem:** Confusing UX, didn't match grid-based workflow

**Attempt 2: Extend grid with all mod params**
- Show all LFO params for M1-M4 (52 columns)
- Show all ARSeq+ params for M1-M4 (56 columns)
- Show all Sauce params for M1-M4 (72 columns)
- **Problem:** Most columns useless depending on what's loaded

**Root cause:** Cannot make a sensible grid without modulator standardization.

### Current Grid Implementation

**File:** `src/gui/mod_matrix_window.py` (800+ lines)

**Key Methods:**
- `_build_column_headers()` - Creates column headers
- `_build_rows()` - Creates cell grid for each mod output
- `_on_cell_clicked()` - Toggle route on/off
- `_on_cell_right_clicked()` - Open adjustment popup

**Grid cell structure:**
```python
# Stored in self.cells dictionary
key = (source_bus, target_slot, target_param)  # For generator routes
# e.g., (0, 2, 'cutoff') = M1.A → G3 Cutoff

# For extended routes (if we could build them):
key = (source_bus, None, 'fx:heat:drive')  # Extended route
# e.g., (0, None, 'fx:heat:drive') = M1.A → HEAT Drive
```

**How it works:**
1. Grid displays 16×80 cells
2. Click cell → `_on_cell_clicked(bus, slot, param)`
3. Creates ModConnection: `ModConnection(source_bus=bus, target_slot=slot, target_param=param)`
4. Routing state emits signal
5. modulation_controller sends OSC

**To extend grid, we need:**
- Add columns after generators (currently line ~210)
- Create cells for extended targets
- Cell click creates ModConnection with target_str instead of target_slot/target_param
- Everything else stays the same

---

## Proposed Solution: Modulator Standardization

### Step 1: Design Standardized Parameter Set

**Option A: Mirror Generator Structure (P1-P10)**
```
Common params (all modulators):
- rate, mode

Custom params (type-specific):
- P1, P2, P3, P4, P5, P6, P7, P8, P9, P10
```

**Mapping examples:**
```
LFO:
  P1 = shape
  P2 = pattern
  P3 = rotate
  P4 = wave_1 (output A wave)
  P5 = wave_2 (output B wave)
  P6 = wave_3 (output C wave)
  P7 = wave_4 (output D wave)
  P8 = pol_1 (output A polarity)
  ... etc

ARSeq+:
  P1 = clockMode
  P2 = atk_1 (output A attack)
  P3 = atk_2 (output B attack)
  P4 = atk_3 (output C attack)
  P5 = atk_4 (output D attack)
  P6 = rel_1 (output A release)
  ... etc

Sauce:
  P1 = depth
  P2 = grav (gravity)
  P3 = reso (resonance)
  P4 = excur (excursion)
  P5 = calm
  P6 = tens_1 (tension 1)
  ... etc
```

**Benefits:**
- Grid can show "M1 P1", "M1 P2" etc. regardless of loaded mod type
- Consistent with generator architecture
- UI labels can update based on loaded type (like generators do)

**Option B: Common Subset Only**
```
Only show params that exist across multiple types:
- rate (LFO, ARSeq+, Sauce)
- mode (LFO, ARSeq+)
```

**Benefits:**
- Minimal change
- No ambiguity

**Drawbacks:**
- Very limited cross-modulation capability
- Loses most of the power

### Step 2: Implementation Plan

**Phase 1: Backend Refactor**
1. Update SuperCollider SynthDefs (4 files):
   - `supercollider/synths/modulators/lfo.scd`
   - `supercollider/synths/modulators/arseq_plus.scd`
   - `supercollider/synths/modulators/sauce_of_grav.scd`
   - `supercollider/synths/modulators/sloth.scd` (if applicable)

2. Change param names from specific (wave_1, atk_1, tens_1) to generic (p1, p2, p3)

3. Update OSC handlers:
   - `supercollider/core/mod_osc.scd` - update param name mappings
   - Add mapping layer: UI sends "p1" → SC translates to current meaning

4. Test all 4 mod types still work correctly

**Phase 2: Frontend Refactor**
1. Update modulator UI widgets:
   - `src/gui/modulator_slot.py` - update param names
   - Keep labels dynamic based on type (like generators)

2. Update preset schema:
   - `src/presets/preset_schema.py` - migrate old param names to P1-P10

3. Add migration code for old presets

**Phase 3: Grid Extension**
1. Add MOD_PARAMS to mod_matrix_window.py:
```python
   MOD_PARAMS = [
       ('p1', 'P1'),
       ('p2', 'P2'),
       # ... up to P10
   ]
```

2. Extend `_build_column_headers()` to add mod columns

3. Extend `_build_rows()` to create mod cells

4. Cell clicks create: `ModConnection(source_bus=0, target_str='mod:1:p1')`

**Estimated Effort:**
- Phase 1 (Backend): 4-6 hours
- Phase 2 (Frontend): 2-3 hours  
- Phase 3 (Grid): 1-2 hours
- Testing: 2 hours
- **Total: ~10-13 hours**

---

## Alternative: Dynamic Grid (Complex)

Instead of standardization, make the grid dynamically show/hide columns based on what's loaded.

**How it would work:**
1. Grid starts with generator + FX + send columns
2. When user loads LFO in M1 → add LFO-specific columns for M1
3. When user loads ARSeq+ in M2 → add ARSeq+-specific columns for M2
4. Columns appear/disappear as mods change

**Benefits:**
- No backend refactor needed
- Always shows relevant params

**Drawbacks:**
- Complex grid management
- Confusing UX (columns appear/disappear)
- Hard to maintain
- Doesn't fit hardware synth philosophy

**Not recommended.**

---

## Files Reference

### Backend (Complete ✅)
```
supercollider/core/mod_snapshot.scd          - Snapshot system
supercollider/core/ext_mod.scd               - Extended mod engine
supercollider/core/ext_mod_osc.scd           - OSC handlers
supercollider/init.scd                        - Integration
contracts/mod_matrix_expansion.yaml          - 36/36 tests passing
```

### Frontend (Needs Standardization ❌)
```
src/gui/mod_matrix_window.py                 - Grid UI (needs extension)
src/gui/mod_routing_state.py                 - Data model (complete)
src/gui/controllers/modulation_controller.py - OSC routing (complete)
src/gui/modulator_slot.py                    - Mod UI (needs P1-P10)
src/presets/preset_schema.py                 - Needs migration
```

### Modulator SynthDefs (Need Refactor)
```
supercollider/synths/modulators/lfo.scd
supercollider/synths/modulators/arseq_plus.scd
supercollider/synths/modulators/sauce_of_grav.scd
supercollider/synths/modulators/sloth.scd
```

---

## Recommendation

**Standardize modulators to P1-P10 architecture:**
1. Consistent with generator design philosophy
2. Enables clean grid extension
3. Future-proof for additional mod types
4. ~10-13 hours of work but solves the problem permanently

**Steps to start:**
1. Review this brief
2. Decide on P1-P10 mapping for each modulator type
3. Start with one modulator (LFO) as proof-of-concept
4. Refactor remaining modulators
5. Extend grid

---

## Questions for New Session

1. **Do you approve P1-P10 standardization approach?**
   - Yes → proceed with mapping design
   - No → explore alternatives

2. **Which modulator should we refactor first?**
   - Recommendation: LFO (simplest, most common)

3. **What about existing presets?**
   - Need migration code: wave_1 → p4, etc.
   - Or break compatibility?

4. **Priority level?**
   - High: Critical for performance workflow
   - Medium: Nice to have, finish other features first
   - Low: Future enhancement

---

## Current Git State

**Branch:** `feature/mod-matrix`
**Last Commit:** 7a3af9b "WIP: Extended routes UI (has crash issue, investigating)"

**Completed work on branch:**
- Backend implementation (36/36 tests)
- Data model extension (ModConnection.target_str)
- OSC routing (extended routes)

**Needs cleanup:**
- Remove popup UI attempt
- Document standardization blocker
- Create standardization task

---

*End of Technical Brief*
