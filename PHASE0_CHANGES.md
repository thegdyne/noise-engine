# Phase 0: Quadrature Expansion (3→4 outputs)

## Summary

Expanded LFO and Sloth from 3 to 4 outputs per slot. Total mod buses: 12 → 16.

## Files Changed

### Config
- `src/config/__init__.py`
  - `MOD_OUTPUTS_PER_SLOT`: 3 → 4
  - `MOD_BUS_COUNT`: 12 → 16
  - Added `MOD_LFO_PHASE_PATTERNS` (QUAD/PAIR/SPREAD/TIGHT/WIDE/SYNC)
  - Added `MOD_LFO_ROTATE_STEPS` (24 = 15° each)
  - Updated `MOD_OUTPUT_LABELS` for 4 outputs

### SuperCollider SynthDefs
- `supercollider/core/mod_lfo.scd`
  - 4 outputs: A, B, C, D
  - New params: `pattern` (0-5), `rotate` (0-23)
  - Phase controlled globally via pattern+rotate

- `supercollider/core/mod_sloth.scd`
  - 4 outputs: X, Y, Z, R
  - R = rectified gate (fires when slow > fast)

### SuperCollider Infrastructure
- `supercollider/core/mod_buses.scd` - 16 buses
- `supercollider/core/mod_slots.scd` - Updated synth creation

### JSON Configs
- `supercollider/mod_generators/lfo.json` - 4 outputs, pattern/rotate params
- `supercollider/mod_generators/sloth.json` - 4 outputs including R

### Python UI
- `src/gui/mod_scope.py` - 4 traces
- `src/gui/modulator_slot.py` - Updated docstrings
- `src/gui/modulator_slot_builder.py` - Handle pattern_rotate config
- `src/gui/skins/default.py` - scope_trace_d colour
- `src/gui/theme.py` - scope_trace_d mapping

## LFO Phase Patterns

| Pattern | A | B | C | D | Use Case |
|---------|---|---|---|---|----------|
| QUAD | 0° | 90° | 180° | 270° | Classic quadrature |
| PAIR | 0° | 0° | 180° | 180° | Two stereo pairs |
| SPREAD | 0° | 45° | 180° | 225° | Wider spread |
| TIGHT | 0° | 22° | 45° | 67° | Subtle differences |
| WIDE | 0° | 120° | 180° | 300° | Maximum spread |
| SYNC | 0° | 0° | 0° | 0° | All in phase |

## Sloth R Output

```
R = max(0, (Y.abs + Z.abs * 0.5) - X.abs) * 2
```

Creates irregular gate pulses when slower chaos exceeds faster - useful for triggering.

## Application

Copy these files to your noise-engine project, replacing existing ones:

```bash
cp quadrature-changes/src/config/__init__.py noise-engine/src/config/
cp quadrature-changes/supercollider/core/*.scd noise-engine/supercollider/core/
cp quadrature-changes/supercollider/mod_generators/*.json noise-engine/supercollider/mod_generators/
cp quadrature-changes/src/gui/*.py noise-engine/src/gui/
cp quadrature-changes/src/gui/skins/default.py noise-engine/src/gui/skins/
```

Then test by starting the app and switching a mod slot to LFO - you should see 4 output rows and PAT/ROT controls.
