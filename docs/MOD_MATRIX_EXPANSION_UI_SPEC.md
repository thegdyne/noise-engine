# Mod Matrix Expansion - UI Specification v1.0.0

---
**Status:** Draft  
**Author:** Gareth + Claude  
**Date:** 2026-01-05  
**Backend Contract:** mod_matrix_expansion.yaml (frozen)  
**Depends On:** MOD_MATRIX_EXPANSION_SPEC_v1.6.1.md (backend complete)

---

## Overview

Extends the modulation matrix UI to support routing mod sources to:
- **FX parameters** (HEAT, ECHO, REVERB, DUAL_FILTER)
- **Modulator parameters** (LFO, ARSeq+, SauceOfGrav)
- **Send levels** (per-channel echo/verb sends)

Currently, the UI only supports generator targets (cutoff, frequency, etc.).

---

## Scope

### In Scope
- Extend `ModConnection` dataclass to support extended target types
- Add target type constants (TARGET_TYPE_FX, TARGET_TYPE_MOD, TARGET_TYPE_SEND)
- Add target string builders (build_fx_target, build_mod_target, build_send_target)
- Extend `ModConnectionPopup` to have 4 tabs: Generator / FX / Modulator / Send
- Update `ModMatrixWindow` to send extended OSC messages
- Add preset persistence for extended routes

### Out of Scope
- Backend implementation (already complete)
- Visual indicators for extended targets in matrix grid (future enhancement)
- "Learn" mode for quick routing (future enhancement)

---

## Architecture

### Current Structure (Generator Targets Only)
```
ModConnection:
  source_bus: int (0-15)
  target_slot: int (1-8)
  target_param: str ("cutoff", "frequency", etc.)
  
Target String Format: "gen:{slot}:{param}"
```

### New Structure (Extended Targets)
```
ModConnection:
  source_bus: int (0-15)
  target_type: str ("gen", "fx", "mod", "send")  # NEW
  target_str: str  # NEW - replaces target_slot + target_param
  
Target String Formats:
  - Generator: "gen:{slot}:{param}"      (e.g. "gen:1:cutoff")
  - FX:        "fx:{type}:{param}"       (e.g. "fx:heat:drive")
  - Modulator: "mod:{slot}:{param}"      (e.g. "mod:1:rate")
  - Send:      "send:{slot}:{type}"      (e.g. "send:3:ec")
```

---

## Requirements

### R001: Extended Target Types
**Priority:** must  
**Description:** ModConnection supports all target types  
**Acceptance Criteria:**
- [ ] `target_type` field added to ModConnection (gen/fx/mod/send)
- [ ] `target_str` field added to replace target_slot + target_param
- [ ] Backward compatibility: old presets with target_slot/target_param still load
- [ ] `key` property uses target_str instead of target_slot/param

### R002: Target String Builders
**Priority:** must  
**Description:** Helper functions to build target strings  
**Acceptance Criteria:**
- [ ] `build_gen_target(slot, param)` returns "gen:{slot}:{param}"
- [ ] `build_fx_target(fx_type, param)` returns "fx:{fx_type}:{param}"
- [ ] `build_mod_target(slot, param)` returns "mod:{slot}:{param}"
- [ ] `build_send_target(slot, send_type)` returns "send:{slot}:{send_type}"

### R003: FX Parameter Lists
**Priority:** must  
**Description:** UI shows correct params for each FX type  
**Acceptance Criteria:**
- [ ] HEAT params: circuit, drive, mix
- [ ] ECHO params: time, feedback, tone, wow, spring
- [ ] REVERB params: size, decay, tone
- [ ] DUAL_FILTER params: drive, freq1, reso1, freq2, reso2, routing, syncAmt, mix

### R004: Modulator Parameter Lists
**Priority:** must  
**Description:** UI shows correct params for each mod type  
**Acceptance Criteria:**
- [ ] LFO params: rate, wave_1-4, pol_1-4, shape, pattern, mode, rotate
- [ ] ARSeq+ params: rate, atk_1-4, rel_1-4, pol_1-4, mode
- [ ] SauceOfGrav params: rate, depth, grav, reso, excur, calm, tens_1-4, mass_1-4, pol_1-4

