# Relative Modulation Rollout Plan

**Goal:** Implement hardware-style modulation where the slider position is the center point, with depth/amount/polarity controls.

**Estimated Duration:** 6 phases, ~1 session each

---

## Overview

### Current Behaviour (Problem)
- Base value captured once when route created
- Moving slider while modulated doesn't update center point
- Single "depth" control (-100% to +100%)
- Negative depth = inverted

### New Behaviour (Target)
- Slider position = live center point of modulation
- Dual bus architecture (user intent vs modulated output)
- Three controls: Depth (range), Amount (VCA), Polarity (bi/uni)
- Immediate response when slider moved

### Key Formulas

**Single source modulation:**
```
s = mod signal ∈ [-1, +1]
r = depth × amount ∈ [0, 1]  (effective range)
c = center (slider position, normalized 0-1)
inv = invert flag (1 or -1)

Apply invert first: s' = s × inv

Polarity delta functions:
  bipolar: delta = s' × r
  uni+   : delta = ((s' + 1) × 0.5) × r      // maps -1..+1 to 0..r
  uni-   : delta = -((s' + 1) × 0.5) × r     // maps -1..+1 to -r..0

output = clamp(c + delta, 0, 1)
```

**Multi-source bracket calculation:**
```
For each source i with range r_i and polarity_i:

  bipolar: upFactor=1, downFactor=1
  uni+   : upFactor=1, downFactor=0
  uni-   : upFactor=0, downFactor=1

up   = Σ (r_i × upFactor_i)
down = Σ (r_i × downFactor_i)

bracket_min = clamp(c - down, 0, 1)
bracket_max = clamp(c + up, 0, 1)
```

This handles mixed polarities correctly (e.g., one uni+ and one uni- source).

---

## Phase 1: Dual Bus Foundation

**Goal:** Add separate buses for user values vs modulated values. Always-on modApply layer (no conditional passthrough).

**Duration:** 1 session

### Key Design Decision: Always-On ModApply

Instead of:
- OSC writes to userParams
- IF no routes: copy to genParams
- IF routes: modApply writes to genParams

We do:
- OSC writes to userParams ONLY
- modApply synth ALWAYS reads userParams and writes to genParams
- 0 routes = passthrough (all busX = -1, output = center)

This eliminates race conditions and edge cases. One code path, always.

### SuperCollider Changes

**File:** `supercollider/core/buses.scd`

```supercollider
// Add after ~genParams creation
~genUserParams = 8.collect { |i|
    Dictionary.newFrom([
        \cutoff, Bus.control(s, 1).set(8000),
        \frequency, Bus.control(s, 1).set(440),
        \resonance, Bus.control(s, 1).set(0.5),
        \attack, Bus.control(s, 1).set(0.01),
        \decay, Bus.control(s, 1).set(0.3),
    ]);
};
```

**File:** `supercollider/core/osc_handlers.scd`

- Modify param handlers to write to `~genUserParams` ONLY
- NO passthrough logic - modApply handles everything

**File:** `supercollider/core/mod_apply_v2.scd`

- Modify `\modApply` SynthDef to read base value from `~genUserParams` bus (In.kr)
- Create passthrough synths for all modulatable params on init
- When route added: update existing synth args (or rebuild)
- When route removed: synth continues with fewer sources
- 0 routes = synth still runs, just outputs center value

### Deliverables Checklist

- [ ] `~genUserParams` buses created for all 8 slots × 5 params
- [ ] OSC param handlers write to userParams ONLY
- [ ] Passthrough synths created on init for all params
- [ ] ModApply reads userParams bus continuously (In.kr)
- [ ] 0 routes = passthrough (output = input)
- [ ] Moving slider while modulating updates center point immediately

### Success Criteria

1. Start SC - all params have passthrough synths running
2. Load generator, set CUT to 80% - sound responds (passthrough working)
3. Create mod route M1.A → G1.CUT
4. Hear modulation centered around 80%
5. Drag CUT slider to 20%
6. Modulation center moves immediately to 20%
7. Remove mod route - passthrough continues, slider value preserved

---

## Phase 2: Data Model Update

**Goal:** Add amount, polarity, and invert fields to connection model, update OSC protocol.

**Duration:** 1 session

### Python Changes

**File:** `src/gui/mod_routing_state.py`

```python
from enum import Enum

class Polarity(Enum):
    BIPOLAR = 'bipolar'
    UNI_POS = 'uni_pos'
    UNI_NEG = 'uni_neg'

@dataclass
class ModConnection:
    source_bus: int
    target_slot: int
    target_param: str
    depth: float = 0.5       # 0.0 to 1.0 (was -1.0 to 1.0)
    amount: float = 1.0      # 0.0 to 1.0 (NEW)
    polarity: Polarity = Polarity.BIPOLAR  # (NEW)
    invert: bool = False     # (NEW) flip mod signal before applying
    
    # Remove 'enabled' field - no longer needed
```

