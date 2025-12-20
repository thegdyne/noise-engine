# Mod Matrix Rollout Plan

**Created:** December 17, 2025  
**Status:** Ready to Execute  
**Total Phases:** 13 (Phase 0-12)  
**Estimated Total:** 22-32 sessions

---

## Current State Summary

### What Exists
- ✅ Mod source panel UI (Python) - 4 slots in 2×2 grid
- ✅ LFO SynthDef (3 outputs, clock-synced, 8 waveforms)
- ✅ Sloth SynthDef (3 outputs, chaos algorithm)
- ✅ Scope widget (3 traces, 30fps)
- ✅ Config constants (`MOD_SLOT_COUNT`, `MOD_BUS_COUNT`, etc.)
- ✅ Generator cycle concept (`["Empty", "LFO", "Sloth"]`)

### What's Broken
- ❌ Python sends OSC → nowhere (no SC handlers)
- ❌ SC mod buses allocated but nothing writes to them
- ❌ Scopes show nothing (no real data)
- ❌ Type selector UI missing (slots fixed to defaults)

### What's Missing
- ❌ 4th output per slot (quadrature)
- ❌ OSC handlers for mod messages
- ❌ Mod routing system
- ❌ Matrix window
- ❌ Modulation visualisation on sliders

---

## Phase 0: Quadrature Expansion

**Goal:** Expand from 3 to 4 outputs per mod slot. 16 total mod buses.

**Duration:** 1-2 sessions

### Config Changes

**File:** `src/config/__init__.py`

```python
# BEFORE
MOD_OUTPUTS_PER_SLOT = 3
MOD_BUS_COUNT = 12

# AFTER
MOD_OUTPUTS_PER_SLOT = 4
MOD_BUS_COUNT = 16
MOD_LFO_OUTPUTS = ["A", "B", "C", "D"]
MOD_SLOTH_OUTPUTS = ["X", "Y", "Z", "R"]
MOD_LFO_PHASE_PATTERNS = {
    "QUAD": [0, 90, 180, 270],
    "PAIR": [0, 0, 180, 180],
    "SPREAD": [0, 45, 180, 225],
    "TIGHT": [0, 22, 45, 67],
    "WIDE": [0, 120, 180, 300],
    "SYNC": [0, 0, 0, 0],
}
MOD_LFO_ROTATE_STEPS = 24  # 15° each
```

### LFO SynthDef Changes

**File:** `supercollider/core/mod_lfo.scd`

```supercollider
SynthDef(\modLFO, {
    arg outA, outB, outC, outD,  // 4 output buses (was 3)
        rate=0, shape=0.5, 
        waveA=0, waveB=0, waveC=0, waveD=0,  // per-output waveform
        phaseA=0, phaseB=2, phaseC=4, phaseD=6,  // 0°, 90°, 180°, 270°
        polA=1, polB=1, polC=1, polD=1,
        pattern=0, rotate=0;  // NEW: pattern preset, rotation
    
    // ... implementation ...
    
    Out.kr(outA, sigA);
    Out.kr(outB, sigB);
    Out.kr(outC, sigC);
    Out.kr(outD, sigD);  // NEW
}).add;
```

### Sloth SynthDef Changes

**File:** `supercollider/core/mod_sloth.scd`

```supercollider
SynthDef(\modSloth, {
    arg outX, outY, outZ, outR,  // 4 outputs (was 3)
        mode=0, bias=0.5,
        polX=1, polY=1, polZ=1, polR=1;
    
    // Existing X, Y, Z chaos outputs...
    
    // NEW: R = rectified sum (gate-like bursts)
    var r = max(0, y + z - x);  // fires when slow > fast
    
    Out.kr(outX, x);
    Out.kr(outY, y);
    Out.kr(outZ, z);
    Out.kr(outR, r);  // NEW
}).add;
```

### UI Changes

**File:** `src/gui/mod_source_slot.py`

- [ ] Add 4th output row (D for LFO, R for Sloth)
- [ ] Add PAT (pattern) CycleButton for LFO
- [ ] Add ROT (rotate) slider for LFO
- [ ] Update output labels based on generator type

**File:** `src/gui/mod_scope.py`

- [ ] Support 4 traces
- [ ] Add 4th colour to skin system

**File:** `src/config/skin.py`

- [ ] Add `scope_trace_4` colour (suggest: magenta or white)

