# UI Refresh Implementation Guide

## Overview

This guide decomposes the UI_REFRESH_SPEC.md into 7 sequential phases for delivery via Claude Code sessions. Each phase has hard exit gates that must pass before proceeding.

**Total Effort:** ~20-24 hours across 7 sessions  
**Methodology:** CDD-lite (exit gates, not full YAML contracts)  
**Key Constraint:** Phase dependencies are strict—earlier phases create infrastructure later phases require.

---

## Dependency Graph

```
Phase 0: Bus Unification (149→176)
    │
    ├──► Phase 1: SC FX Slot Infrastructure
    │        │
    │        └──► Phase 2: SC Channel Strip Sends
    │                 │
    │                 ├──► Phase 3: Python FX Slot GUI
    │                 │        │
    │                 │        └──► Phase 5: Boid Pulse Updates
    │                 │
    │                 └──► Phase 4: Mixer Panel Updates
    │                          │
    │                          └──► Phase 5: Boid Pulse Updates
    │
    └──► Phase 6: Preset Schema + Migration
             │
             └──► Phase 7: Main Frame Integration
```

---

## Phase 0: Bus Unification Foundation

**Session type:** Build  
**Effort:** 2-3 hours  
**Blocking:** YES — all other phases depend on this

### Why First

The unified bus system expands from 149 to 176 targets. Every boid column index, every unified key, every pulse resolver references these indices. Getting this wrong cascades everywhere.

### Contracts Addressed

- **Contract 1:** Bus target strategy (breaking remap 108+)
- **Contract 2:** Unified key naming convention
- **Contract 14:** Boid preset migration (by KEY)
- **Contract 19:** Bus index invariant

### Deliverables

| # | File | Action | Description |
|---|------|--------|-------------|
| 1 | `src/config/target_keys_v2.py` | CREATE | Immutable historical 149 keys for migration |
| 2 | `src/config/__init__.py` | MODIFY | 176 targets, new `_build_unified_bus_target_keys()` |
| 3 | `src/boids/boid_engine.py` | MODIFY | `GRID_COLS = 176` |
| 4 | `src/boids/boid_state.py` | MODIFY | Zone ranges: chan=108-147, fx=148-175 |
| 5 | `src/utils/boid_bus.py` | MODIFY | `GRID_TOTAL_COLUMNS = 176`, range checks |
| 6 | `supercollider/core/bus_unification.scd` | MODIFY | 176 targets, arrays, bounds |
| 7 | `supercollider/core/unified_boids.scd` | MODIFY | `~unifiedBusCount = 176` |
| 8 | `tests/test_bus_unification.py` | CREATE | Validation tests |

### Key Changes

**New unified key layout (indices 108-175):**
```python
# Channels: 8 slots × 5 params = 40 (indices 108-147)
chan_1_fx1, chan_1_fx2, chan_1_fx3, chan_1_fx4, chan_1_pan,  # 108-112
chan_2_fx1, chan_2_fx2, chan_2_fx3, chan_2_fx4, chan_2_pan,  # 113-117
# ... through chan_8

# FX Slots: 4 slots × 5 params = 20 (indices 148-167)
fx_slot1_p1, fx_slot1_p2, fx_slot1_p3, fx_slot1_p4, fx_slot1_return,  # 148-152
fx_slot2_p1, fx_slot2_p2, fx_slot2_p3, fx_slot2_p4, fx_slot2_return,  # 153-157
fx_slot3_p1, fx_slot3_p2, fx_slot3_p3, fx_slot3_p4, fx_slot3_return,  # 158-162
fx_slot4_p1, fx_slot4_p2, fx_slot4_p3, fx_slot4_p4, fx_slot4_return,  # 163-167

# Master inserts: 8 params (indices 168-175)
fx_fb_drive, fx_fb_freq1, fx_fb_reso1, fx_fb_freq2,   # 168-171
fx_fb_reso2, fx_fb_syncAmt, fx_fb_harmonics,          # 172-174
fx_heat_drive,                                         # 175
```

### Exit Gate