**Note on invert:** This preserves "inverted bipolar" which was previously achieved with negative depth. Invert flips the mod signal (s → -s) before polarity is applied.

Update signals:
- `connection_changed` → emits on depth OR amount OR polarity OR invert change

**File:** `src/config/__init__.py`

Add new OSC paths:
```python
'mod_route_add': '/noise/mod/route/add',      # [bus, slot, param, depth, amount, polarity, invert]
'mod_route_depth': '/noise/mod/route/depth',  # [bus, slot, param, depth]
'mod_route_amount': '/noise/mod/route/amount', # [bus, slot, param, amount]
'mod_route_polarity': '/noise/mod/route/polarity', # [bus, slot, param, polarity_int]
'mod_route_invert': '/noise/mod/route/invert', # [bus, slot, param, invert_int]
```

### SuperCollider Changes

**File:** `supercollider/core/mod_apply_v2.scd`

Update `\modApply` SynthDef:
```supercollider
SynthDef(\modApply, { |userParamBus, paramBus, minVal=0, maxVal=1, curve=0,
                      bus0=(-1), depth0=0, amount0=1, polarity0=0, invert0=0,
                      bus1=(-1), depth1=0, amount1=1, polarity1=0, invert1=0,
                      ... |
    // polarity: 0=bipolar, 1=uni+, 2=uni-
    // invert: 0=normal, 1=inverted
});
```

**File:** `supercollider/core/mod_routing.scd`

Update OSC handlers for new message format.

### Deliverables Checklist

- [ ] ModConnection has depth (0-1), amount (0-1), polarity (enum), invert (bool)
- [ ] Removed 'enabled' field
- [ ] OSC messages include amount, polarity, and invert
- [ ] SC modApply accepts amount/polarity/invert per source
- [ ] Polarity affects modulation direction correctly
- [ ] Invert flips mod signal before polarity applied

### Success Criteria

1. Create route with default values (depth=0.5, amount=1.0, bipolar, invert=false)
2. Hear full bipolar modulation
3. Toggle invert → modulation direction flips
4. Set polarity to uni+ → only goes up
5. Set polarity to uni+ with invert → goes up when LFO goes down

---

## Phase 3: Popup Redesign

**Goal:** New popup layout with depth slider, amount slider, polarity toggle, invert toggle.

**Duration:** 1 session

### Python Changes

**File:** `src/gui/mod_depth_popup.py` → rename to `src/gui/mod_connection_popup.py`

```
┌─────────────────────────────┐
│  M1.A → G1 CUT              │  Header
├─────────────────────────────┤
│  Depth    [━━━━━●━━━] 60%   │  Horizontal slider 0-100%
│  Amount   [━━━━━━━━●] 100%  │  Horizontal slider 0-100%
├─────────────────────────────┤
│  [Bi] [Uni+] [Uni-]  [INV]  │  Segmented + toggle
├─────────────────────────────┤
│         [Remove]            │  Single red button
└─────────────────────────────┘
```

Features:
- Real-time preview (non-modal, hear changes immediately)
- Depth slider: 0-100%, shows percentage
- Amount slider: 0-100%, shows percentage  
- Polarity: segmented control (faster than radio buttons)
- Invert: toggle button (highlights when active)
- Remove button (no Disable)
- Throttle OSC updates (~60Hz max) to avoid hammering SC

**File:** `src/gui/mod_matrix_window.py`

- Update import from mod_depth_popup to mod_connection_popup
- Update popup creation calls

**File:** `src/gui/main_frame.py`

- Update handler for connection changes (now includes amount/polarity/invert)

### Deliverables Checklist

- [ ] New popup file: mod_connection_popup.py
- [ ] Depth slider (0-100%)
- [ ] Amount slider (0-100%)
- [ ] Polarity segmented control (Bi / Uni+ / Uni-)
- [ ] Invert toggle button
- [ ] Remove button (red)
- [ ] Changes emit signals → update SC in real-time (throttled)
- [ ] Popup positioned near clicked cell

### Success Criteria

1. Right-click cell → popup opens
2. Drag depth slider → hear range change
3. Drag amount slider → hear intensity change
4. Click Uni+ → modulation only goes up
5. Click INV → modulation direction flips
6. Click Remove → connection deleted, popup closes

---

## Phase 4: Matrix Cell Visuals

**Goal:** Show polarity in matrix cell with arrow indicators.

**Duration:** 0.5-1 session

### Python Changes

**File:** `src/gui/mod_matrix_cell.py`