### SC Bus Allocation

**File:** `supercollider/core/mod_buses.scd`

```supercollider
// BEFORE
~modBuses = Bus.control(s, 12);

// AFTER  
~modBuses = Bus.control(s, 16);
```

### JSON Config Updates

**File:** `supercollider/mod_generators/lfo.json`

```json
{
  "name": "LFO",
  "outputs": 4,
  "params": [
    {"key": "rate", "label": "RATE", "type": "stepped", "steps": 12, "default": 6},
    {"key": "shape", "label": "SHAP", "type": "continuous", "default": 0.5},
    {"key": "pattern", "label": "PAT", "type": "stepped", "steps": 6, "default": 0},
    {"key": "rotate", "label": "ROT", "type": "stepped", "steps": 24, "default": 0}
  ]
}
```

**File:** `supercollider/mod_generators/sloth.json`

```json
{
  "name": "Sloth", 
  "outputs": 4,
  "output_labels": ["X", "Y", "Z", "R"],
  "params": [
    {"key": "mode", "label": "MODE", "type": "stepped", "steps": 3, "default": 0},
    {"key": "bias", "label": "BIAS", "type": "continuous", "default": 0.5}
  ]
}
```

### Deliverables Checklist

- [ ] Config updated: 4 outputs, 16 buses
- [ ] LFO SynthDef: 4 outputs, pattern, rotate
- [ ] Sloth SynthDef: 4 outputs including R
- [ ] UI: 4 output rows per slot
- [ ] UI: PAT and ROT controls for LFO
- [ ] Scope: 4 traces with 4th colour
- [ ] JSON configs updated
- [ ] Bus allocation: 16 buses

### Success Criteria

- [ ] LFO scope shows 4 traces at 0°/90°/180°/270°
- [ ] Sloth R output pulses irregularly (visible in scope)
- [ ] Pattern button cycles through QUAD/PAIR/SPREAD/TIGHT/WIDE/SYNC
- [ ] Rotate control shifts all phases together

---

## Phase 1: Wire Mod Sources

**Goal:** Mod sources actually output CV to buses. Scopes show real waveforms.

**Duration:** 1 session

### New Files

**File:** `supercollider/core/mod_osc.scd`

OSC handlers for mod slot messages:

```supercollider
// Slot type change
OSCdef(\modSlotType, { |msg|
    var slot = msg[1].asInteger;
    var type = msg[2].asSymbol;
    ~setModSlotType.(slot, type);
}, '/noise/mod/slot/type');

// LFO parameters
OSCdef(\modLFORate, { |msg|
    var slot = msg[1].asInteger;
    var value = msg[2].asFloat;
    ~modSynths[slot].set(\rate, value);
}, '/noise/mod/lfo/rate');

OSCdef(\modLFOShape, { |msg|
    var slot = msg[1].asInteger;
    var value = msg[2].asFloat;
    ~modSynths[slot].set(\shape, value);
}, '/noise/mod/lfo/shape');

// ... pattern, rotate, per-output wave/phase/polarity ...

// Sloth parameters
OSCdef(\modSlothMode, { |msg|
    var slot = msg[1].asInteger;
    var value = msg[2].asInteger;
    ~modSynths[slot].set(\mode, value);
}, '/noise/mod/sloth/mode');

// ... bias, per-output polarity ...
```

**File:** `supercollider/core/mod_slots.scd`

Slot management functions:

```supercollider
~modSynths = Array.newClear(4);

~startModSlot = { |slot, type|
    var busOffset = slot * 4;
    var buses = (0..3).collect { |i| ~modBuses.index + busOffset + i };
    
    ~modSynths[slot].free;
    
    switch(type,
        \LFO, {
            ~modSynths[slot] = Synth(\modLFO, [
                \outA, buses[0], \outB, buses[1],
                \outC, buses[2], \outD, buses[3]
            ]);
        },
        \Sloth, {
            ~modSynths[slot] = Synth(\modSloth, [
                \outX, buses[0], \outY, buses[1],
                \outZ, buses[2], \outR, buses[3]
            ]);
        }
    );
    
    ("Started" + type + "in mod slot" + slot).postln;
};

~freeModSlot = { |slot|
    ~modSynths[slot].free;
    ~modSynths[slot] = nil;
};

~initModSlots = {
    // Default: LFO/Sloth/LFO/Sloth
    ~startModSlot.(0, \LFO);
    ~startModSlot.(1, \Sloth);
    ~startModSlot.(2, \LFO);
    ~startModSlot.(3, \Sloth);
};
```