```bash
# All three must pass
python -c "from src.config import UNIFIED_BUS_TARGET_KEYS; assert len(UNIFIED_BUS_TARGET_KEYS) == 176, f'Got {len(UNIFIED_BUS_TARGET_KEYS)}'"

grep -q "unifiedBusCount = 176" supercollider/core/bus_unification.scd && echo "SC count OK"

pytest tests/test_bus_unification.py -v | cpb
```

### Claude Code Instructions

```
Read UI_REFRESH_SPEC.md Contracts 1, 2, 14, 19.

Create target_keys_v2.py with the IMMUTABLE historical 149 keys.
Update config/__init__.py to build 176 keys with new layout.
Update all Python files that reference GRID_COLS or zone ranges.
Update SC bus_unification.scd with new target count and metadata.
Create test file validating key count and zone boundaries.
```

---

## Phase 1: SC FX Slot Infrastructure

**Session type:** Build  
**Effort:** 3-4 hours  
**Depends on:** Phase 0

### Why Second

SuperCollider audio routing is the foundation. Can't wire Python UI to non-existent buses or SynthDefs.

### Contracts Addressed

- **Contract 4:** Return gain architecture (returns owned by preMasterMixer)
- **Contract 9:** Boot/start order
- **Contract 11:** Return summing point
- **Contract 16:** Empty slot behavior

### Deliverables

| # | File | Action | Description |
|---|------|--------|-------------|
| 1 | `supercollider/core/buses.scd` | MODIFY | Add fx3/fx4 send+return buses |
| 2 | `supercollider/core/fx_slots.scd` | CREATE | Slot manager, `~setFxSlotType`, `~fxSlotSynths` |
| 3 | `supercollider/core/fx_mixer.scd` | MODIFY | 4 returns in preMasterMixer |
| 4 | `supercollider/effects/fx_echo.scd` | CREATE | Canonical p1-p4 slot pattern |
| 5 | `supercollider/effects/fx_reverb.scd` | CREATE | Same pattern |
| 6 | `supercollider/effects/fx_chorus.scd` | CREATE | Same pattern |
| 7 | `supercollider/effects/fx_lofi.scd` | CREATE | Same pattern |
| 8 | `supercollider/effects/fx_empty.scd` | CREATE | Silent passthrough |
| 9 | `supercollider/core/init.scd` | MODIFY | Load order for new files |

### Key Pattern: Canonical FX Slot SynthDef

All FX slot SynthDefs use exactly 4 generic params (p1-p4):

```supercollider
SynthDef(\fxSlot_echo, { |inBus, outBus,
    p1=0.3, p2=0.4, p3=0.7, p4=0.1,  // Generic params
    bypass=0,
    p1Bus=(-1), p2Bus=(-1), p3Bus=(-1), p4Bus=(-1)|
    
    var in = In.ar(inBus, 2);
    
    // SEND-FX BYPASS: stop feeding input, never output dry
    var feed = in * (1 - Lag.kr(bypass, 0.02));
    
    // Bus unification support
    var p1Eff = Select.kr(p1Bus >= 0, [p1, In.kr(p1Bus)]);
    // ... etc
    
    // Map generic to semantic internally
    var time = p1Eff, feedback = p2Eff, tone = p3Eff, wow = p4Eff;
    
    var wet = feed;  // ... actual DSP ...
    
    Out.ar(outBus, wet);  // UNITY OUTPUT - return scaling in preMasterMixer
}).add;
```

### Exit Gate

```bash
# SC boots without errors
sclang -e "\"supercollider/init.scd\".load; \"Boot OK\".postln; 0.exit" 2>&1 | grep -q "Boot OK" && echo "SC boot OK"

# Slot swap works (manual test in SC)
# ~setFxSlotType.(0, \reverb);
# ~setFxSlotType.(0, \echo);
```

### Claude Code Instructions

