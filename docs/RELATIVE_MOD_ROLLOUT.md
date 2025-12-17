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
```
effective_range = depth × amount
output = center + (mod_signal × effective_range × polarity_factor)

Polarity factors:
  Bipolar:  mod range -1 to +1 → output range (center - range) to (center + range)
  Uni+:     mod range -1 to +1 → output range (center) to (center + range)
  Uni-:     mod range -1 to +1 → output range (center - range) to (center)
```

---

## Phase 1: Dual Bus Foundation

**Goal:** Add separate buses for user values vs modulated values. Passthrough when no modulation.

**Duration:** 1 session

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

- Modify param handlers to write to `~genUserParams` instead of `~genParams`
- Add passthrough: when no mod route exists for that param, copy value to `~genParams`

**File:** `supercollider/core/mod_apply_v2.scd`

- Modify `\modApply` SynthDef to read base value from `~genUserParams` bus (not fixed arg)
- Use `In.kr(userParamBus)` for continuous tracking

### Deliverables Checklist

- [ ] `~genUserParams` buses created for all 8 slots × 5 params
- [ ] OSC param handlers write to userParams
- [ ] Passthrough copies to genParams when no mod active
- [ ] ModApply reads userParams bus continuously
- [ ] Moving slider while modulating updates center point immediately

### Success Criteria

1. Load generator, set CUT to 80%
2. Create mod route M1.A → G1.CUT
3. Hear modulation centered around 80%
4. Drag CUT slider to 20%
5. Modulation center moves immediately to 20%
6. Remove mod route - slider value preserved

---

## Phase 2: Data Model Update

**Goal:** Add amount and polarity fields to connection model, update OSC protocol.

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
    
    # Remove 'enabled' field - no longer needed
```

Update signals:
- `connection_changed` → emits on depth OR amount OR polarity change

**File:** `src/config/__init__.py`

Add new OSC paths:
```python
'mod_route_add': '/noise/mod/route/add',      # [bus, slot, param, depth, amount, polarity]
'mod_route_depth': '/noise/mod/route/depth',  # [bus, slot, param, depth]
'mod_route_amount': '/noise/mod/route/amount', # [bus, slot, param, amount]
'mod_route_polarity': '/noise/mod/route/polarity', # [bus, slot, param, polarity_int]
```

### SuperCollider Changes

**File:** `supercollider/core/mod_apply_v2.scd`

Update `\modApply` SynthDef:
```supercollider
SynthDef(\modApply, { |userParamBus, paramBus, minVal=0, maxVal=1, curve=0,
                      bus0=(-1), depth0=0, amount0=1, polarity0=0,
                      bus1=(-1), depth1=0, amount1=1, polarity1=0,
                      ... |
    // polarity: 0=bipolar, 1=uni+, 2=uni-
});
```

**File:** `supercollider/core/mod_routing.scd`

Update OSC handlers for new message format.

### Deliverables Checklist

- [ ] ModConnection has depth (0-1), amount (0-1), polarity (enum)
- [ ] Removed 'enabled' field
- [ ] OSC messages include amount and polarity
- [ ] SC modApply accepts amount/polarity per source
- [ ] Polarity affects modulation direction correctly

### Success Criteria

1. Create route with default values (depth=0.5, amount=1.0, bipolar)
2. Hear full bipolar modulation
3. Manually send OSC to change polarity to uni+
4. Modulation only goes above slider position
5. Change to uni- 
6. Modulation only goes below slider position

---

## Phase 3: Popup Redesign

**Goal:** New popup layout with depth slider, amount slider, polarity toggle.

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
│  (●) Bi   ( ) Uni+  ( ) Uni-│  Radio buttons
├─────────────────────────────┤
│         [Remove]            │  Single red button
└─────────────────────────────┘
```

Features:
- Real-time preview (non-modal, hear changes immediately)
- Depth slider: 0-100%, shows percentage
- Amount slider: 0-100%, shows percentage  
- Polarity: three radio/toggle buttons
- Remove button (no Disable)

**File:** `src/gui/mod_matrix_window.py`

- Update import from mod_depth_popup to mod_connection_popup
- Update popup creation calls

**File:** `src/gui/main_frame.py`

- Update handler for connection changes (now includes amount/polarity)

### Deliverables Checklist

- [ ] New popup file: mod_connection_popup.py
- [ ] Depth slider (0-100%)
- [ ] Amount slider (0-100%)
- [ ] Polarity radio buttons (Bi / Uni+ / Uni-)
- [ ] Remove button (red)
- [ ] Changes emit signals → update SC in real-time
- [ ] Popup positioned near clicked cell

### Success Criteria

1. Right-click cell → popup opens
2. Drag depth slider → hear range change
3. Drag amount slider → hear intensity change
4. Click Uni+ → modulation only goes up
5. Click Remove → connection deleted, popup closes

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

**Goal:** New key mappings for amount, depth, and polarity.

**Duration:** 0.5-1 session

### Key Mapping

| Key | Action |
|-----|--------|
| `1-9` | Set Amount (10%-90%) |
| `Shift + 1-9` | Set Depth (10%-90%) |
| `-` alone | Set Unipolar Negative |
| `+` alone | Set Unipolar Positive |
| `=` alone | Set Bipolar |
| `-` held + `1-9` | Amount + Uni- |
| `+` held + `1-9` | Amount + Uni+ |
| `Space` | Toggle connection (create/remove) |
| `Delete/Backspace` | Remove connection |
| `D` | Open popup |
| Arrow keys | Navigate |

