# Mod Matrix Expansion - UI Specification v1.0.2

---
**Status:** Draft (Contract-Verified)  
**Author:** Gareth + Claude  
**Date:** 2026-01-05  
**Backend Contract:** mod_matrix_expansion.yaml (frozen, 36/36 tests pass)  
**Depends On:** MOD_MATRIX_EXPANSION_SPEC_v1.6.1.md (backend complete)

**Changelog:**
- v1.0.2: Wire keys verified against actual SynthDefs - zero guessing
- v1.0.1: Fixed to match Option A (parallel systems)
- v1.0.0: Initial draft (had mismatches)

---

## Overview

Extends the modulation matrix UI to support routing mod sources to:
- **FX parameters** (HEAT, ECHO, REVERB, DUAL_FILTER)
- **Modulator parameters** (LFO, ARSeq+, SauceOfGrav)
- **Send levels** (per-channel echo/verb sends)

Currently, the UI only supports generator targets (cutoff, frequency, etc.).

**Architecture: Parallel Systems (Option A)**
- Generator routes: existing `/noise/mod/route/*` (UNCHANGED)
- Extended routes: new `/noise/extmod/*` (PARALLEL)

---

## Architecture

### Two Parallel Routing Systems

**Generator Routes (Existing - Unchanged):**
```
Storage: (source_bus, target_slot, target_param)
  - source_bus: 0-15
  - target_slot: 1-8
  - target_param: "cutoff", "frequency", "resonance", etc.

OSC: /noise/mod/route/{add|remove|set|clear_all}
```

**Extended Routes (New - This Spec):**
```
Storage: (source_bus, target_str)
  - source_bus: 0-15
  - target_str: "mod:1:rate", "fx:heat:drive", "send:3:ec"

OSC: /noise/extmod/{add_route|remove_route|set_user_param|clear_all}
```

**Target String Formats:**
- Modulator: `"mod:{slot}:{param}"` (slot 1-4)
- FX: `"fx:{type}:{param}"` (type: heat|echo|reverb|dual_filter)
- Send: `"send:{slot}:{send}"` (slot 1-8, send: ec|vb)

---

## Requirements

### R001: Extended Connection Data Model
**Priority:** must  
**Acceptance Criteria:**
- [ ] Keep `target_slot: int | None` (generator only)
- [ ] Keep `target_param: str | None` (generator only)
- [ ] Add `target_str: str | None` (extended only)
- [ ] Add `is_extended` property
- [ ] Backward compat: old presets load
- [ ] `key` uses `(bus, target_str)` for extended, `(bus, slot, param)` for gen

### R002: Target String Builders
**Priority:** must  
**Acceptance Criteria:**
- [ ] `build_mod_target(slot, param)` returns `"mod:{slot}:{param}"`
- [ ] `build_fx_target(fx_type, param)` returns `"fx:{fx_type}:{param}"`
- [ ] `build_send_target(slot, send_type)` returns `"send:{slot}:{send_type}"`

### R003: FX Parameter Lists (Wire Keys - VERIFIED)
**Priority:** must  
**Description:** UI shows params that exist in actual SynthDefs  
**Acceptance Criteria:**
- [ ] HEAT: type, drive, mix (from \heat SynthDef)
- [ ] ECHO: time, feedback, tone, wow, spring (from \tapeEcho SynthDef)
- [ ] REVERB: size, decay, tone (from \reverb SynthDef)
- [ ] DUAL_FILTER: drive, freq1, reso1, freq2, reso2, routing, sync1Rate, sync2Rate, syncAmt, harmonics, mix (from \dualFilter SynthDef)

**Note:** These are SC synth arg names. Backend maps UI wire keys to these.

### R004: Modulator Parameter Lists (Wire Keys - VERIFIED)
**Priority:** must  
**Description:** UI shows params that exist in actual SynthDefs  
**Acceptance Criteria:**
- [ ] LFO: rate, mode, shape, pattern, rotate, wave_1-4 (waveA-D), pol_1-4 (polarityA-D) (from \modLFO SynthDef)
- [ ] ARSeq+: rate, mode, clockMode, atk_1-4 (atkA-D), rel_1-4 (relA-D), pol_1-4 (polarityA-D) (from \modARSeqPlus SynthDef)
- [ ] SauceOfGrav: rate, depth, grav (gravity), reso (resonance), excur (excursion), calm, tens_1-4 (tension1-4), mass_1-4 (mass1-4), pol_1-4 (polarity1-4) (from \ne_mod_sauce_of_grav SynthDef)

**Note:** Backend handles wire key → synth arg mapping (e.g., grav → gravity)

### R005: Send Target Lists
**Priority:** must  
**Acceptance Criteria:**
- [ ] Channel 1-8 selectable
- [ ] Send type: ec (echo), vb (verb)