```
Read UI_REFRESH_SPEC.md Contracts 4, 9, 11, 16 and the Canonical FX Slot SynthDef Pattern section.

Create buses for fx3/fx4 sends and returns.
Create fx_slots.scd with slot manager (~setFxSlotType, ~fxSlotSynths array).
Create FX SynthDefs using canonical p1-p4 pattern.
Update preMasterMixer to sum 4 returns with modulation buses.
Update init.scd load order (fx_slots.scd after buses, before effects).
Ensure ~fxSendGroup executes BEFORE ~masterGroup for correct node order.
```

---

## Phase 2: SC Channel Strip Sends

**Session type:** Build  
**Effort:** 2 hours  
**Depends on:** Phase 1

### Why Here

Channel strips need the new buses from Phase 1 to exist before they can send to them.

### Contracts Addressed

- **Contract 6:** OSC path structure & aliasing
- **Contract 15:** Value domains
- **Contract 20:** Channel strip modulation wiring

### Deliverables

| # | File | Action | Description |
|---|------|--------|-------------|
| 1 | `supercollider/core/channel_strips.scd` | MODIFY | fx3Send, fx4Send params + mod buses |
| 2 | `supercollider/core/osc_handlers.scd` | MODIFY | New send handlers + legacy aliases |

### Key Changes

```supercollider
SynthDef(\channelStrip, { |inBus, outBus, drySumBus,
    fx1SendBus, fx2SendBus, fx3SendBus, fx4SendBus,
    volume=0.8, pan=0.5,
    fx1Send=0, fx2Send=0, fx3Send=0, fx4Send=0,
    // Modulation buses (unified bus wiring)
    fx1ModBus=(-1), fx2ModBus=(-1), fx3ModBus=(-1), fx4ModBus=(-1), panModBus=(-1)|
    
    // Effective values (base or modulated)
    var fx1SendEff = Select.kr(fx1ModBus >= 0, [fx1Send, In.kr(fx1ModBus)]);
    // ... etc for all 5 params
    
    // Send to FX buses (post-fader)
    Out.ar(fx1SendBus, panned * Lag.kr(fx1SendEff, 0.02));
    Out.ar(fx2SendBus, panned * Lag.kr(fx2SendEff, 0.02));
    Out.ar(fx3SendBus, panned * Lag.kr(fx3SendEff, 0.02));
    Out.ar(fx4SendBus, panned * Lag.kr(fx4SendEff, 0.02));
}).add;
```

**OSC Legacy Aliases:**
```supercollider
// Old paths forward to new handlers
/noise/strip/{slot}/echo/send → forwards to fx1 handler
/noise/strip/{slot}/verb/send → forwards to fx2 handler
```

### Exit Gate

```bash
# OSC test
oscsend localhost 57120 /noise/strip/1/fx3 f 0.5
oscsend localhost 57120 /noise/strip/1/fx4 f 0.5

# Verify in SC post window that state arrays updated
# ~stripFx3SendState[0] should be 0.5
```

### Claude Code Instructions

```
Read UI_REFRESH_SPEC.md Contracts 6, 15, 20.

Add fx3Send, fx4Send args to channelStrip SynthDef.
Add mod bus args for all 5 params (fx1-4 + pan).
Wire mod buses using absolute index pattern: ~unifiedBuses.index + ~getBusIndex.(key).
Add state arrays: ~stripFx3SendState, ~stripFx4SendState.
Add OSC handlers for /noise/strip/{slot}/fx3 and /noise/strip/{slot}/fx4.
Add legacy aliases forwarding echo→fx1, verb→fx2.
Pan uses 0..1 on OSC, SC converts to -1..1 exactly once.
```

---

## Phase 3: Python FX Slot GUI

**Session type:** Build  
**Effort:** 3-4 hours  
**Depends on:** Phase 2

### Why Here

GUI needs working SC backend from Phases 1-2 to wire to.

### Contracts Addressed

- **Contract 3:** Generic p1-p4 param model
- **Contract 12:** Widget objectName convention
- **Contract 13:** Turbo presets
- **Contract 17:** INI button behavior
- **Contract 18:** FX type selection guard

### Deliverables