Update `paintEvent`:
```python
# After drawing the circle...
if self.polarity == Polarity.UNI_POS:
    # Draw up arrow above/beside circle
    painter.drawLine(cx, cy - radius - 2, cx, cy - radius - 6)
    painter.drawLine(cx - 2, cy - radius - 4, cx, cy - radius - 6)
    painter.drawLine(cx + 2, cy - radius - 4, cx, cy - radius - 6)
elif self.polarity == Polarity.UNI_NEG:
    # Draw down arrow below/beside circle
    ...
# Bipolar = no arrow (just circle)
```

Add property:
```python
def set_polarity(self, polarity: Polarity):
    self._polarity = polarity
    self.update()
```

**File:** `src/gui/mod_matrix_window.py`

- When connection changes, update cell's polarity property
- Sync polarity from ModRoutingState on window open

### Deliverables Checklist

- [ ] Cell stores polarity state
- [ ] Bipolar: filled circle only (●)
- [ ] Uni+: circle with up arrow (●↑)
- [ ] Uni-: circle with down arrow (●↓)
- [ ] Dot size still reflects depth
- [ ] Color still reflects source type

### Success Criteria

1. Create bipolar connection → circle only
2. Open popup, change to Uni+ → arrow appears pointing up
3. Change to Uni- → arrow points down
4. Change back to Bipolar → arrow disappears

---

## Phase 5: Keyboard Shortcuts

**Goal:** New key mappings for amount, depth, polarity, and invert.

**Duration:** 0.5-1 session

### Key Mapping

| Key | Action |
|-----|--------|
| `1-9` | Set Amount (10%-90%) |
| `Shift + 1-9` | Set Depth (10%-90%) |
| `-` alone | Set Unipolar Negative |
| `+` alone | Set Unipolar Positive |
| `=` alone | Set Bipolar |
| `I` | Toggle Invert |
| `-` held + `1-9` | Amount + Uni- |
| `+` held + `1-9` | Amount + Uni+ |
| `Space` | Toggle connection (create/remove) |
| `Delete/Backspace` | Remove connection |
| `D` | Open popup |
| Arrow keys | Navigate |

### Python Changes

**File:** `src/gui/mod_matrix_window.py`

Update `keyPressEvent` - use `event.text()` for UK keyboard compatibility:
```python
def keyPressEvent(self, event):
    key = event.key()
    text = event.text()  # Use text for +/- detection (UK keyboard safe)
    modifiers = event.modifiers()
    
    # Number keys for amount/depth
    if key in range(Qt.Key_1, Qt.Key_9 + 1):
        value = (key - Qt.Key_0) / 10.0  # 0.1 to 0.9
        
        if modifiers & Qt.ShiftModifier:
            self._set_selected_depth(value)
        else:
            self._set_selected_amount(value)
    
    # Polarity via text (more reliable across keyboard layouts)
    elif text == '-':
        self._set_selected_polarity(Polarity.UNI_NEG)
    elif text == '+':
        self._set_selected_polarity(Polarity.UNI_POS)
    elif text == '=':
        self._set_selected_polarity(Polarity.BIPOLAR)
    
    # Invert toggle
    elif key == Qt.Key_I:
        self._toggle_selected_invert()
    
    # ... existing navigation keys
```

### Deliverables Checklist

- [ ] `1-9` sets amount
- [ ] `Shift + 1-9` sets depth
- [ ] `-` sets Uni- (via event.text())
- [ ] `+` sets Uni+ (via event.text())
- [ ] `=` sets Bipolar
- [ ] `I` toggles invert
- [ ] Existing nav keys still work

### Success Criteria

1. Select cell with connection
2. Press `5` → amount becomes 50%
3. Press `Shift+8` → depth becomes 80%
4. Press `-` → polarity becomes Uni-
5. Press `=` → polarity becomes Bipolar
6. Press `I` → invert toggles
7. Arrow keys still navigate

---

## Phase 6: Slider Visualization Update

**Goal:** Brackets show effective range (depth × amount), move with slider, handle mixed polarities.

**Duration:** 1 session

### Python Changes

**File:** `src/gui/main_frame.py`

Update `_update_slider_mod_range` with proper up/down aggregation:
```python
def _update_slider_mod_range(self, slot_id, param):
    # Get all connections for this target
    connections = self.mod_routing.get_connections_for_target(slot_id, param)
    
    if not connections:
        slider.clear_modulation()
        return
    
    # Get current slider position as center (normalized 0-1)
    center = slider.value() / 1000.0
    
    # Calculate separate up/down ranges for mixed polarities
    up_range = 0.0
    down_range = 0.0
    
    for c in connections:
        effective = c.depth * c.amount
        if c.polarity == Polarity.BIPOLAR:
            up_range += effective
            down_range += effective
        elif c.polarity == Polarity.UNI_POS:
            up_range += effective
        elif c.polarity == Polarity.UNI_NEG:
            down_range += effective
    
    # Calculate bracket positions
    mod_min = max(0.0, center - down_range)
    mod_max = min(1.0, center + up_range)
    
    slider.set_modulation_range(mod_min, mod_max, color)
```