### R006: ModConnectionPopup Tabs
**Priority:** must  
**Acceptance Criteria:**
- [ ] Tab 1: Generator (existing, unchanged)
- [ ] Tab 2: FX (type + param dropdowns)
- [ ] Tab 3: Modulator (slot + param dropdowns)
- [ ] Tab 4: Send (channel + send type dropdowns)

### R007: OSC Message Routing
**Priority:** must  

**Generator routes (existing, unchanged):**
- [ ] Add: `/noise/mod/route/add [bus, slot, param, depth, amt, off, pol, inv]`
- [ ] Remove: `/noise/mod/route/remove [bus, slot, param]`
- [ ] Set: `/noise/mod/route/set [bus, slot, param, depth, amt, off, pol, inv]`
- [ ] Clear: `/noise/mod/route/clear_all`

**Extended routes (new, parallel):**
- [ ] Add: `/noise/extmod/add_route [bus, target_str, depth, amt, off, pol, inv]`
- [ ] Remove: `/noise/extmod/remove_route [bus, target_str]`
- [ ] Set base: `/noise/extmod/set_user_param [target_str, value]`
- [ ] Clear: `/noise/extmod/clear_all`

**Note:** No `/noise/extmod/set_route` OSC handler exists. Use add_route (upserts internally).

### R008: Base Value Tracking
**Priority:** must  
**Acceptance Criteria:**
- [ ] Call `/noise/extmod/set_user_param` BEFORE adding routes
- [ ] Call on: SC boot, preset load, live param change
- [ ] Base values from current UI state

### R009: Preset Persistence
**Priority:** must  
**Acceptance Criteria:**
- [ ] Add `ext_mod_routes: List[Dict]` (separate from `mod_routes`)
- [ ] Add `ext_user_params: Dict[str, float]` (optional)
- [ ] save_preset() serializes both
- [ ] load_preset() restores `ext_user_params` FIRST, then `ext_mod_routes`
- [ ] Backward compat: old presets load

### R010: UI State Management
**Priority:** should  
**Acceptance Criteria:**
- [ ] Separate storage for gen vs extended
- [ ] Matrix grid shows only generator routes
- [ ] Extended route counter displayed

---

## Wire Keys Reference (Contract-Verified)

### Rule: Wire Keys Are Canonical
- UI emits only keys listed below (verified against actual SynthDefs)
- Display labels may differ (e.g., "Feedback" displays, "feedback" sent)
- Backend handles wire key → synth arg mapping where needed

---

### FX Wire Keys (Verified Against SynthDefs)

**HEAT (\heat SynthDef):**
```
UI Wire Key    →  SC Synth Arg   | Display Label
────────────────────────────────────────────────
type           →  circuit         | Circuit
drive          →  drive           | Drive
mix            →  mix             | Mix
```

**ECHO (\tapeEcho SynthDef):**
```
UI Wire Key    →  SC Synth Arg   | Display Label
────────────────────────────────────────────────
time           →  time            | Time
feedback       →  feedback        | Feedback
tone           →  tone            | Tone
wow            →  wow             | Wow
spring         →  spring          | Spring
```

**REVERB (\reverb SynthDef):**
```
UI Wire Key    →  SC Synth Arg   | Display Label
────────────────────────────────────────────────
size           →  size            | Size
decay          →  decay           | Decay
tone           →  tone            | Tone
```

**DUAL_FILTER (\dualFilter SynthDef):**
```
UI Wire Key    →  SC Synth Arg   | Display Label
────────────────────────────────────────────────
drive          →  drive           | Drive
freq1          →  freq1           | Freq 1
reso1          →  reso1           | Res 1
freq2          →  freq2           | Freq 2
reso2          →  reso2           | Res 2
routing        →  routing         | Routing
sync1Rate      →  sync1Rate       | Sync 1
sync2Rate      →  sync2Rate       | Sync 2
syncAmt        →  syncAmt         | Sync Amt
harmonics      →  harmonics       | Harmonics
mix            →  mix             | Mix
```

---

### Modulator Wire Keys (Verified Against SynthDefs)

**LFO (\modLFO SynthDef):**
```
UI Wire Key    →  SC Synth Arg   | Display Label
────────────────────────────────────────────────
rate           →  rate            | Rate
mode           →  mode            | Mode
shape          →  shape           | Shape
pattern        →  pattern         | Pattern
rotate         →  rotate          | Rotate
wave_1         →  waveA           | Wave A
wave_2         →  waveB           | Wave B
wave_3         →  waveC           | Wave C
wave_4         →  waveD           | Wave D
pol_1          →  polarityA       | Pol A
pol_2          →  polarityB       | Pol B
pol_3          →  polarityC       | Pol C
pol_4          →  polarityD       | Pol D
```