| # | File | Action | Description |
|---|------|--------|-------------|
| 1 | `src/gui/fx_slot.py` | CREATE | Single FX slot widget, flat layout |
| 2 | `src/gui/fx_grid.py` | CREATE | 4-slot horizontal container |
| 3 | `src/config/__init__.py` | MODIFY | FX_TYPES list, FX_PARAM_MAPPING |

### Key Requirements

**Flat layout pattern (CRITICAL):**
```python
FX_SLOT_LAYOUT = {
    'slot_width': 160,
    'slot_height': 150,
    'id_x': 5, 'id_y': 4,
    'selector_x': 30, 'selector_y': 2,
    # ... all positions absolute
}

# NO nested layouts - use move() and setFixedSize()
self.p1_slider = DragSlider(self)
self.p1_slider.move(L['p1_x'], L['slider_y'])
self.p1_slider.setFixedSize(L['slider_w'], L['slider_h'])
```

**Widget objectNames MUST match unified keys exactly:**
```python
# In FXSlot.__init__:
self.p1_slider.setObjectName(f"fx_slot{self.slot_id}_p1")
self.p2_slider.setObjectName(f"fx_slot{self.slot_id}_p2")
self.p3_slider.setObjectName(f"fx_slot{self.slot_id}_p3")
self.p4_slider.setObjectName(f"fx_slot{self.slot_id}_p4")
self.return_slider.setObjectName(f"fx_slot{self.slot_id}_return")
```

**All param widgets must implement:**
```python
def set_boid_glow(self, intensity: float, muted: bool = False) -> None:
    """Set boid glow visualization on this widget."""
    self._boid_glow_intensity = max(0.0, min(1.0, intensity))
    self._boid_glow_muted = muted
    self.update()
```

### Exit Gate

```bash
# Module imports
python -c "from src.gui.fx_slot import FXSlot; from src.gui.fx_grid import FXGrid; print('OK')"

# F9 X-ray in running app: verify objectNames match unified keys
# Click on fx_slot1_p1 slider, should show "fx_slot1_p1" in console
```

### Claude Code Instructions

```
Read UI_REFRESH_SPEC.md Contracts 3, 12, 13, 17, 18 and the Flat Layout Requirements section.

Create fx_slot.py with FLAT absolute positioning (no QVBoxLayout/QHBoxLayout).
Use LAYOUT dict for all positions.
Set objectName == unified_key for all param widgets.
Implement set_boid_glow() on all sliders.
Wire type selector to /noise/fx/slot/{n}/type OSC path.
Wire p1-p4 sliders to /noise/fx/slot/{n}/p{m} OSC paths.
Implement INI button (resets p1-p4 to type defaults).
Implement T1/T2 turbo buttons (apply preset param values).
Create fx_grid.py as simple 4-slot horizontal container.
```

---

## Phase 4: Mixer Panel Updates

**Session type:** Build  
**Effort:** 2 hours  
**Depends on:** Phase 2

### Why Here

Mixer sends need FX slots to exist (for audio routing) but doesn't need Python FX slot GUI.

### Contracts Addressed

- **Contract 2:** Unified key naming (channel sends)
- **Contract 12:** Widget objectName convention
- **Contract 20:** Channel strip modulation wiring (Python side)

### Deliverables

| # | File | Action | Description |
|---|------|--------|-------------|
| 1 | `src/gui/mixer_panel.py` | MODIFY | Add fx3_knob, fx4_knob per channel |

### Key Requirements

**Widget objectNames:**
```python
# In ChannelStrip.__init__:
self._fx1_knob.setObjectName(f"chan_{self.slot_id}_fx1")
self._fx2_knob.setObjectName(f"chan_{self.slot_id}_fx2")
self._fx3_knob.setObjectName(f"chan_{self.slot_id}_fx3")
self._fx4_knob.setObjectName(f"chan_{self.slot_id}_fx4")
self._pan_knob.setObjectName(f"chan_{self.slot_id}_pan")
```

