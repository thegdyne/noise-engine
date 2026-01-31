# Telemetry Integration Plan

## Overview

Integrate the development-only DSP telemetry system from `telemetry_files/` into the noise-engine codebase, following all existing conventions (OSC_PATHS, theme, osc_bridge signal pattern, helpers).

The telemetry system streams generator internal state (phase, per-stage RMS, peak, bad values) from SC to Python for real-time debugging and ideal vs actual waveform comparison.

---

## Phase 1: Config — OSC Path Registration

**File:** `src/config/__init__.py`

Add 4 telemetry paths to `OSC_PATHS` dict using `/noise/telem/...` convention (not the spec's `/telem/...`):

```
telem_enable       → /noise/telem/enable        (Py→SC: [slot, rate])
telem_gen          → /noise/telem/gen            (SC→Py: control-rate data)
telem_wave_enable  → /noise/telem/wave/enable    (Py→SC: [slot, enable])
telem_wave         → /noise/telem/wave           (SC→Py: 128 waveform samples)
```

---

## Phase 2: OSC Bridge — Signals & Handlers

**File:** `src/audio/osc_bridge.py`

- Add 2 signals after `scope_debug_done_received` (line 46):
  - `telem_data_received = pyqtSignal(int, object)` — slot, data dict
  - `telem_waveform_received = pyqtSignal(int, object)` — slot, sample tuple
- Add 2 `dispatcher.map()` calls in `_start_server()` for `telem_gen` and `telem_wave`
- Add 2 handler methods (`_handle_telem_gen`, `_handle_telem_wave`) following the `_handle_scope_data` pattern — parse args, emit signal

---

## Phase 3: Telemetry Controller (Python)

**New file:** `src/audio/telemetry_controller.py`

Follow `ScopeController` pattern exactly:
- Constructor takes `osc_bridge`, stores reference as `self.osc`
- `enable(slot, rate)` / `disable(slot)` — sends via `self.osc.send('telem_enable', ...)`
- `enable_waveform(slot)` / `disable_waveform(slot)` — sends via `self.osc.send('telem_wave_enable', ...)`
- `on_data(slot, data)` — slot receives data dict, stores in rolling history (300 frames)
- `on_waveform(slot, samples)` — stores latest waveform as numpy array
- `snapshot()` / `export_history()` — JSON export with git hash provenance
- `IdealOverlay` class — pure numpy math for ideal waveform generation + phase alignment

Key differences from spec's `telemetry.py`:
- No standalone OSC handler registration (handled by osc_bridge)
- Uses project logger, not print()
- No UI code in this file

---

## Phase 4: Connection Wiring

**File:** `src/gui/controllers/connection_controller.py`

In `toggle_connection()` after scope setup (line 95):
- Create `TelemetryController(self.main.osc)`
- Connect `telem_data_received` and `telem_waveform_received` signals to controller slots

In disconnect block (after line 131):
- Disconnect telemetry signals
- Disable and null out telemetry controller

In `on_connection_restored()` (after line 183):
- Reconnect telemetry signals, re-create controller if needed

---

## Phase 5: SC Telemetry Tap Infrastructure

**New file:** `supercollider/core/telemetry_tap.scd`

Rewritten from `telemetry_files/telemetry_tap.scd` with:
- Wrapped in `~setupTelemetryTap = { ... };` function (like `~setupScopeTap`)
- Uses `~pythonAddr` from config.scd (not a new NetAddr)
- Uses `/noise/telem/...` OSC paths
- Uses `~generators[slotID]` for `.set(\telemetryRate, rate)` (1-based slots per endstage.scd)
- Uses `~intermediateBus[slot]` for waveform capture input
- Waveform capture SynthDef: zero-crossing triggered, 128-sample buffer, 12Hz burst cap
- State arrays: `~telemetry.enabled[8]`, `~telemetry.waveBuffers[8]`, `~telemetry.waveSynths[8]`
- OSCdef handlers: `\telemEnable`, `\telemWaveEnable`, `\telemWaveReady`

**File to modify:** `supercollider/init.scd` — add `~setupTelemetryTap.()` after scope tap setup

---

## Phase 6: B258 Generator Telemetry Taps

**File:** `packs/core/generators/b258_dual_morph.scd`

Add to existing SynthDef (currently 66 lines):
- Add `telemetryRate=0` arg, `slotIndex=0` arg to SynthDef signature
- Add `Phasor.ar` for normalized phase tracking (0-1), convert to kr via `A2K.kr`
- Tap 3 stages: `stage1 = sine` (line 40), `stage2 = sig` after XFade2 (line 55), `stage3 = sig` after final LeakDC (line 61)
- Add `Amplitude.ar` for per-stage RMS, `Peak.ar` for peak detection
- Add `CheckBadValues.ar` for NaN/inf detection
- Conditional `SendReply.kr(Impulse.kr(telemetryRate), '/noise/telem/gen', [...], slotIndex)` — zero rate = no overhead

Do NOT refactor existing DSP or switch to helpers — that's a separate concern.

---

## Phase 7: Telemetry Widget (UI)

**New file:** `src/gui/telemetry_widget.py`

Rewritten from `telemetry_files/telemetry.py` UI portion:
- All colors from `theme.py` COLORS dict (no hardcoded hex)
- All fonts from `FONT_SIZES` / `FONT_FAMILY` / `MONO_FONT`
- Slot selector (1-8) + enable/disable toggle
- Parameter labels grid (FRQ, P0-P4)
- 3 vertical RMS meters (stage 1/2/3) with dB color grading
- Peak indicator with green/orange/red thresholds
- Core Lock warning (bad value indicator)
- Waveform display using QPainter (following `ScopeDisplay` pattern, no PyQtGraph dependency)
- Ideal overlay trace (phase-aligned)
- Snapshot + export buttons
- Opens as separate window (not docked)

**File:** `src/gui/main_frame.py` — add `Ctrl+Shift+T` shortcut to open telemetry window

---

## Files Summary

### Create (3):
| File | Purpose |
|------|---------|
| `src/audio/telemetry_controller.py` | Python controller, history, ideal overlay, snapshots |
| `src/gui/telemetry_widget.py` | Themed UI widget with meters + waveform display |
| `supercollider/core/telemetry_tap.scd` | SC-side OSC handlers, buffer mgmt, waveform capture |

### Modify (5):
| File | Change |
|------|--------|
| `src/config/__init__.py` | Add 4 OSC paths to OSC_PATHS |
| `src/audio/osc_bridge.py` | Add 2 signals, 2 handlers, 2 dispatcher mappings |
| `src/gui/controllers/connection_controller.py` | Wire telemetry at connect/disconnect/reconnect |
| `src/gui/main_frame.py` | Add Ctrl+Shift+T shortcut |
| `packs/core/generators/b258_dual_morph.scd` | Add telemetryRate arg + conditional SendReply |

### Do NOT modify:
| File | Reason |
|------|--------|
| `supercollider/init.scd` | Need to add `~setupTelemetryTap.()` call |

Wait — `init.scd` DOES need modification. Updated above.

### Modify (6 total):
Add `supercollider/init.scd` — add `~setupTelemetryTap.()` call after scope tap setup.

---

## Verification

1. **SSOT check:** `bash tools/ssot.sh` — verify all new OSC paths are properly registered
2. **Python import:** `python -c "from src.audio.telemetry_controller import TelemetryController"` — no import errors
3. **Widget launch:** Start app, Ctrl+Shift+T opens telemetry window without crash
4. **SC load:** Verify `init.scd` loads telemetry_tap without errors in SC post window
5. **End-to-end:** Enable telemetry on a slot with B258 loaded, verify data flows to widget
6. **Disable:** Verify telemetryRate=0 produces zero SendReply overhead
7. **Disconnect/reconnect:** Verify telemetry survives SC reconnection cycle
