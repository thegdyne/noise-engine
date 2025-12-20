# Widget Naming Convention

All Qt widgets should have an `objectName` set for debugging purposes.
This enables the click-to-trace feature and makes the debug overlay useful.

## Why?

Without objectNames, the debug trace shows:
```
CycleButton 70x20 ⚠️FIXED
  ↑ QFrame 70x20 ⚠️FIXED
  ↑ QWidget 156x20 ⚠️FIXED
  ↑ QFrame 164x263 ⚠️FIXED
```

With objectNames:
```
gen1_type (CycleButton) 70x20 ⚠️FIXED
  ↑ gen1_type_container (QFrame) 70x20 ⚠️FIXED
  ↑ gen1_header (QWidget) 156x20 ⚠️FIXED
  ↑ generatorFrame (QFrame) 164x263 ⚠️FIXED
```

## Naming Format

```
{section}{id}_{component}
```

- **section**: `gen`, `mod`, `mix`, `master`, `fx`
- **id**: Slot number (1-8) or empty for singletons
- **component**: Descriptive name of the widget

### Examples

| objectName | Description |
|------------|-------------|
| `gen1_type` | Generator 1 type selector |
| `gen1_header` | Generator 1 header row |
| `gen1_type_container` | Container for type selector |
| `mod2_wave0` | Modulator 2, output 0 waveform button |
| `master_fader` | Master output fader |
| `mix3_pan` | Mixer channel 3 pan slider |

## How to Add

```python
# After creating widget
widget = QWidget()
widget.setObjectName(f"gen{slot.slot_id}_header")  # DEBUG

# For buttons/controls
self.type_btn = CycleButton(...)
self.type_btn.setObjectName(f"gen{slot.slot_id}_type")  # DEBUG
```

## Required Names

### Generator Slots
- `gen{N}_slot` - GeneratorSlot container
- `gen{N}_header` - Header row widget
- `gen{N}_type` - Type selector button
- `gen{N}_type_container` - Type selector container
- `gen{N}_label` - "GEN N" label
- `gen{N}_filter` - Filter type button
- `gen{N}_env` - Envelope source button
- `gen{N}_rate` - Clock rate button
- `gen{N}_midi` - MIDI channel button
- `gen{N}_mute` - Mute button
- `gen{N}_gate` - Gate LED indicator

### Modulator Slots
- `mod{N}_slot` - ModulatorSlot container
- `mod{N}_type` - Generator type selector
- `mod{N}_label` - "MOD N" label
- `mod{N}_mode` - Mode button (CLK/FREE)
- `mod{N}_wave{M}` - Waveform button (M=0,1,2)
- `mod{N}_phase{M}` - Phase button
- `mod{N}_pol{M}` - Polarity button

### Mixer Channels
- `mix{N}_strip` - Channel strip container
- `mix{N}_fader` - Volume fader
- `mix{N}_pan` - Pan slider
- `mix{N}_mute` - Mute button
- `mix{N}_solo` - Solo button
- `mix{N}_meter` - Level meter

### Master Section
- `master_fader` - Main output fader
- `master_meter` - Output level meter
- `master_eq_lo` - EQ low band
- `master_eq_mid` - EQ mid band
- `master_eq_hi` - EQ high band
- `master_comp_threshold` - Compressor threshold
- `master_limiter_ceiling` - Limiter ceiling

## CI Check

Run the naming checker:
```bash
python tools/check_widget_names.py
```

This scans source files and reports widgets without objectNames.
The CI threshold is set to allow gradual adoption.

## Debug Usage

1. Run app: `noise`
2. Press **Fn+F9** to enable debug mode
3. **Click any widget** to see its hierarchy in terminal
4. Use the objectName to find the code that creates it