**get_param_widget for boid pulse:**
```python
def get_param_widget(self, param: str) -> Optional[QWidget]:
    """Return widget for param (for boid pulse visualization)."""
    mapping = {
        'fx1': self._fx1_knob, 'fx2': self._fx2_knob,
        'fx3': self._fx3_knob, 'fx4': self._fx4_knob,
        'pan': self._pan_knob,
    }
    # Legacy aliases
    if param == 'echo': param = 'fx1'
    elif param == 'verb': param = 'fx2'
    return mapping.get(param)
```

### Exit Gate

```bash
# Count send widgets (should be 40 = 8 channels × 5 params)
python -c "
from PyQt5.QtWidgets import QApplication
app = QApplication([])
from src.gui.mixer_panel import MixerPanel
m = MixerPanel()
count = sum(1 for i in range(1,9) for p in ['fx1','fx2','fx3','fx4','pan'] 
            if m.findChild(type(m), f'chan_{i}_{p}'))
print(f'Found {count} widgets (expected 40)')
"
```

### Claude Code Instructions

```
Read UI_REFRESH_SPEC.md Contracts 2, 12, 20.

Add fx3_knob and fx4_knob to each channel strip.
Set objectName to match unified keys exactly (chan_1_fx1, not chan_1_fx1_knob).
Wire knobs to OSC paths /noise/strip/{slot}/fx3 and /noise/strip/{slot}/fx4.
Implement get_param_widget() method for boid pulse resolver.
Ensure all knobs implement set_boid_glow().
```

---

## Phase 5: Boid Pulse Visualization Updates

**Session type:** Build  
**Effort:** 2-3 hours  
**Depends on:** Phases 3 and 4

### Why Here

Pulse manager needs all widgets from Phases 3-4 to exist before it can find them.

### Contracts Addressed

- **Contract 8:** Boid pulse resolver & widget mapping
- **Contract 10:** Boid pulse visualization updates
- **Contract 21:** Boid pulse architecture (direct objectName lookup)
- **Contract 22:** Widget set_boid_glow signature

### Deliverables

| # | File | Action | Description |
|---|------|--------|-------------|
| 1 | `src/boids/boid_pulse_manager.py` | MODIFY | Direct findChild lookup, new zone handling |
| 2 | `src/gui/boid_panel.py` | MODIFY | Use GRID_COLS constant |
| 3 | `src/gui/boid_overlay.py` | MODIFY | Use GRID_COLS constant |

### Key Changes

**Simplified pulse manager (Contract 21):**
```python
def _apply_glow(self, col: int, intensity: float) -> None:
    """Apply glow to widget for column."""
    key = UNIFIED_BUS_TARGET_KEYS[col]
    widget = self._main.findChild(QWidget, key)  # Direct lookup!
    if widget and hasattr(widget, 'set_boid_glow'):
        scale = get_boid_scales().get_scale(col)
        muted = self._is_target_muted(col)
        widget.set_boid_glow(intensity * scale, muted)  # ALWAYS pass both args
```

**Updated zone checks in _is_target_muted():**
```python
# FX slot muting
elif zone == 'fx_slot':
    fx_grid = getattr(self._main, 'fx_grid', None)
    if fx_grid:
        slot_widget = fx_grid.get_slot(slot)
        if slot_widget:
            if getattr(slot_widget, 'fx_type', None) == 'empty':
                return True
            if getattr(slot_widget, 'bypassed', False):
                return True
```

### Exit Gate

```python
# Run in debug console with app running
from src.config import UNIFIED_BUS_TARGET_KEYS
from PyQt5.QtWidgets import QWidget

missing = []
for key in UNIFIED_BUS_TARGET_KEYS:
    w = main_frame.findChild(QWidget, key)
    if w is None:
        missing.append(key)
    elif not hasattr(w, 'set_boid_glow'):
        missing.append(f"{key} (no set_boid_glow)")

print(f"Missing: {len(missing)}")  # Must be 0
if missing:
    print(missing[:10])  # Show first 10
```

### Claude Code Instructions