### R005: Send Target Lists
**Priority:** must  
**Description:** UI shows send targets  
**Acceptance Criteria:**
- [ ] Channel 1-8 selectable
- [ ] Send type: ec (echo), vb (verb)

### R006: ModConnectionPopup Tabs
**Priority:** must  
**Description:** Popup has 4 tabs for target selection  
**Acceptance Criteria:**
- [ ] Tab 1: Generator (existing UI, unchanged)
- [ ] Tab 2: FX (type dropdown + param dropdown)
- [ ] Tab 3: Modulator (slot dropdown + param dropdown)
- [ ] Tab 4: Send (channel dropdown + send type dropdown)
- [ ] Tab selection updates target_type
- [ ] get_target_string() builds correct format based on tab

### R007: OSC Message Format
**Priority:** must  
**Description:** UI sends extended OSC messages  
**Acceptance Criteria:**
- [ ] Add route: `/noise/extmod/add_route` with [bus, target_str, depth, amt, off, pol, inv]
- [ ] Remove route: `/noise/extmod/remove_route` with [bus, target_str]
- [ ] Set user param: `/noise/extmod/set_user_param` with [target_str, value]
- [ ] Clear all: `/noise/extmod/clear_all`

### R008: Preset Persistence
**Priority:** must  
**Description:** Extended routes save/load in presets  
**Acceptance Criteria:**
- [ ] PresetSchema has `ext_mod_routes` field (List[Dict])
- [ ] save_preset() serializes extended connections
- [ ] load_preset() deserializes and sends OSC messages
- [ ] Backward compat: old presets without ext_mod_routes still load

### R009: UI State Management
**Priority:** should  
**Description:** UI tracks extended routes separately  
**Acceptance Criteria:**
- [ ] ModRoutingState distinguishes gen vs extended routes
- [ ] Matrix grid shows extended routes differently (or hides them)
- [ ] Extended route count displayed somewhere

---

## UI Mockup

### ModConnectionPopup - Extended Version
```
┌────────────────────────────────────────┐
│  M1.A → [Target]                       │  Header (target TBD)
├────────────────────────────────────────┤
│  ┌──────────────────────────────────┐  │
│  │ Generator │ FX │ Mod │ Send      │  │  Tab Widget
│  └──────────────────────────────────┘  │
│                                        │
│  [Tab-specific content here]           │
│                                        │
│  Amount   [━━━━━●━━━] 50%              │  Common controls
│  Offset   [━━━━━━━━●] 0%               │
│  Polarity [Bipolar ▼]                  │
│  Invert   [ ]                          │
│                                        │
│         [Remove]                       │
└────────────────────────────────────────┘
```

### Tab 1: Generator (Existing)
```
Slot:   [1 ▼]
Param:  [cutoff ▼]
```

### Tab 2: FX
```
FX Unit:  [HEAT ▼]
Param:    [drive ▼]
```

### Tab 3: Modulator
```
Mod Slot: [1 ▼]
Param:    [rate ▼]
```

### Tab 4: Send
```
Channel:  [3 ▼]
Send:     [echo ▼]
```

---

## Implementation Plan

### Phase 1: Data Model (1 hour)
**File:** `src/gui/mod_routing_state.py`

1. Add target type constants
2. Add target string builders
3. Extend ModConnection dataclass:
   - Add `target_type` field (default "gen")
   - Add `target_str` field
   - Add migration logic from old format
   - Update `key` property
   - Update serialization

**Verification:**
```python
# Old format still works
conn = ModConnection(source_bus=0, target_slot=1, target_param="cutoff")
assert conn.target_type == "gen"
assert conn.target_str == "gen:1:cutoff"

# New format works
conn = ModConnection(source_bus=0, target_type="fx", target_str="fx:heat:drive")
assert conn.target_type == "fx"
```

### Phase 2: UI - Popup Extension (2 hours)
**File:** `src/gui/mod_connection_popup.py`

1. Refactor existing UI into Generator tab
2. Add QTabWidget
3. Create FX tab:
   - FX type QComboBox (heat/echo/reverb/dual_filter)
   - Param QComboBox (updates when FX type changes)
