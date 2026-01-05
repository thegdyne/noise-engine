# Grid Extension Implementation Plan

## Goal
Extend the mod matrix grid from 80 columns to 122 columns by adding FX/Mod/Send targets.

## Current State
- 16 rows (M1.A through M4.D)
- 80 columns (8 generators × 10 params)
- Grid cells create generator routes only

## Target State  
- 16 rows (same)
- 122 columns (80 generator + 42 extended)
  - Columns 1-80: Generators (existing)
  - Columns 81-102: FX params (22 params)
  - Columns 103-106: Mod rate params (4 params)
  - Columns 107-122: Send params (16 params)
- Grid cells create BOTH generator AND extended routes

## Implementation Steps

### Step 1: Add Extended Target Definitions (~5 min)
File: `src/gui/mod_matrix_window.py`
- Add FX_PARAMS list (22 items)
- Add MOD_PARAMS list (4 items)
- Add SEND_PARAMS list (16 items)
- Add EXTENDED_PARAMS = FX + MOD + SEND
- Update TOTAL_COLS = 122

### Step 2: Extend Column Headers (~10 min)
File: `src/gui/mod_matrix_window.py` → `_build_column_headers()`
- After generator columns, add section separators
- Add FX section headers (grouped by unit)
- Add MOD section headers
- Add SEND section headers
- Visual grouping with background tints

### Step 3: Extend Cell Grid (~15 min)
File: `src/gui/mod_matrix_window.py` → `_build_rows()`
- Loop through EXTENDED_PARAMS after generator params
- Create cells for extended targets
- Store in self.cells with extended keys: `(bus, None, "fx:heat:drive")`

### Step 4: Update Cell Click Handlers (~10 min)
File: `src/gui/mod_matrix_window.py` → `_on_cell_clicked()`, `_on_cell_right_clicked()`
- Detect if target is extended (check for ':' in param string)
- Create ModConnection with target_str instead of target_slot/target_param
- Rest of logic stays the same (popup already handles extended routes via modulation_controller)

### Step 5: Update Navigation (~5 min)
File: `src/gui/mod_matrix_window.py` → keyboard navigation
- Update TOTAL_COLS constant
- Navigation should work automatically

### Step 6: Remove Popup UI Code (~5 min)
Files: `src/gui/mod_matrix_window.py`
- Remove `_build_extended_routes_section()` method
- Remove `_on_add_extended_route_clicked()` and related methods
- Remove `_update_ext_routes_list()` and helper methods
- Remove call to `_build_extended_routes_section()` in `_setup_ui()`

### Step 7: Test (~10 min)
- Open mod matrix
- Scroll horizontally to see extended columns
- Click FX cell → creates route
- Right-click → popup opens
- Adjust amount/offset → works
- Remove route → works
- Save preset → routes persist
- Load preset → routes restore

## Estimated Time: 1 hour

## Files to Modify
- `src/gui/mod_matrix_window.py` (main changes)
- `src/gui/mod_connection_popup_ext.py` (DELETE - not needed)

## Files Already Complete
- Backend (SuperCollider + OSC) ✅
- Data model (ModConnection) ✅
- OSC routing (modulation_controller) ✅

---

**Ready to implement next session!**
