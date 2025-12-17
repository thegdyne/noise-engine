# 🔀 Quadrature Modulation System Live

Major expansion to the mod sources - now with 4 outputs per slot for proper quadrature LFO and enhanced Sloth chaos.

---

## What's New

### 4 Outputs Per Mod Slot
- **LFO:** A, B, C, D outputs with phase patterns
- **Sloth:** X, Y, Z, R outputs (R = rectified gate)
- **16 mod buses total** (4 slots × 4 outputs)

### LFO Phase Patterns
Six preset patterns for instant quadrature setups:
| Pattern | Phases | Use Case |
|---------|--------|----------|
| QUAD | 0°, 90°, 180°, 270° | Classic quadrature |
| PAIR | 0°, 0°, 180°, 180° | Stereo pairs |
| SPREAD | 0°, 45°, 180°, 225° | Wide stereo |
| TIGHT | 0°, 22°, 45°, 67° | Subtle variation |
| WIDE | 0°, 120°, 180°, 300° | Maximum spread |
| SYNC | 0°, 0°, 0°, 0° | All in phase |

Plus **ROTATE** control - spin all phases together in 15° steps.

### Output Invert (NORM/INV)
Per-output signal flip. Defaults to NORM (non-inverted). Hit INV to flip the waveform - useful for:
- Creating contrary motion between outputs
- Inverting Sloth chaos for "anti-correlated" modulation
- Phase tricks with the R (rectified) output

---

## Architecture

```
4 Mod Slots × 4 Outputs = 16 Mod Buses
         ↓
    Mod Matrix (16×40 grid)
         ↓
    Up to 4 sources per destination
         ↓
    Animated slider visualization
```

Bus index formula: `(slot - 1) * 4 + output`
- Slot 1: buses 0-3
- Slot 2: buses 4-7
- Slot 3: buses 8-11
- Slot 4: buses 12-15

---

## Test Coverage

207 tests passing, including new architecture tests:
- Quadrature consistency (4 outputs everywhere)
- Bus index calculations
- NORM/INV defaults
- SC ↔ Python alignment
- SSOT compliance

---

## Files Changed

**Config:**
- `src/config/__init__.py` - MOD_OUTPUTS_PER_SLOT=4, phase patterns, NORM/INV

**SuperCollider:**
- `supercollider/core/mod_lfo.scd` - Quadrature outputs, pattern+rotate
- `supercollider/core/mod_sloth.scd` - 4 outputs (X/Y/Z/R)
- `supercollider/core/mod_slots.scd` - 4-output state management
- `supercollider/mod_generators/lfo.json` - pattern_rotate config
- `supercollider/mod_generators/sloth.json` - XYZR outputs

**GUI:**
- `src/gui/modulator_slot_builder.py` - 4 output rows, invert buttons
- `src/gui/mod_scope.py` - 4-trace display
- `src/gui/mod_matrix_window.py` - 16 source columns

---

## Up Next

- [ ] Bracket visualization respecting polarity modes
- [ ] Mod group ordering for clock sync reliability
- [ ] LFO FREE mode (non-clocked Hz control)