```
Read UI_REFRESH_SPEC.md Contracts 8, 10, 21, 22.

Replace zone-based resolvers with direct findChild(QWidget, key) lookup.
Update _is_target_muted() for fx_slot and fx_master zones.
Update zone ranges in boid_state.py (108-147 channels, 148-175 fx).
Update BoidMiniVisualizer for 176 columns.
Remove old _resolve_fx_widget() and similar methods.
Ensure set_boid_glow() ALWAYS called with both args (intensity, muted).
```

---

## Phase 6: Preset Schema + Migration

**Session type:** Build  
**Effort:** 2 hours  
**Depends on:** Phase 0

### Why Here

Schema changes need the unified key definitions from Phase 0, but don't need GUI widgets.

### Contracts Addressed

- **Contract 7:** Preset schema changes
- **Contract 14:** Boid preset migration

### Deliverables

| # | File | Action | Description |
|---|------|--------|-------------|
| 1 | `src/presets/preset_schema.py` | MODIFY | New dataclasses, version bump |
| 2 | `src/presets/migrations.py` | CREATE | v2→v3 migration functions |
| 3 | `tests/test_preset_migration.py` | CREATE | Round-trip tests |

### Key Changes

**New ChannelState:**
```python
@dataclass
class ChannelState:
    volume: float = 0.8
    pan: float = 0.5
    mute: bool = False
    solo: bool = False
    eq_hi: int = 100
    eq_mid: int = 100
    eq_lo: int = 100
    gain: int = 0
    fx1_send: int = 0  # was echo_send
    fx2_send: int = 0  # was verb_send
    fx3_send: int = 0  # NEW
    fx4_send: int = 0  # NEW
    lo_cut: bool = False
    hi_cut: bool = False
```

**New FXSlotState:**
```python
@dataclass
class FXSlotState:
    fx_type: str = "empty"
    bypass: bool = False
    p1: float = 0.5
    p2: float = 0.5
    p3: float = 0.5
    p4: float = 0.5
    return_level: float = 0.5
    turbo: int = 0  # 0=off, 1=T1, 2=T2
```

**Boid preset migration (by KEY, not index):**
```python
def migrate_boid_preset(data: dict) -> dict:
    """Migrate boid preset from v2 (149) to v3 (176) by key."""
    from src.config import UNIFIED_BUS_TARGET_KEYS
    from src.config.target_keys_v2 import TARGET_KEYS_V2
    
    key_to_index_v3 = {k: i for i, k in enumerate(UNIFIED_BUS_TARGET_KEYS)}
    
    if 'target_columns' in data:
        new_cols = []
        for old_col in data['target_columns']:
            if old_col < len(TARGET_KEYS_V2):
                old_key = TARGET_KEYS_V2[old_col]
                new_key = KEY_ALIAS.get(old_key, old_key)
                if new_key in key_to_index_v3:
                    new_cols.append(key_to_index_v3[new_key])
        data['target_columns'] = new_cols
    
    return data
```

### Exit Gate

```bash
pytest tests/test_preset_migration.py -v | cpb

# Round-trip test: save → load → compare (ignoring auto-generated fields)
```

### Claude Code Instructions

```
Read UI_REFRESH_SPEC.md Contracts 7, 14.

Update ChannelState: rename echo_send→fx1_send, verb_send→fx2_send, add fx3/fx4.
Create FXSlotState dataclass with fx_type, bypass, p1-p4, return_level, turbo.
Bump PRESET_VERSION to v3.
Create migrate_v2_to_v3() for preset migration.
Create migrate_boid_preset() using KEY_ALIAS mapping.
Add version check on load (reject unversioned boid patterns).
Create tests for round-trip and migration.
```

---

## Phase 7: Main Frame Integration

**Session type:** Build  
**Effort:** 3-4 hours  
**Depends on:** All previous phases

### Why Last

This wires everything together. All components must exist first.

### Contracts Addressed

- **Contract 11:** Return summing point (partial—UI wiring)

### Deliverables

| # | File | Action | Description |
|---|------|--------|-------------|
| 1 | `src/gui/master_chain.py` | CREATE | Heat + DualFilter + EQ + Comp + Output container |
| 2 | `src/gui/main_frame.py` | MODIFY | New bottom bar layout, replace inline_fx_strip |
| 3 | `src/gui/inline_fx_strip.py` | DEPRECATE | Mark for removal |
| 4 | `src/gui/master_section.py` | DEPRECATE | Absorbed into master_chain |