4. Create Mod tab:
   - Slot QComboBox (1-4)
   - Param QComboBox (all mod params)
5. Create Send tab:
   - Channel QComboBox (1-8)
   - Send type QComboBox (ec/vb)
6. Update get_target_string() method
7. Update header to show target description

**Verification:**
- Open popup
- Switch between tabs
- Select different targets
- Verify target_str format

### Phase 3: UI - Matrix Window (1 hour)
**File:** `src/gui/mod_matrix_window.py`

1. Update add_route() to send extmod_add_route OSC
2. Update remove_route() to send extmod_remove_route OSC
3. Add route type detection (gen vs extended)
4. Update UI to show extended route count

**Verification:**
- Create extended route
- Verify OSC message sent
- Check SuperCollider receives route

### Phase 4: Preset Integration (1 hour)
**File:** `src/presets/preset_schema.py`

1. Add `ext_mod_routes: List[Dict]` field
2. Update save_preset() to include extended routes
3. Update load_preset() to restore extended routes via OSC
4. Test backward compatibility

**Verification:**
- Create extended routes
- Save preset
- Load preset
- Verify routes restored

---

## Testing Strategy

### Unit Tests (Python)
```python
def test_target_string_builders():
    assert build_gen_target(1, "cutoff") == "gen:1:cutoff"
    assert build_fx_target("heat", "drive") == "fx:heat:drive"
    assert build_mod_target(2, "rate") == "mod:2:rate"
    assert build_send_target(3, "ec") == "send:3:ec"

def test_backward_compatibility():
    # Old format
    old_data = {
        'source_bus': 0,
        'target_slot': 1,
        'target_param': 'cutoff',
        'amount': 0.5
    }
    conn = ModConnection.from_dict(old_data)
    assert conn.target_type == "gen"
    assert conn.target_str == "gen:1:cutoff"
```

### Integration Tests (Manual)
1. **FX Modulation**
   - Route LFO 1A → fx:heat:drive
   - Play sound through HEAT
   - Verify drive oscillates

2. **Mod Cross-Modulation**
   - Route Sloth 1A → mod:1:rate
   - Verify LFO rate drifts

3. **Send Modulation**
   - Route ARSeq+ 1A → send:3:ec
   - Verify echo send follows envelope

4. **Preset Persistence**
   - Create 2 extended routes
   - Save preset
   - Restart
   - Load preset
   - Verify routes restored

---

## Open Questions

**Q1:** Should extended routes show in the matrix grid?
- **Option A:** Hide them (grid only shows gen routes)
- **Option B:** Show with different color/icon
- **Recommendation:** Option A for now (simpler)

**Q2:** How to display target in popup header?
- Generator: "M1.A → G1 CUT" (current format)
- FX: "M1.A → HEAT Drive"
- Mod: "M1.A → LFO 1 Rate"
- Send: "M1.A → CH3 Echo"

**Q3:** Should we validate discrete param ranges in UI?
- HEAT circuit: 0-3 (4 choices)
- LFO wave: 0-7 (8 choices)
- **Recommendation:** Let SC handle it (already implemented)

---

## Success Criteria

- [ ] All 4 tabs functional in ModConnectionPopup
- [ ] Can create routes to FX/mod/send targets
- [ ] Routes persist in presets
- [ ] Manual test: LFO → HEAT drive works
- [ ] Manual test: Sloth → LFO rate works
- [ ] Manual test: ARSeq+ → send works
- [ ] Backward compat: old presets load

---

## Timeline Estimate

- Phase 1 (Data Model): 1 hour
- Phase 2 (Popup UI): 2 hours
- Phase 3 (Matrix Window): 1 hour
- Phase 4 (Presets): 1 hour
- Testing: 1 hour
- **Total: 6 hours**

---

## Next Steps

1. Review this spec
2. Create UI contract (mod_matrix_expansion_ui.yaml)
3. Implement Phase 1-4
4. Manual integration testing
5. Freeze contracts
6. Merge to main

---

*End of UI Specification v1.0.0*
