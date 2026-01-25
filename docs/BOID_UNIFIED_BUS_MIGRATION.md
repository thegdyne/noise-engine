# Boid Unified Bus Migration Spec

**Date:** 2025-01-25
**Status:** Implementation pending
**Issue:** Boid modulation not affecting generator parameters through unified bus system

## Problem Summary

Generator parameters (cols 0-79) were added to the unified bus system in Phase 7, but the boid controller still splits contributions at col 80 and sends gen params through the legacy `/noise/gen/boid/offsets` path instead of the unified `/noise/boid/offsets` path.

## Source of Truth

`supercollider/core/bus_unification.scd` defines the canonical bus layout:

```
Bus Layout (149 total, indices 0-148):
| Index     | Count | Category      | Parameters                                      |
|-----------|-------|---------------|------------------------------------------------|
| 0-39      | 40    | Gen Core      | 8 slots x 5 params (freq, cutoff, res, atk, dec)|
| 40-79     | 40    | Gen Custom    | 8 slots x 5 custom params (custom0-4)          |
| 80-107    | 28    | Mod Slots     | 4 slots x 7 params (P0-P6)                     |
| 108-131   | 24    | Channels      | 8 slots x 3 params (echo, verb, pan)           |
| 132-148   | 17    | FX            | heat, echo, reverb, dualFilter (mix excluded)  |
```

**Grid dimensions:** 149 columns (0-148) x 16 rows

## Files Requiring Changes

### 1. `src/boids/boid_engine.py`

| Line | Current | Should Be |
|------|---------|-----------|
| 22 | `GRID_COLS = 151` | `GRID_COLS = 149` |

### 2. `src/boids/boid_state.py`

| Line | Current | Should Be |
|------|---------|-----------|
| 60 | `# Columns 132-150 (FX params)` | `# Columns 132-148 (FX params)` |
| 150 | `ranges.append((132, 150))` | `ranges.append((132, 148))` |
| 161 | `if self.zone_fx and 132 <= col <= 150:` | `if self.zone_fx and 132 <= col <= 148:` |

### 3. `src/boids/boid_controller.py`

| Line | Change |
|------|--------|
| 8 | Remove mention of "Generator routing (separate OSC path for cols 0-79)" |
| 20 | Remove import of `BoidGenRouter` |
| 42 | Remove `self._gen_router` attribute |
| 65-69 | Remove `_get_gen_router()` method |
| 166-184 | Replace split logic - send ALL contributions through unified |

**New `_tick()` method:**
```python
def _tick(self):
    """Simulation tick - advance physics and send OSC."""
    if not self._state.enabled:
        return

    # Advance simulation
    self._engine.tick()

    # Get contributions
    contributions = self._engine.get_contributions()

    # Send ALL contributions through unified bus sender
    bus_sender = self._get_bus_sender()
    if bus_sender:
        bus_sender.send_offsets(contributions)

    # Emit signals for visualization
    self.positions_updated.emit(self._engine.get_positions())
    self.cells_updated.emit(self._engine.get_cell_values())
```

### 4. `src/gui/boid_overlay.py`

| Line | Current | Should Be |
|------|---------|-----------|
| 134 | `# Grid is 151 cols x 16 rows` | `# Grid is 149 cols x 16 rows` |
| 135 | `cx = (col / 151.0) * w` | `cx = (col / 149.0) * w` |
| 137 | `cell_w = w / 151.0` | `cell_w = w / 149.0` |

### 5. `src/gui/boid_panel.py`

| Line | Current | Should Be |
|------|---------|-----------|
| 73 | `# Grid is 151 cols x 16 rows` | `# Grid is 149 cols x 16 rows` |
| 74 | `cx = (col / 151.0) * w` | `cx = (col / 149.0) * w` |
| 76 | `cell_w = w / 151.0` | `cell_w = w / 149.0` |
| 214 | `"cols 132-150"` | `"cols 132-148"` |

## Files Already Correct

| File | Status | Notes |
|------|--------|-------|
| `src/utils/boid_bus.py` | OK | `GRID_TOTAL_COLUMNS = 149`, `FX_COLS = (132, 148)` |
| `src/gui/controllers/generator_controller.py` | OK | Routes UI through `/noise/bus/base` |
| `supercollider/core/bus_unification.scd` | OK | Source of truth, 149 targets |
| `supercollider/core/bus_unification_osc.scd` | OK | Handles all 149 targets |

## Files to Deprecate (no immediate change needed)

| File | Reason |
|------|--------|
| `src/utils/boid_gen_router.py` | No longer called after controller fix |
| `osc_handlers.scd` `/noise/gen/boid/offsets` handler | Legacy, not used after migration |

## Data Flow After Migration

```
Boid Engine (20Hz tick)
    |
    v
BoidController._tick()
    |
    | contributions = [(row, col, value), ...]
    |
    v
BoidBusSender.send_offsets(contributions)
    |
    | grid_to_bus(row, col) -> bus_index
    | aggregate by bus_index
    |
    v
OSC: /noise/boid/offsets [busIdx1, offset1, busIdx2, offset2, ...]
    |
    v
SC: bus_unification_osc.scd OSCdef(\boidOffsets)
    |
    | Parse pairs, validate indices
    | Queue via ~queueBoidOp(\setOffsets, offsets)
    |
    v
SC: bus_unification.scd apply tick (200Hz)
    |
    | Phase 3: Drain boid ops, update ~activeBoidIndices
    | Phase 5: For targets in ~activeBoidIndices, add boid offset
    |
    v
Unified bus value updated -> Synth reads via In.kr(bus)
```

## Verification Steps

1. **SC boot:** Should see `149 targets` in bus unification log
2. **Python connect:** Should see `bus base set to XXX` in Python log
3. **Enable boids:** Generator param sliders should show modulation
4. **Zone toggles:** GEN zone (cols 0-79) should affect gen params
5. **No connection drops:** Heartbeat should remain stable

## Related Prior Fixes

- **Bus base synchronization:** Python queries SC for actual bus base at connect time (fixes allocation mismatch where SC allocates at 246 instead of 1000)
- **Thread starvation fix:** Apply tick lowered from 500Hz to 200Hz, lazy boid computation added