### Scope Data Flow

**SC side:** Send bus values to Python for scope display

```supercollider
~modScopeRoutine = Routine({
    loop {
        4.do { |slot|
            var busOffset = slot * 4;
            var values = (0..3).collect { |i|
                ~modBuses.subBus(busOffset + i).getSynchronous;
            };
            NetAddr.localAddr.sendMsg('/noise/mod/scope', slot, *values);
        };
        (1/30).wait;  // 30fps
    }
}).play;
```

**Python side:** `src/gui/mod_scope.py` receives `/noise/mod/scope` and updates display

### Deliverables Checklist

- [ ] `mod_osc.scd` - all OSC handlers
- [ ] `mod_slots.scd` - start/free/init functions
- [ ] SC loads mod slots on startup
- [ ] Scope receives real bus values
- [ ] Python parameter changes reach SC

### Success Criteria

- [ ] Move RATE slider → see LFO speed change in scope
- [ ] Move MODE slider → see Sloth character change
- [ ] SC post window shows "Started LFO in mod slot 0" on boot
- [ ] All 4 traces animate in scope

---

## Phase 2: Mod Bus → Generator Param (Hardcoded Test)

**Goal:** Prove modulation works end-to-end before building UI.

**Duration:** 1 session

### New File

**File:** `supercollider/core/mod_apply.scd`

```supercollider
~applyModulation = { |paramBus, modBusIndex, depth|
    // Read current param value
    // Read mod bus value
    // Write modulated value to param bus
    // This runs in a Routine or is triggered by param changes
};

// HARDCODED TEST - remove after Phase 3
~testModulation = {
    "Testing: LFO bus 0 → Gen 1 cutoff at 50%".postln;
    // Wire mod bus 0 to gen 1 cutoff param bus
    // depth = 0.5
};
```

### Test Procedure

1. Boot Noise Engine
2. Load a generator in slot 1 (anything with a filter)
3. Run `~testModulation.()` in SC
4. Hear cutoff being modulated by LFO
5. Change LFO rate → modulation speed changes

### Deliverables Checklist

- [ ] `mod_apply.scd` with `~applyModulation` helper
- [ ] Hardcoded test routes LFO → cutoff
- [ ] Modulation audible

### Success Criteria

- [ ] Filter sweeps in sync with LFO
- [ ] Changing LFO rate changes sweep speed
- [ ] No UI interaction needed - pure SC test

---

## Phase 3: Connection Data Model

**Goal:** Define how mod routing connections are stored and transmitted.

**Duration:** 1-2 sessions

### Python Data Model

**File:** `src/gui/mod_routing_state.py`

```python
from dataclasses import dataclass
from typing import List, Dict, Optional
from PyQt5.QtCore import QObject, pyqtSignal

@dataclass
class ModConnection:
    source_bus: int      # 0-15
    target_slot: int     # 1-8 (generator slot)
    target_param: str    # 'cutoff', 'frequency', etc.
    depth: float         # -1.0 to +1.0
    enabled: bool = True

class ModRoutingState(QObject):
    connection_added = pyqtSignal(ModConnection)
    connection_removed = pyqtSignal(int, int, str)  # bus, slot, param
    connection_changed = pyqtSignal(ModConnection)
    
    def __init__(self):
        super().__init__()
        self._connections: List[ModConnection] = []
    
    def add_connection(self, conn: ModConnection) -> None: ...
    def remove_connection(self, source_bus: int, target_slot: int, target_param: str) -> None: ...
    def set_depth(self, source_bus: int, target_slot: int, target_param: str, depth: float) -> None: ...
    def set_enabled(self, source_bus: int, target_slot: int, target_param: str, enabled: bool) -> None: ...
    def get_connections_for_bus(self, bus: int) -> List[ModConnection]: ...
    def get_connections_for_target(self, slot: int, param: str) -> List[ModConnection]: ...
    def to_dict(self) -> Dict: ...  # For preset saving
    def from_dict(self, data: Dict) -> None: ...  # For preset loading
```

### OSC Message Design

**File:** `src/config/__init__.py` (add to existing)

