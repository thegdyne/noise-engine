# Mod Matrix Expansion - Implementation Progress

## Session Summary (2026-01-05)

### ✅ Completed

#### Backend (100% - Contract Verified)
- **File:** `supercollider/core/mod_snapshot.scd`
  - 50Hz mod bus snapshot system with guards
  - Prevents crashes if ~modBuses not ready
  
- **File:** `supercollider/core/ext_mod.scd`
  - Extended modulation engine (~430 lines)
  - 37 parameter configurations (mod/FX/send)
  - Wire key → synth arg mapping
  - Per-target summing with discrete param handling
  - Restore-on-remove functionality
  
- **File:** `supercollider/core/ext_mod_osc.scd`
  - OSC handlers: /noise/extmod/{add_route, remove_route, set_user_param, clear_all}
  - Auto-start/stop apply task
  
- **File:** `supercollider/init.scd`
  - Integration: loads mod_snapshot → ext_mod → ext_mod_osc
  
- **File:** `src/config/__init__.py`
  - Python OSC paths added (extmod_*)
  
- **Contract:** `contracts/mod_matrix_expansion.yaml`
  - 36/36 tests passing
  - All requirements verified

#### UI Spec (100% - Contract Verified)
- **File:** `docs/MOD_MATRIX_EXPANSION_UI_SPEC_v1.0.2.md`
  - Verified against actual SynthDefs
  - Verified against actual backend implementation
  - Wire keys extracted from real code
  - Zero assumptions, zero guessing
  - Option A architecture (parallel systems)

#### Phase 1: Data Model (100% Complete)
- **File:** `src/gui/mod_routing_state.py` (Updated)
  - Added `target_str` field for extended routes
  - Added `is_extended` property
  - Updated `key` property (dual logic)
  - Target string builders: build_mod_target(), build_fx_target(), build_send_target()
  - Backward compatible serialization
  - Generator/extended route separation
  - All unit tests pass

#### Phase 2: Extended Popup (100% Complete)
- **File:** `src/gui/mod_connection_popup_ext.py` (New, 585 lines)
  - 4-tab interface (FX/Mod/Send - no generator tab needed)
  - Create mode: user selects target type → param → creates route
  - Edit mode: shows amount/offset sliders only
  - Wire key dropdowns populated from backend contract
  - FX params: HEAT (3), ECHO (5), REVERB (3), DUAL_FILTER (11)
  - Mod params: LFO (13), ARSeq+ (14), SauceOfGrav (18)
  - Send params: ec, vb
  - All dropdowns use backend-verified wire keys

#### Phase 3: OSC Integration (100% Complete)
- **File:** `src/gui/controllers/modulation_controller.py` (Updated)
  - `_on_mod_route_added()` handles extended routes
  - `_on_mod_route_removed()` handles extended routes (signature changed to pass conn)
  - `_on_mod_route_changed()` handles extended routes
  - Routes to correct OSC paths based on `conn.is_extended`
  - Generator routes unchanged (no risk)
  - Extended routes use /noise/extmod/* paths

---

### ⏳ Remaining Work

#### Phase 3 Continued: Matrix Window UI (2-3 hours)
**Status:** Not started  
**Files to modify:**
- `src/gui/mod_matrix_window.py`

**Tasks:**
1. Add "Extended Routes" section below matrix grid
   - Button: "+ Add Extended Route"
   - List widget showing existing extended routes
   - Click route → open ExtModConnectionPopup in edit mode
   
2. Wire up ExtModConnectionPopup creation button
   - Opens popup in create mode
   - Signal: `connection_created` → add to routing_state
   - Signal: `connection_changed` → update routing_state
   - Signal: `remove_requested` → remove from routing_state
   
3. Update extended route list when routes change
   - Listen to routing_state signals
   - Display: "M1.A → HEAT Drive" style labels
   
4. Extended route counter/status display
   - Show count: "5 generator + 2 extended routes"

**Verification:**
- Can open popup to create extended route
- Can select FX/Mod/Send target
- Can adjust amount/offset
- Can click Create → route appears in list
- Can click route in list → edit popup opens
- Can remove route from edit popup

---

#### Phase 4: Preset Integration (1.5 hours)
**Status:** Not started  
**Files to modify:**
- `src/presets/preset_schema.py`

**Tasks:**
1. Add fields to PresetSchema:
```python
   ext_mod_routes: List[Dict] = field(default_factory=list)
   ext_user_params: Dict[str, float] = field(default_factory=dict)
```

2. Update `save_preset()`:
   - Serialize extended routes separately from generator routes
   - Save base values for extended targets
   
3. Update `load_preset()`:
   - Restore UI params first
   - Send ext_user_params via OSC (set_user_param)
   - Add extended routes via OSC (add_route)
   - Add generator routes last
   
4. Add base value tracking:
   - When creating extended route, capture current UI value
   - Send via `/noise/extmod/set_user_param` before add_route
   - Call on: SC boot, preset load, live param change

**Verification:**
- Create 1 gen + 2 extended routes
- Save preset
- Clear all routes
- Load preset
- All routes restored correctly
- Base values center modulation correctly

---

#### Phase 5: Testing & Polish (1 hour)
**Status:** Not started

**Integration Tests:**
1. LFO → fx:heat:drive (verify oscillation)
2. Sloth → mod:1:rate (verify drift)
3. ARSeq+ → send:3:ec (verify envelope)
4. Preset save/load (verify persistence)
5. Base value tracking (verify modulation centers)

**Bug Fixes:**
- Any UI glitches discovered
- OSC timing issues
- Edge cases

---

## Architecture Decisions (Locked)

### Option A: Parallel Systems (Chosen)
- **Generator routes:** `/noise/mod/route/*` (unchanged)
- **Extended routes:** `/noise/extmod/*` (new, parallel)
- **State:** Separate dictionaries (`~modRoutes` vs `~extTargets`)
- **Benefits:** Clean separation, no risk to existing, different polling rates possible

### Wire Keys (Contract-Verified)
All wire keys extracted from actual SynthDefs:
- FX: type, drive, mix, time, feedback, tone, wow, spring, size, decay, etc.
- Mod: rate, mode, shape, pattern, rotate, wave_1-4, pol_1-4, atk_1-4, etc.
- Send: ec, vb

Backend handles mapping to synth args (e.g., wave_1 → waveA, pol_1 → polarityA).

---

## Next Session Action Items

1. **Start Phase 3 continued (Matrix Window UI)**
   - Read mod_matrix_window.py structure
   - Add extended routes section
   - Wire up popup creation
   
2. **Then Phase 4 (Presets)**
   - Update schema
   - Update save/load
   - Add base value tracking
   
3. **Then Phase 5 (Testing)**
   - Manual integration tests
   - Bug fixes
   - Polish

**Estimated remaining: 4.5 hours**

---

## Files Modified This Session

### Created:
- `contracts/mod_matrix_expansion.yaml`
- `supercollider/core/mod_snapshot.scd`
- `supercollider/core/ext_mod.scd`
- `supercollider/core/ext_mod_osc.scd`
- `docs/MOD_MATRIX_EXPANSION_UI_SPEC_v1.0.2.md`
- `src/gui/mod_connection_popup_ext.py`

### Modified:
- `supercollider/init.scd`
- `src/config/__init__.py`
- `src/gui/mod_routing_state.py`
- `src/gui/controllers/modulation_controller.py`

### Backed Up:
- `src/gui/mod_routing_state.py.backup`
- `src/gui/controllers/modulation_controller.py.backup`

---

*End of Progress Report*