### Key Changes

**Bottom bar layout:**
```
┌────────┬────────┬────────┬────────┬──────────────────────────┐
│ FX 1   │ FX 2   │ FX 3   │ FX 4   │      MASTER CHAIN        │
│ SLOT   │ SLOT   │ SLOT   │ SLOT   │  HEAT│FILT│EQ│COMP│OUT  │
└────────┴────────┴────────┴────────┴──────────────────────────┘
```

**Master chain objectNames:**
```python
# Must match unified keys exactly
fx_heat_drive
fx_fb_drive, fx_fb_freq1, fx_fb_reso1, fx_fb_freq2, fx_fb_reso2, fx_fb_syncAmt, fx_fb_harmonics
```

### Exit Gate

```bash
# Full app launch
python main.py

# F9 X-ray: no missing boid targets (0 missing)
# Manual: full session test
# - Load pack
# - Adjust FX sends
# - Swap FX types
# - Verify audio routing
# - Save/load preset
```

### Claude Code Instructions

```
Read UI_REFRESH_SPEC.md visual design section and Contract 11.

Create master_chain.py with Heat, DualFilter, EQ, Comp, Output sections.
Use flat layout (no nested QBoxLayouts).
Set all param widget objectNames to match unified keys.
Update main_frame.py bottom bar:
  - Replace inline_fx_strip with fx_grid
  - Add master_chain to right of fx_grid
Wire all signals to controllers.
Update right panel layout (Boids + Mixer vertical stack).
Test full app launch and audio routing.
```

---

## Summary Table

| Phase | Focus | Effort | Exit Gate |
|-------|-------|--------|-----------|
| **0** | Bus unification (149→176) | 2-3h | `assert len(UNIFIED_BUS_TARGET_KEYS) == 176` |
| **1** | SC FX slot infrastructure | 3-4h | SC boots, slots swap |
| **2** | SC channel strip sends | 2h | OSC sends work |
| **3** | Python FX slot GUI | 3-4h | Widgets exist, glows work |
| **4** | Mixer panel updates | 2h | 40 send widgets found |
| **5** | Boid pulse updates | 2-3h | 0 missing targets |
| **6** | Preset schema + migration | 2h | Round-trip test passes |
| **7** | Main frame integration | 3-4h | Full session test |

**Total: ~20-24 hours across 7 sessions**

---

## Session Workflow

For each phase:

1. **Start Claude Code session** with session type (Build)
2. **Read spec sections** listed in "Contracts Addressed"
3. **Check current state** of files before editing
4. **Implement deliverables** following flat layout pattern
5. **Run exit gate** before marking complete
6. **Commit** with descriptive message: `"UI Refresh Phase N: {focus}"`

**Don't proceed to next phase until exit gate passes.**

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Phase 0 bus indices wrong | Comprehensive test suite validates all 176 keys |
| SC node order breaks audio | Explicit group structure in fx_slots.scd |
| Widget objectNames don't match | F9 X-ray verification at each GUI phase |
| Preset migration loses data | Migration by KEY not index; historical keys frozen |
| Boid pulse finds wrong widgets | Direct findChild replaces complex resolvers |

---

## Quick Reference: Unified Keys

**Indices 0-107:** UNCHANGED (gen_core, gen_custom, mod_slots)

**Indices 108-147:** Channels (40 params)
```
chan_{1-8}_fx{1-4}, chan_{1-8}_pan
```

**Indices 148-167:** FX Slots (20 params)
```
fx_slot{1-4}_p{1-4}, fx_slot{1-4}_return
```

**Indices 168-175:** Master Inserts (8 params)
```
fx_fb_drive, fx_fb_freq1, fx_fb_reso1, fx_fb_freq2,
fx_fb_reso2, fx_fb_syncAmt, fx_fb_harmonics, fx_heat_drive
```