```python
# Mod routing OSC paths
OSC_MOD_ROUTE_ADD = '/noise/mod/route/add'        # [source_bus, slot, param, depth]
OSC_MOD_ROUTE_REMOVE = '/noise/mod/route/remove'  # [source_bus, slot, param]
OSC_MOD_ROUTE_DEPTH = '/noise/mod/route/depth'    # [source_bus, slot, param, depth]
OSC_MOD_ROUTE_ENABLE = '/noise/mod/route/enable'  # [source_bus, slot, param, 0/1]
```

### SC-Side Storage

**File:** `supercollider/core/mod_routing.scd`

```supercollider
// Storage: slot -> param -> [[modBus, depth, enabled], ...]
~modRouting = Dictionary.new;

// Initialize empty routing for all slots/params
~initModRouting = {
    8.do { |slot|
        ~modRouting[slot] = Dictionary.new;
    };
};

// OSC handlers
OSCdef(\modRouteAdd, { |msg|
    var bus = msg[1].asInteger;
    var slot = msg[2].asInteger;
    var param = msg[3].asSymbol;
    var depth = msg[4].asFloat;
    
    ~addModRoute.(bus, slot, param, depth);
}, '/noise/mod/route/add');

// ... remove, depth, enable handlers ...
```

### Preset JSON Schema

```json
{
  "modulation": {
    "connections": [
      {
        "source_bus": 0,
        "target_slot": 1,
        "target_param": "cutoff",
        "depth": 0.5,
        "enabled": true
      }
    ]
  }
}
```

### Deliverables Checklist

- [ ] `ModConnection` dataclass
- [ ] `ModRoutingState` class with signals
- [ ] OSC paths in config
- [ ] SC `mod_routing.scd` with storage and handlers
- [ ] Preset schema defined
- [ ] State sync on connect (Python → SC)

### Success Criteria

- [ ] Programmatically add connection → SC receives and stores
- [ ] Programmatically remove connection → SC removes
- [ ] Reconnect to SC → all connections restored
- [ ] Export/import via dict works

---

## Phase 4: Matrix Window - Basic Grid

**Goal:** Visual matrix window with clickable cells.

**Duration:** 2-3 sessions

### New Files

**File:** `src/gui/mod_matrix_window.py`

```python
class ModMatrixWindow(QMainWindow):
    def __init__(self, routing_state: ModRoutingState):
        # 16 rows (mod buses) × N columns (gen params)
        # Row headers: dynamic based on slot types
        # Column headers: G1 FRQ, G1 CUT, etc.
        # Grid of ModMatrixCell widgets
        pass
    
    def update_row_labels(self, slot: int, gen_type: str): ...
    def on_cell_clicked(self, bus: int, slot: int, param: str): ...
```

**File:** `src/gui/mod_matrix_cell.py`

```python
class ModMatrixCell(QWidget):
    clicked = pyqtSignal()
    
    def __init__(self, bus: int, slot: int, param: str):
        self.connected = False
        self.enabled = True
        self.depth = 0.0
        self.source_type = 'lfo'  # for colour
    
    def paintEvent(self, event):
        # Draw filled circle if connected
        # Draw empty circle if connected but disabled
        # Colour based on source type
        pass
```

### Layout Spec

```
Window size: ~1200 × 600 (resizable)
Row height: 24px
Column width: 28px
Row header width: 80px
Column header height: 40px (two lines: "G1" / "FRQ")

Separators:
- Horizontal line every 4 rows (between mod slots)
- Vertical line every 10 columns (between generators)
```

### Integration

**File:** `src/gui/main_frame.py`

- [ ] Add menu item: View → Mod Matrix (Cmd+M)
- [ ] Store matrix window reference
- [ ] Pass routing state to matrix

### Deliverables Checklist

- [ ] `ModMatrixWindow` class
- [ ] `ModMatrixCell` class
- [ ] Dynamic row labels from slot types
- [ ] Column headers for all gen params
- [ ] Click to toggle connection
- [ ] Visual feedback (filled/empty/disabled)
- [ ] Menu item and shortcut
- [ ] Window remembers position/size

### Success Criteria

- [ ] Cmd+M opens matrix window
- [ ] Click cell → connection created → audio responds
- [ ] Click again → connection removed
- [ ] Row labels match loaded generator types
- [ ] Cells colour-coded by source type

---

## Phase 5: Depth Control