### Python Changes

**File:** `src/gui/mod_matrix_window.py`

Update `keyPressEvent`:
```python
def keyPressEvent(self, event):
    key = event.key()
    modifiers = event.modifiers()
    
    if key in range(Qt.Key_1, Qt.Key_9 + 1):
        value = (key - Qt.Key_0) / 10.0  # 0.1 to 0.9
        
        if modifiers & Qt.ShiftModifier:
            self._set_selected_depth(value)
        else:
            # Check if minus or plus held (platform-specific)
            self._set_selected_amount(value)
            # Also check polarity modifier...
    
    elif key == Qt.Key_Minus:
        self._set_selected_polarity(Polarity.UNI_NEG)
    elif key == Qt.Key_Plus:
        self._set_selected_polarity(Polarity.UNI_POS)
    elif key == Qt.Key_Equal:
        self._set_selected_polarity(Polarity.BIPOLAR)
```

### Deliverables Checklist

- [ ] `1-9` sets amount
- [ ] `Shift + 1-9` sets depth
- [ ] `-` sets Uni-
- [ ] `+` sets Uni+
- [ ] `=` sets Bipolar
- [ ] Modifier + number combo works
- [ ] Existing nav keys still work

### Success Criteria

1. Select cell with connection
2. Press `5` → amount becomes 50%
3. Press `Shift+8` → depth becomes 80%
4. Press `-` → polarity becomes Uni-
5. Press `=` → polarity becomes Bipolar
6. Arrow keys still navigate

---

## Phase 6: Slider Visualization Update

**Goal:** Brackets show effective range (depth × amount), move with slider.

**Duration:** 1 session

### Python Changes

**File:** `src/gui/main_frame.py`

Update `_update_slider_mod_range`:
```python
def _update_slider_mod_range(self, slot_id, param):
    # Get all connections for this target
    connections = self.mod_routing.get_connections_for_target(slot_id, param)
    
    if not connections:
        slider.clear_modulation()
        return
    
    # Calculate combined effective range
    total_range = sum(c.depth * c.amount for c in connections)
    
    # Get current slider position as center
    center = slider.value() / 1000.0
    
    # Calculate bracket positions based on polarity
    # (simplified - real impl handles multiple polarities)
    mod_min = max(0, center - total_range * 0.5)
    mod_max = min(1, center + total_range * 0.5)
    
    slider.set_modulation_range(mod_min, mod_max, color)
```

**File:** `src/gui/widgets.py`

Ensure `DragSlider` repaints when value changes while modulated:
```python
def setValue(self, value):
    super().setValue(value)
    if self.has_modulation():
        # Trigger range recalculation via signal
        self.normalizedValueChanged.emit(value / 1000.0)
```

### Connection to Slider Movement

When slider moved while modulated:
1. Python sends new value via OSC → `~genUserParams`
2. ModApply synth reads new center from bus (continuous)
3. Python also recalculates bracket positions
4. Brackets redraw around new center

### Deliverables Checklist

- [ ] Brackets width = depth × amount (effective range)
- [ ] Brackets centered on current slider position
- [ ] Moving slider moves brackets in real-time
- [ ] Polarity affects bracket position (uni+ = above only, etc.)
- [ ] Multi-source: brackets show combined range
- [ ] Animated line still shows current modulated value

### Success Criteria

1. Create connection: depth=60%, amount=100% → brackets show 60% range
2. Change amount to 50% → brackets shrink to 30% range
3. Drag slider up → brackets follow immediately
4. Set Uni+ → brackets only above slider position
5. Set Uni- → brackets only below slider position

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
| `supercollider/core/osc_handlers.scd` | 1 | Write to userParams, passthrough |
| `supercollider/core/mod_apply_v2.scd` | 1, 2 | Read userParams, amount/polarity |
| `supercollider/core/mod_routing.scd` | 2 | New OSC handlers |
| `src/gui/mod_routing_state.py` | 2 | amount, polarity fields |
| `src/config/__init__.py` | 2 | New OSC paths |
| `src/gui/mod_connection_popup.py` | 3 | New popup (replaces mod_depth_popup) |
| `src/gui/mod_matrix_cell.py` | 4 | Polarity arrows |
| `src/gui/mod_matrix_window.py` | 3, 4, 5 | Popup, cell sync, keys |
| `src/gui/main_frame.py` | 6 | Slider viz update |
| `src/gui/widgets.py` | 6 | Bracket recalc on move |

---

## Risk Areas

1. **OSC timing** - User param changes vs modulation updates could race. Mitigation: SC handles both on same thread.

2. **Passthrough logic** - Need to track which params have active routes. Mitigation: Use Dictionary lookup.

3. **Polarity math** - Uni+/Uni- need careful implementation. Mitigation: Clear formulas in spec, test each.

4. **Backward compatibility** - Old presets won't have amount/polarity. Mitigation: Default values on load.

---

## Success Metrics (End State)

- [ ] Slider = center point (hardware feel)
- [ ] Depth × Amount = effective range
- [ ] Polarity works correctly (bi/uni+/uni-)
- [ ] Keyboard shortcuts intuitive
- [ ] Visual feedback accurate
- [ ] No disable concept (simpler)
- [ ] Works with multi-source

---

*Ready to begin Phase 1?*
