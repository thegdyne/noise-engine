# Preset Mixer Loading Behavior

## Problem

Loading a preset brings in mixer settings (channel faders, master fader). If loading an init patch or older preset with full-blast levels, this can cause unexpected volume jumps.

## Options

### A: Don't load mixer state
Presets = sounds only. Mixer stays as-is.
- ✓ Simple, safe
- ✗ Lose mix recall

### B: Master fader stays put
Load channel faders/EQ but leave master where it is.
- ✓ Relative mix preserved
- ✓ Master as hands-on safety control (hardware synth feel)
- ✓ Simple to implement

### C: Load with fade-in
Ramp loaded volumes up over ~500ms.
- ✓ Prevents sudden blasts
- ✗ Adds complexity
- ✗ May feel sluggish

### D: Checkbox on load
"Include mixer settings" toggle in load dialog.
- ✓ Most flexible
- ✓ Full session recall when wanted
- ✗ Extra UI element

### E: Conservative init defaults
Ensure init presets have sensible levels (-12dB not 0dB).
- ✓ Easy
- ✗ Doesn't solve existing full-blast presets

## Recommendation

**Option B** — Master fader stays put. Fits hardware synth workflow: load patch, then bring up level. Simple, safe, no UI changes.

## Decision

*Pending*