**Goal:** Set per-connection modulation depth.

**Duration:** 1-2 sessions

### New File

**File:** `src/gui/mod_depth_popup.py`

```python
class ModDepthPopup(QDialog):
    depth_changed = pyqtSignal(float)
    remove_requested = pyqtSignal()
    disable_requested = pyqtSignal()
    
    def __init__(self, connection: ModConnection):
        # Header: "LFO 1 A → Gen 1 Cutoff"
        # Horizontal slider: -100% to +100%
        # Current value display
        # Buttons: Disable, Remove, OK
        pass
```

### Cell Visual Feedback

Update `ModMatrixCell.paintEvent()`:
- Circle size reflects depth magnitude
- Or: circle fill intensity reflects depth
- Negative depth: different colour or indicator

### Context Menu

Right-click on cell:
- Set Depth...
- Disable / Enable
- Remove
- Copy to Row (same depth to all destinations)
- Copy to Column (same source to all params)

### Deliverables Checklist

- [ ] `ModDepthPopup` dialog
- [ ] Click connected cell → popup appears
- [ ] Slider controls depth -100% to +100%
- [ ] Visual feedback in cell
- [ ] Right-click context menu
- [ ] Copy operations

### Success Criteria

- [ ] Set LFO→Cutoff to +80%, LFO→Res to -20%
- [ ] Hear different modulation depths
- [ ] Cell visuals reflect depth

---

## Phase 6: Visual Polish & Interaction

**Goal:** Matrix feels like a professional instrument.

**Duration:** 2 sessions

### Keyboard Navigation

| Key | Action |
|-----|--------|
| Arrow keys | Navigate cells |
| Space | Toggle connection |
| Delete | Remove connection |
| D | Open depth editor |
| 1-9 | Quick depth (10%-90%) |
| 0 | Set depth to 0% (disable) |
| - | Invert depth sign |
| Escape | Close popup / deselect |

### Drag Operations

- Drag across row → assign same source to multiple destinations
- Shift+drag → copy depth value to dragged cells
- Alt+drag → remove connections from dragged cells

### Active Highlighting

- Row pulses/glows when mod source outputting non-zero
- Column highlights when generator is active
- Selected cell has focus ring

### Window Behaviour

- Remembers position/size (QSettings)
- "Always on top" toggle in menu
- Minimum size enforced
- Sensible resize behaviour

### Deliverables Checklist

- [ ] Full keyboard navigation
- [ ] Drag operations
- [ ] Active source highlighting
- [ ] Active generator highlighting
- [ ] Selection state
- [ ] Window persistence
- [ ] Always on top option

### Success Criteria

- [ ] Can route entire patch without mouse
- [ ] Drag across row creates multiple connections
- [ ] Visual feedback shows what's active

---

## Phase 7: Modulation Visualisation on Sliders

**Goal:** See modulation happening on generator parameter sliders.

**Duration:** 2-3 sessions

### Extended Slider Class

**File:** `src/gui/modulated_slider.py`

```python
class ModulatedSlider(FaderSlider):
    def __init__(self, ...):
        self.mod_min = None
        self.mod_max = None
        self.mod_current = None
        self.mod_colour = None
    
    def set_modulation_range(self, min_val: float, max_val: float, colour: QColor):
        self.mod_min = min_val
        self.mod_max = max_val
        self.mod_colour = colour
        self.update()
    
    def set_modulated_value(self, value: float):
        self.mod_current = value
        self.update()
    
    def clear_modulation(self):
        self.mod_min = self.mod_max = self.mod_current = None
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        if self.mod_min is not None:
            # Draw range brackets
            # Draw current value line (animated)
            pass
```

### SC → Python Data Flow

**SC side:**

```supercollider
// Batch modulated values at 30fps
~modVisualisationRoutine = Routine({
    loop {
        var values = [];
        // Collect all modulated param values
        // Only include actively modulated params
        NetAddr.localAddr.sendMsg('/noise/mod/values', *values);
        (1/30).wait;
    }
}).play;
```

**Python side:**

```python
# In osc_bridge.py
def handle_mod_values(self, *values):
    # Route to appropriate sliders
    # Only update visible/active sliders
    pass
```

### Integration

**File:** `src/gui/generator_slot_builder.py`

