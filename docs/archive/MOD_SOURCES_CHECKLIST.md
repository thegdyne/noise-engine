# Modulation Sources - Implementation Checklist

**Last Updated:** December 16, 2025

---

## LFO

### ✅ Done

- [x] Clock-synced operation (x32 master clock)
- [x] 12 clock rates: /64, /32, /16, /8, /4, /2, 1, x2, x4, x8, x16, x32
- [x] 8 waveforms: Saw, Ramp, Sqr, Tri, Sin, Rect+, Rect-, S&H
- [x] Shape distortion (centre point shift / PWM)
- [x] 3 independent outputs (A, B, C)
- [x] Per-output waveform selection
- [x] Per-output phase offset (8 steps: 0°-315°)
- [x] Per-output invert (NORM/INV)
- [x] Default phases spread at ~120° (0°, 135°, 225°)
- [x] Frequency derived from BPM (stays in sync)
- [x] Smooth Phasor-based phase (no stepping)
- [x] RATE slider with drag control
- [x] SHAP slider with drag control
- [x] FREE mode (non-clocked, manual frequency 0.01-100Hz)
- [x] Mode toggle: CLK / FREE (via MODE param slider)
- [x] MOD_LFO_MODES config constant
- [x] MOD_LFO_FREQ_MIN/MAX config constants

### ⬜ TODO

- [ ] Waveform preview icons (visual indicator of shape)
- [ ] Reset phase button (force all outputs to 0°)
- [ ] Tooltips on all controls

---

## Sloth

### ✅ Done

- [x] 3 speed modes: Torpor (~20s), Apathy (~75s), Inertia (~33min)
- [x] Chaos-like slowly varying CV
- [x] Bias control (attractor weighting)
- [x] 3 outputs: X, Y, Z
- [x] Z = inverted Y (per NLC design)
- [x] Per-output invert (NORM/INV)
- [x] MODE slider with drag control
- [x] BIAS slider with drag control
- [x] Timings within NLC Triple Sloth spec

### ⬜ TODO

- [ ] True Lorenz system implementation (more accurate chaos)
- [ ] Freeze button (hold current values)
- [ ] Tooltips on all controls

---

## Scope Display

### ✅ Done

- [x] Real-time oscilloscope per slot
- [x] 3 traces colour-coded (green/cyan/orange from skin)
- [x] Circular buffer (128 samples)
- [x] ~30fps update rate (SC side)
- [x] UI throttling (not per-message repaint)
- [x] Bipolar display (-1 to +1)
- [x] Grid with center line
- [x] Enabled/disabled based on generator type

### ⬜ TODO

- [ ] Auto-ranging time scale (based on LFO rate / Sloth mode)
- [ ] Unipolar display mode (0 to 1)
- [ ] Trace visibility toggles
- [ ] Trigger/sync mode
- [ ] Freeze button

---

## UI / Slot

### ✅ Done

- [x] 4 mod source slots
- [x] 2×2 grid layout (aligned with generator rows)
- [x] Generator CycleButton (Empty/LFO/Sloth)
- [x] CycleButton wrap=True by default
- [x] Dynamic UI based on generator type
- [x] Output rows with labels (A/B/C or X/Y/Z)
- [x] Per-output waveform button (LFO only)
- [x] Per-output phase button (LFO only)
- [x] Per-output polarity button
- [x] Parameter sliders (RATE/SHAP or MODE/BIAS)
- [x] Border colour from skin accents (cyan=LFO, orange=Sloth)
- [x] Default generators on startup: LFO/Sloth/LFO/Sloth
- [x] State sync on connect (sends current UI values to SC)

### ⬜ TODO

- [ ] Tooltips on all controls
- [ ] Empty state polish (scope flat/disabled)
- [ ] Consistent spacing refinement
- [ ] Window resize behaviour testing
- [ ] Remove "COMING SOON" badge (if still present)
- [ ] Generator selector scroll dead zone: name length changes cause scroll to miss (need fixed-width hit area)
- [ ] Generator buttons outside slot frame: visual containment issue

---

## SuperCollider

### ✅ Done

- [x] 12 mod buses allocated (`~modBuses`)
- [x] Bus index helper (`~modBusIndex`)
- [x] Mod slot manager (`~startModSlot`, `~freeModSlot`)
- [x] modLFO SynthDef
- [x] modSloth SynthDef
- [x] OSC handlers for all mod messages
- [x] Scope value streaming (~30fps)
- [x] Enable/disable streaming per slot
- [x] Clock source: x32 (index 12)
- [x] Ticks per cycle array in config.scd
- [x] BPM-derived frequency for LFO
- [x] FREE mode frequency input for LFO (0.01-100Hz exponential mapping)

### ⬜ TODO

- [ ] Scope streaming rate adjustment based on mod rate

---

## Config / SSOT

### ✅ Done

- [x] `MOD_SLOT_COUNT = 4`
- [x] `MOD_OUTPUTS_PER_SLOT = 3`
- [x] `MOD_BUS_COUNT = 12`
- [x] `MOD_GENERATOR_CYCLE = ["Empty", "LFO", "Sloth"]`
- [x] `MOD_LFO_WAVEFORMS` (8 waveforms)
- [x] `MOD_LFO_PHASES` (8 steps)
- [x] `MOD_SLOTH_MODES` (3 modes)
- [x] `MOD_CLOCK_RATES` (12 rates)
- [x] `MOD_CLOCK_SOURCE_INDEX = 12`
- [x] `MOD_CLOCK_TICKS_PER_CYCLE` (12 values)
- [x] `MOD_POLARITY = ["NORM", "INV"]`
- [x] `MOD_OUTPUT_LABELS` dict
- [x] OSC paths in config
- [x] JSON configs for LFO and Sloth
- [x] SC config mirrors Python (`~modClockSourceIndex`, etc.)
- [x] `MOD_LFO_MODES = ["CLK", "FREE"]`
- [x] `MOD_LFO_FREQ_MIN = 0.01`, `MOD_LFO_FREQ_MAX = 100`

### ⬜ TODO

(None - all config items complete)

---

## Skin Integration

### ✅ Done

- [x] `accent_mod_lfo` colour (cyan #00ccff)
- [x] `accent_mod_sloth` colour (orange #ff8800)
- [x] Slot border uses accent colours
- [x] Scope traces use skin colours
- [x] Scope grid uses skin colours

### ⬜ TODO

- [ ] Output label colours from skin
- [ ] Button colours from skin (currently using generic)

---

## Routing (Future Feature)

### ⬜ TODO

- [ ] Mod routing matrix design
- [ ] Connect mod buses to generator parameters
- [ ] Per-connection depth control
- [ ] Visual feedback on modulated parameters
- [ ] Mod amount display on target sliders

---

## Summary

| Category | Done | TODO |
|----------|------|------|
| LFO | 17 | 3 |
| Sloth | 10 | 3 |
| Scope | 9 | 5 |
| UI/Slot | 16 | 7 |
| SuperCollider | 12 | 1 |
| Config/SSOT | 17 | 0 |
| Skin | 5 | 2 |
| Routing | 0 | 5 |
| **Total** | **86** | **26** |

**~77% complete** (core functionality done, polish and advanced features remaining)