### Bracket Recalculation Triggers

Brackets should recalc on:
- `slider.valueChanged` signal
- `mod_routing.connection_changed` signal
- Popup depth/amount/polarity changes

Do NOT override `setValue()` - use signals instead to avoid double-emits.

**File:** `src/gui/main_frame.py`

Connect slider valueChanged to bracket update:
```python
# In generator panel setup
slider.valueChanged.connect(
    lambda v, s=slot_id, p=param: self._update_slider_mod_range(s, p)
)
```

### Connection to Slider Movement

When slider moved while modulated:
1. Python sends new value via OSC → `~genUserParams`
2. ModApply synth reads new center from bus (continuous via In.kr)
3. valueChanged signal triggers bracket recalc
4. Brackets redraw around new center

### Deliverables Checklist

- [ ] Brackets use up/down aggregation (not symmetric)
- [ ] Brackets centered on current slider position
- [ ] Moving slider moves brackets in real-time
- [ ] Uni+ → brackets only above slider position
- [ ] Uni- → brackets only below slider position
- [ ] Mixed sources (e.g., uni+ and uni-) handled correctly
- [ ] Animated line still shows current modulated value

### Success Criteria

1. Create connection: depth=60%, amount=100%, bipolar → brackets show ±60% range
2. Change to Uni+ → brackets only above slider
3. Change amount to 50% → brackets shrink to +30% only
4. Drag slider up → brackets follow immediately
5. Add second source Uni- → brackets now extend both directions
6. Set slider near edge → brackets clip at 0%/100%

---

## Phase 7 (Optional): Polish & Edge Cases

**Goal:** Handle edge cases, optimize, document.

**Duration:** As needed

### Items

- [ ] Bracket clipping at 0%/100% boundaries
- [ ] Exponential params (cutoff/frequency) bracket scaling
- [ ] Preset save/load with new fields
- [ ] Remove old mod_depth_popup.py file
- [ ] Update MOD_MATRIX_BACKLOG.md (mark complete)
- [ ] Update mod-matrix-process.html with relative mod section

---

## Files Summary

| File | Phase | Changes |
|------|-------|---------|
| `supercollider/core/buses.scd` | 1 | Add ~genUserParams |
| `supercollider/core/osc_handlers.scd` | 1 | Write to userParams ONLY |
| `supercollider/core/mod_apply_v2.scd` | 1, 2 | Always-on passthrough, amount/polarity/invert |
| `supercollider/core/mod_routing.scd` | 2 | New OSC handlers |
| `src/gui/mod_routing_state.py` | 2 | amount, polarity, invert fields |
| `src/config/__init__.py` | 2 | New OSC paths |
| `src/gui/mod_connection_popup.py` | 3 | New popup (replaces mod_depth_popup) |
| `src/gui/mod_matrix_cell.py` | 4 | Polarity arrows |
| `src/gui/mod_matrix_window.py` | 3, 4, 5 | Popup, cell sync, keys (event.text()) |
| `src/gui/main_frame.py` | 6 | Slider viz with up/down aggregation |

---

## Risk Areas

1. **Always-on passthrough synths** - 40 synths (8 slots × 5 params) always running. Should be minimal CPU (simple In.kr → Out.kr). Monitor with s.avgCPU.

2. **Polarity math** - Uni+/Uni- need careful implementation. Clear formulas in spec. Test each polarity × invert combination.

3. **Backward compatibility** - Old presets won't have amount/polarity/invert. Mitigation: Default values on load (amount=1.0, bipolar, invert=false).

4. **Multi-source + mixed polarities** - Need separate up/down bracket aggregation. Tested in Phase 6.

5. **Keyboard layout (UK)** - Using `event.text()` instead of `event.key()` for +/-/= detection.

---

## Success Metrics (End State)

- [ ] Slider = center point (hardware feel)
- [ ] Depth × Amount = effective range
- [ ] Polarity works correctly (bi/uni+/uni-)
- [ ] Invert flips mod signal correctly
- [ ] Keyboard shortcuts intuitive (event.text() for UK)
- [ ] Visual feedback accurate (up/down bracket aggregation)
- [ ] No disable concept (simpler)
- [ ] Works with multi-source + mixed polarities

---

*Ready to begin Phase 1?*