- [ ] Use `ModulatedSlider` instead of `FaderSlider` for modulatable params
- [ ] Connect to routing state for range updates
- [ ] Connect to OSC handler for value updates

### Deliverables Checklist

- [ ] `ModulatedSlider` class
- [ ] Range bracket drawing
- [ ] Animated current value line
- [ ] SC sends batched values at 30fps
- [ ] Python routes to correct sliders
- [ ] Colour matches source type
- [ ] Only active modulations visualised

### Success Criteria

- [ ] Route LFO to cutoff → see cyan brackets on slider
- [ ] Brackets show modulation range
- [ ] Line animates with LFO
- [ ] Multiple sources → combined range shown

---

## Phase 8: Multi-Source Summation

**Goal:** Multiple mod sources can target the same parameter.

**Duration:** 1-2 sessions

### Summation Modes

```python
class SummationMode(Enum):
    ADD = 'add'        # Sum values, clip to range
    AVERAGE = 'avg'    # Average values
    MAX = 'max'        # Highest absolute value wins
```

### SC Implementation

```supercollider
~calculateModulation = { |slot, param|
    var routes = ~modRouting[slot][param];
    var values = routes.collect { |route|
        var bus = route[0];
        var depth = route[1];
        var enabled = route[2];
        if(enabled, {
            ~modBuses.subBus(bus).getSynchronous * depth
        }, { 0 });
    };
    
    switch(~summationMode,
        \add, { values.sum.clip(-1, 1) },
        \avg, { values.mean },
        \max, { values.maxItem({ |v| v.abs }) }
    );
};
```

### Matrix Visual

When multiple sources connected to same destination:
- Show stacked dots or connection count
- Tooltip shows all sources and depths

### Deliverables Checklist

- [ ] Summation mode selector (global or per-destination)
- [ ] SC-side summing logic
- [ ] Matrix shows multi-connection state
- [ ] Slider visualisation shows combined range

### Success Criteria

- [ ] LFO + Sloth both on cutoff
- [ ] Hear combined modulation
- [ ] Visualisation shows combined range

---

## Phase 9: MIDI as Mod Source

**Goal:** MIDI CCs appear as mod sources in the matrix.

**Duration:** 2 sessions

### Additional Mod Sources

| Source | Bus Index | Notes |
|--------|-----------|-------|
| Velocity | 16 | Per-note, captured on note-on |
| Mod Wheel | 17 | CC1, continuous |
| Aftertouch | 18 | Channel pressure |
| Expression | 19 | CC11, continuous |
| Assignable | 20-23 | User picks CC number |

### SC Implementation

```supercollider
// MIDI CC to mod bus
MIDIdef.cc(\modWheel, { |val|
    ~modBuses.subBus(17).set(val / 127);
}, 1);  // CC1

MIDIdef.cc(\expression, { |val|
    ~modBuses.subBus(19).set(val / 127);
}, 11);  // CC11
```

### Matrix Extension

- Additional rows below internal sources
- Purple colour coding
- MIDI learn option: click cell, move controller, auto-assign

### Deliverables Checklist

- [ ] MIDI sources write to mod buses
- [ ] Matrix shows MIDI rows
- [ ] Purple colour coding
- [ ] Velocity captured per-note
- [ ] Assignable CC configuration
- [ ] Optional: MIDI learn

### Success Criteria

- [ ] Move mod wheel → see value in matrix
- [ ] Route mod wheel to cutoff → hear response
- [ ] Velocity affects per-note modulation

---

## Phase 10: Preset Integration

**Goal:** Matrix state saves/loads with presets.

**Duration:** 1 session

### Preset Schema

```json
{
  "name": "My Preset",
  "generators": [...],
  "mixer": {...},
  "master": {...},
  "modulation": {
    "connections": [
      {"source_bus": 0, "target_slot": 1, "target_param": "cutoff", "depth": 0.5, "enabled": true},
      {"source_bus": 4, "target_slot": 2, "target_param": "frequency", "depth": -0.3, "enabled": true}
    ],
    "summation_mode": "add"
  }
}
```

### Load Behaviour

Options:
- Replace all: Clear existing, load new
- Merge: Add new connections, keep existing
- Keep modulation: Load sound but preserve routing

### Deliverables Checklist

- [ ] Save connections to preset JSON
- [ ] Load connections from preset
- [ ] Matrix updates on preset load
- [ ] Audio routes update on preset load
- [ ] "Init" clears all connections
- [ ] Optional: "Keep modulation" checkbox

