# Mod Matrix Backlog

Feature requests and improvements for the modulation matrix system.

---

## High Priority

### Relative Modulation (Base Value Tracking)

**Status:** Not implemented  
**Complexity:** Medium-High  
**Affects:** `supercollider/core/mod_apply.scd`, potentially Python param handlers

**Problem:**
Currently modulation may use fixed parameter ranges (e.g. cutoff always sweeps 20Hz-16kHz at 100% depth). This is not how hardware synths behave.

**Desired Behaviour:**
- Modulation should be relative to the generator's current parameter value
- Example: Cutoff knob at 8kHz + LFO at 50% depth = sweeps ±50% around 8kHz (4kHz-12kHz)
- If user moves cutoff to 4kHz, modulation now sweeps around 4kHz (2kHz-6kHz)
- This is standard behaviour in Eurorack, Moog, etc.

**Implementation Notes:**
- mod_apply.scd needs to read the current base value from the parameter bus
- Modulation range = base_value ± (depth × range_factor)
- Need to handle edge cases (clipping at min/max)
- Consider: linear vs exponential scaling for frequency params
- May need to track "user set value" separately from "modulated value"

**References:**
- Moog modulars: mod depth is percentage of current value
- Eurorack: typically bipolar ±5V around 0V, but CV inputs are additive to knob position

---

### Modulation Offset / Base Value Behaviour Tuning

**Status:** Needs design discussion  
**Complexity:** Medium  
**Affects:** `supercollider/core/mod_apply.scd`, UI slider interaction

**Problem:**
Need to define and implement correct behaviour for:
1. What happens when user moves slider while modulation is active?
2. Should base value update live, or be captured once at route creation?
3. How do slider visualization brackets respond to manual slider changes?
4. What's the interaction between multiple sources and manual control?

**Current Behaviour:**
- Base value captured when route is created
- Moving slider while modulated doesn't update the modulation center point
- Visualization may not match actual modulation range after slider move

**Desired Behaviour:**
- TBD - needs user input on preferred workflow
- Options: live tracking, explicit "set base" action, or modal (mod vs edit modes)

**Related to:** Relative Modulation feature above

---

## Medium Priority

### Arrow Key Speed Control

**Status:** Not implemented  
**Complexity:** Low  
**Affects:** `src/gui/mod_matrix_window.py`

**Problem:**
Navigating 640 cells (16×40) one at a time is slow.

**Desired Behaviour:**
- Modifier keys change navigation step size:
  - **Shift + Arrow**: Jump 4 cells
  - **Ctrl/Cmd + Arrow**: Jump to next row (vertical) or next generator (horizontal)
  - **Home/End**: Jump to first/last column
  - **Page Up/Down**: Jump to first/last row

**Implementation Notes:**
- Modify `keyPressEvent` in `ModMatrixWindow`
- Check `event.modifiers()` for Qt.ShiftModifier, Qt.ControlModifier
- Horizontal jumps: 5 params per generator, so Ctrl+Right = +5 columns
- Vertical jumps: 4 outputs per mod slot, so Ctrl+Down = +4 rows

---

## Low Priority / Nice to Have

### Drag Operations

**Status:** Planned for Phase 6 but deferred  
**Complexity:** Medium  
**Affects:** `src/gui/mod_matrix_window.py`, `src/gui/mod_matrix_cell.py`

**Desired Behaviour:**
- Drag across row → assign same source to multiple destinations
- Shift+drag → copy depth value to dragged cells
- Alt+drag → remove connections from dragged cells

### Active Source Highlighting

**Status:** Planned for Phase 6 but deferred  
**Complexity:** Medium  
**Affects:** `src/gui/mod_matrix_window.py`, requires OSC from SC

**Desired Behaviour:**
- Row pulses/glows when mod source is outputting non-zero signal
- Shows which LFOs/Sloths are actively modulating
- Requires streaming mod bus values to Python (already done for scope)

### Copy/Paste Connections

**Status:** Not implemented  
**Complexity:** Low  
**Affects:** `src/gui/mod_matrix_window.py`

**Desired Behaviour:**
- Ctrl+C on selected cell: copy connection (source, depth, enabled)
- Ctrl+V on selected cell: paste connection to new target
- Could also support copying entire rows/columns

### Context Menu

**Status:** Partially planned  
**Complexity:** Low  
**Affects:** `src/gui/mod_matrix_window.py`

**Desired Behaviour:**
Right-click menu with:
- Set Depth...
- Enable / Disable
- Remove
- Copy to Row (same depth to all destinations)
- Copy to Column (same source to all params)

---

## Completed

- [x] Phase 0: Quadrature expansion (4 outputs per slot)
- [x] Phase 1: OSC wiring for 4 outputs
- [x] Phase 2: Routing engine (mod_apply.scd)
- [x] Phase 3: Connection data model (ModRoutingState)
- [x] Phase 4: Pin Matrix UI window
- [x] Phase 5: Depth control popup
- [x] Phase 6: Keyboard navigation + polish

---

## Notes

### Current Architecture

```
Python (ModRoutingState)
    ↓ OSC: /noise/mod/route/add [bus, slot, param, depth]
SuperCollider (mod_routing.scd)
    ↓ calls ~addModRoute
mod_apply.scd
    ↓ creates \modRoute synth
Modulation applied to parameter bus
```

### Parameter Ranges (mod_apply.scd)

| Param | Min | Max | Curve |
|-------|-----|-----|-------|
| cutoff | 20 | 16000 | exp |
| frequency | 20 | 8000 | exp |
| resonance | 0.1 | 1.0 | linear |
| attack | 0.001 | 2.0 | linear |
| decay | 0.01 | 10.0 | linear |

These are absolute ranges - the "relative modulation" feature would change this.