**ARSeq+ (\modARSeqPlus SynthDef):**
```
UI Wire Key    →  SC Synth Arg   | Display Label
────────────────────────────────────────────────
rate           →  rate            | Rate
mode           →  mode            | Mode
clockMode      →  clockMode       | Clock Mode
atk_1          →  atkA            | Attack A
atk_2          →  atkB            | Attack B
atk_3          →  atkC            | Attack C
atk_4          →  atkD            | Attack D
rel_1          →  relA            | Release A
rel_2          →  relB            | Release B
rel_3          →  relC            | Release C
rel_4          →  relD            | Release D
pol_1          →  polarityA       | Pol A
pol_2          →  polarityB       | Pol B
pol_3          →  polarityC       | Pol C
pol_4          →  polarityD       | Pol D
```

**SauceOfGrav (\ne_mod_sauce_of_grav SynthDef):**
```
UI Wire Key    →  SC Synth Arg   | Display Label
────────────────────────────────────────────────
rate           →  rate            | Rate
depth          →  depth           | Depth
grav           →  gravity         | Gravity
reso           →  resonance       | Resonance
excur          →  excursion       | Excursion
calm           →  calm            | Calm
tens_1         →  tension1        | Tension 1
tens_2         →  tension2        | Tension 2
tens_3         →  tension3        | Tension 3
tens_4         →  tension4        | Tension 4
mass_1         →  mass1           | Mass 1
mass_2         →  mass2           | Mass 2
mass_3         →  mass3           | Mass 3
mass_4         →  mass4           | Mass 4
pol_1          →  polarity1       | Pol 1
pol_2          →  polarity2       | Pol 2
pol_3          →  polarity3       | Pol 3
pol_4          →  polarity4       | Pol 4
```

---

### Send Wire Keys
```
UI Wire Key    →  SC Synth Arg   | Display Label
────────────────────────────────────────────────
ec             →  echoSend        | Echo
vb             →  verbSend        | Verb
```

---

## Implementation Plan

### Phase 1: Data Model (1 hour)
**File:** `src/gui/mod_routing_state.py`

1. Add target string builders
2. Extend ModConnection:
   - Add `target_str: str | None`
   - Add `is_extended` property
   - Update `key` property
   - Update serialization
   - Migration from old format

**Test:**
```python
# Generator (unchanged)
conn = ModConnection(source_bus=0, target_slot=1, target_param="cutoff")
assert not conn.is_extended
assert conn.key == (0, 1, "cutoff")

# Extended (new)
conn = ModConnection(source_bus=0, target_str="fx:heat:drive")
assert conn.is_extended
assert conn.key == (0, "fx:heat:drive")
```

### Phase 2: UI - Popup Extension (2 hours)
**File:** `src/gui/mod_connection_popup.py`

1. Add QTabWidget
2. Refactor existing UI → Generator tab
3. Create FX tab with wire key dropdowns
4. Create Mod tab with wire key dropdowns
5. Create Send tab
6. Update header display

### Phase 3: UI - Matrix Window (1.5 hours)
**File:** `src/gui/mod_matrix_window.py`

1. Update add_route() - route to correct OSC
2. Update remove_route() - route to correct OSC
3. Add set_ext_user_param() - called before add
4. Update UI state tracking

### Phase 4: Preset Integration (1.5 hours)
**File:** `src/presets/preset_schema.py`

1. Add `ext_mod_routes` field
2. Add `ext_user_params` field
3. Update save/load
4. Test backward compat

---

## Testing

### Unit Tests
```python
def test_wire_keys():
    assert build_mod_target(1, "rate") == "mod:1:rate"
    assert build_fx_target("heat", "drive") == "fx:heat:drive"
    assert build_send_target(3, "ec") == "send:3:ec"

def test_connection_types():
    gen = ModConnection(source_bus=0, target_slot=1, target_param="cutoff")
    assert not gen.is_extended
    
    ext = ModConnection(source_bus=0, target_str="fx:heat:drive")
    assert ext.is_extended
```

### Integration Tests
1. LFO → fx:heat:drive (verify oscillation)
2. Sloth → mod:1:rate (verify drift)
3. ARSeq+ → send:3:ec (verify envelope)
4. Preset save/load (verify persistence)
5. Base value tracking (verify modulation centers)

---

## Success Criteria

- [ ] All 4 tabs functional
- [ ] Can create FX/mod/send routes
- [ ] Generator routes unchanged
- [ ] Correct OSC paths used
- [ ] Base values tracked
- [ ] Presets persist
- [ ] Manual tests pass
- [ ] Backward compat works

---

## Timeline

- Phase 1: 1 hour
- Phase 2: 2 hours
- Phase 3: 1.5 hours
- Phase 4: 1.5 hours
- Testing: 1 hour
- **Total: 7 hours**

---

## Next Steps

1. ✅ Backend complete (36/36 tests)
2. ✅ UI spec verified against SynthDefs
3. ⏳ Create UI contract
4. ⏳ Implement Phase 1-4
5. ⏳ Integration testing
6. ⏳ Merge

---

*End of UI Specification v1.0.2 (Contract-Verified)*