### Success Criteria

- [ ] Save preset with complex routing
- [ ] Load on fresh boot → sounds identical
- [ ] Matrix reflects loaded state

---

## Phase 11: Meta-Modulation

**Goal:** Modulate the depth of a mod route with another source.

**Duration:** 2-3 sessions

### Concept

Instead of: LFO 1 → Cutoff at 50% (fixed)
Have: Mod Wheel → (LFO 1 → Cutoff depth)

As mod wheel increases, LFO effect intensifies.

### Implementation

- Depth becomes a bus, not a static value
- Meta-mod source writes to depth bus
- Matrix shows meta-routes differently (dashed line?)

### Deliverables Checklist

- [ ] "Mod depth" as virtual destination
- [ ] UI for assigning meta-mod
- [ ] SC depth buses
- [ ] Matrix visualisation for meta-routes

### Success Criteria

- [ ] Mod wheel at 0 → no LFO effect
- [ ] Mod wheel at 127 → full LFO sweep
- [ ] Smooth transition between

---

## Phase 12: Envelope Follower

**Goal:** External audio drives modulation.

**Duration:** 2 sessions

### New Mod Generator Type

```python
MOD_GENERATOR_CYCLE = ["Empty", "LFO", "Sloth", "EnvFollow"]
```

### EnvFollow SynthDef

```supercollider
SynthDef(\modEnvFollow, {
    arg outA, outB, outC, outD,
        input=0,  // 0=AudioIn, 1-8=Gen, 9=Master
        attack=0.01, release=0.1;
    
    var sig = Select.ar(input, [...]);
    var env = Amplitude.kr(sig, attack, release);
    
    Out.kr(outA, env);
    // B, C, D could be filtered/delayed versions
}).add;
```

### Deliverables Checklist

- [ ] EnvFollow SynthDef
- [ ] Input selector UI
- [ ] Attack/Release controls
- [ ] Add to generator cycle
- [ ] Matrix row labels for EnvFollow

### Success Criteria

- [ ] Drum loop in → envelope drives cutoff
- [ ] Different attack/release settings change character

---

## Summary

| Phase | Description | Sessions | Cumulative |
|-------|-------------|----------|------------|
| 0 | Quadrature Expansion | 1-2 | 1-2 |
| 1 | Wire Mod Sources | 1 | 2-3 |
| 2 | Hardcoded Mod Test | 1 | 3-4 |
| 3 | Connection Data Model | 1-2 | 4-6 |
| 4 | Matrix Window | 2-3 | 6-9 |
| 5 | Depth Control | 1-2 | 7-11 |
| 6 | Visual Polish | 2 | 9-13 |
| 7 | Slider Visualisation | 2-3 | 11-16 |
| 8 | Multi-Source Summation | 1-2 | 12-18 |
| 9 | MIDI Sources | 2 | 14-20 |
| 10 | Preset Integration | 1 | 15-21 |
| 11 | Meta-Modulation | 2-3 | 17-24 |
| 12 | Envelope Follower | 2 | 19-26 |

**Minimum viable matrix:** Phases 0-5 (7-11 sessions)
**Full featured:** All phases (19-26 sessions)

---

## Files Reference

### New Files

```
src/gui/mod_matrix_window.py
src/gui/mod_matrix_cell.py
src/gui/mod_depth_popup.py
src/gui/mod_routing_state.py
src/gui/modulated_slider.py

supercollider/core/mod_osc.scd
supercollider/core/mod_slots.scd
supercollider/core/mod_routing.scd
supercollider/core/mod_apply.scd
```

### Modified Files

```
src/config/__init__.py          # Bus counts, OSC paths
src/config/skin.py              # 4th trace colour
src/gui/mod_source_slot.py      # 4 outputs, PAT/ROT
src/gui/mod_scope.py            # 4 traces
src/gui/main_frame.py           # Matrix menu item
src/gui/generator_slot_builder.py  # ModulatedSlider
src/audio/osc_bridge.py         # Mod value routing

supercollider/core/mod_lfo.scd      # 4 outputs
supercollider/core/mod_sloth.scd    # 4 outputs
supercollider/core/mod_buses.scd    # 16 buses
supercollider/mod_generators/lfo.json
supercollider/mod_generators/sloth.json
```
