# Noise Engine Telemetry System User Guide

**Version:** 1.0  
**Date:** February 2, 2026  
**Audience:** New users and returning developers

---

## Table of Contents

1. [Overview](#overview)
2. [Telemetry Types](#telemetry-types)
3. [Creating a Digital Twin](#creating-a-digital-twin)
4. [Forensic Generator Analysis](#forensic-generator-analysis)
5. [OSC Command Reference](#osc-command-reference)
6. [Data Format Specifications](#data-format-specifications)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The Noise Engine telemetry system provides **real-time insight** into generator behavior at multiple stages of the signal path. It enables:

- **Digital Twin Creation**: Capture complete generator state for hardware profiling or AI model training
- **Forensic Analysis**: Debug unexpected behavior by examining internal signal stages
- **Quality Validation**: Verify generator output matches expected characteristics

### Key Concepts

**Telemetry Types:**
- **INTERNAL**: Infrastructure-based tap using `forge_internal_telem_tap` (works with ANY generator)
- **EXTERNAL**: Embedded `SendReply` in generator SynthDef (e.g., `hw_profile_tap` in `b258_dual_morph`)

**Capture Modes:**
- **Parameter Telemetry**: Real-time control values + audio metrics (RMS, peak, frequency)
- **Waveform Capture**: Cycle-accurate audio buffer snapshots

---

## Telemetry Types

### INTERNAL Telemetry (Infrastructure Observer)

**Use when:** You need telemetry from generators that don't have embedded taps

**How it works:**
- Taps the **intermediate bus** (post-generator, pre-end-stage)
- Reads **customBus0** to access all 5 custom parameters
- Provides: RMS, peak, frequency, and all parameter values
- **Zero modification** to generator SynthDef required

**Limitations:**
- Cannot access internal signal stages (e.g., `stage1`, `stage2`)
- Single RMS value repeated for all stages (simplified view)

### EXTERNAL Telemetry (Embedded SendReply)

**Use when:** You need multi-stage visibility into generator internals

**How it works:**
- Generator SynthDef includes `SendReply.kr()` calls at strategic tap points
- Exposes internal variables (e.g., `stage1`, `stage2`, `stage3`)
- Triggered by `telemetryRate` parameter
- **Example:** `forge_core_b258_dual_morph` exposes:
  - `stage1`: Pure sine seed (pre-morph)
  - `stage2`: Post-XFade2 output (morphed signal)
  - `stage3`: Final output (post-LeakDC)

**Requirements:**
- Generator must have `telemetryRate` parameter in SynthDef signature
- Tap points must be declared as `var` and captured with `SendReply.kr()`

---

## Creating a Digital Twin

### What is a Digital Twin?

A **digital twin** is a complete capture of:
1. Generator configuration (pack, generator ID, custom params)
2. Real-time audio characteristics (frequency, RMS, peak)
3. Waveform snapshots (cycle-accurate audio data)
4. Internal signal stages (if using EXTERNAL telemetry)

This data can be used to:
- Profile hardware synthesizers
- Train AI models on generator behavior
- Validate pack generation quality
- Compare generators across different configurations

### Example: B258 Dual Morph Digital Twin

**Pack:** `core` (Noise Engine core generators)  
**Generator:** `b258_dual_morph` (B258 Dual Oscillator with embedded telemetry)

#### Step 1: Load the Generator

```python
# Via Noise Engine GUI
# 1. Open Pack Browser
# 2. Select "core" pack
# 3. Load "B258 Dual Morph" into Slot 1
```

#### Step 2: Enable EXTERNAL Telemetry

Send OSC command to enable embedded telemetry at 10 Hz:

```python
from pythonosc import udp_client

client = udp_client.SimpleUDPClient("127.0.0.1", 57120)

# Enable telemetry on Slot 1 at 10 Hz
slot = 1
rate = 10  # Hz
client.send_message("/noise/telem/enable", [slot, rate])
```

**What happens:**
- SuperCollider sets `telemetryRate=10` on the generator synth
- Embedded `SendReply.kr()` starts firing at 10 Hz
- Data includes `stage1`, `stage2`, `stage3` taps

#### Step 3: Enable Waveform Capture

```python
# Enable waveform capture for Slot 1
client.send_message("/noise/telem/wave/enable", [slot, 1])
```

**What happens:**
- Allocates 256-sample buffer for cycle capture
- `forge_telemetry_wave_capture` synth monitors intermediate bus
- Triggers on zero-crossings, sends `/noise/telem/wave/ready` when frame complete
- Python receives 128-sample waveform snapshots at ~10 Hz

#### Step 4: Capture Data in Python

```python
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import BlockingOSCUDPServer

data_log = []

def handle_gen_data(addr, *args):
    """Handle /noise/telem/gen messages."""
    slot, freq, phase, p0, p1, p2, p3, p4, rms1, rms2, rms3, peak, badval, peak3 = args
    data_log.append({
        'timestamp': time.time(),
        'type': 'gen',
        'slot': slot,
        'freq': freq,
        'params': [p0, p1, p2, p3, p4],
        'stages': {'rms1': rms1, 'rms2': rms2, 'rms3': rms3},
        'peak': peak,
        'badval': badval
    })

def handle_wave_data(addr, *args):
    """Handle /noise/telem/wave messages."""
    slot = args[0]
    waveform = args[1:]  # 128 samples
    data_log.append({
        'timestamp': time.time(),
        'type': 'wave',
        'slot': slot,
        'waveform': list(waveform)
    })

dispatcher = Dispatcher()
dispatcher.map("/noise/telem/gen", handle_gen_data)
dispatcher.map("/noise/telem/wave", handle_wave_data)

server = BlockingOSCUDPServer(("127.0.0.1", 57130), dispatcher)
print("Listening for telemetry on port 57130...")
server.serve_forever()
```

#### Step 5: Export Digital Twin

After capturing 10-60 seconds:

```python
import json

twin = {
    'generator': {
        'pack': 'core',
        'id': 'b258_dual_morph',
        'synthdef': 'forge_core_b258_dual_morph'
    },
    'capture': {
        'duration_sec': 30,
        'sample_rate': 10,  # Hz
        'data': data_log
    },
    'metadata': {
        'date': '2026-02-02',
        'slot': 1,
        'notes': 'Morph sweep from sine to square/saw'
    }
}

with open('b258_digital_twin.json', 'w') as f:
    json.dump(twin, f, indent=2)
```

---

## Forensic Generator Analysis

### When to Use Forensic Analysis

- Generator produces unexpected output (distortion, silence, clipping)
- Parameter changes don't produce expected effect
- BadValue detector triggers (NaN/Inf in signal)
- Debugging new generator implementations

### Example: Debugging Distortion in Custom Generator

**Scenario:** User reports harsh distortion when `saturation` parameter exceeds 0.8

#### Step 1: Enable INTERNAL Tap (Any Generator)

```python
from pythonosc import udp_client

client = udp_client.SimpleUDPClient("127.0.0.1", 57120)

# Enable INTERNAL tap on Slot 3 at 20 Hz with calibration gain
slot = 3
rate = 20
cal_gain = 1.0  # Adjust if generator output is scaled

client.send_message("/noise/telem/tap/enable", [slot, rate, cal_gain])
```

**What happens:**
- `forge_internal_telem_tap` synth spawns
- Reads intermediate bus (stereo signal pre-end-stage)
- Reads `customBus0` to access all 5 parameters
- Sends `/noise/telem/gen` at 20 Hz

**Note:** INTERNAL tap provides **simplified stages** (RMS repeated 3x) since it cannot access generator internals.

#### Step 2: Capture During Parameter Sweep

```python
import time
from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
import threading

forensic_log = []

def handle_gen_data(addr, *args):
    slot, freq, phase, p0, p1, p2, p3, p4, rms1, rms2, rms3, peak, badval, peak3 = args
    forensic_log.append({
        'time': time.time(),
        'freq': freq,
        'saturation': p4,  # Assuming P4 is saturation
        'rms': rms1,
        'peak': peak,
        'badval': badval
    })
    
    # Alert on anomalies
    if badval > 0:
        print(f"⚠️  BadValue detected! sat={p4:.2f} peak={peak:.4f}")
    if peak > 1.0:
        print(f"⚠️  Clipping detected! sat={p4:.2f} peak={peak:.4f}")

dispatcher = Dispatcher()
dispatcher.map("/noise/telem/gen", handle_gen_data)

server = ThreadingOSCUDPServer(("127.0.0.1", 57130), dispatcher)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()

# Now sweep saturation parameter via GUI or OSC
# Watch for alerts in console
```

#### Step 3: Automated Parameter Sweep

```python
import numpy as np
import time

# Sweep saturation from 0.0 to 1.0 over 10 seconds
for sat in np.linspace(0.0, 1.0, 100):
    # Send to customBus4 (P5 = saturation)
    # (This assumes you have OSC control over parameters)
    client.send_message("/noise/gen/param", [slot, "saturation", sat])
    time.sleep(0.1)

# Wait for capture
time.sleep(2)

# Stop telemetry
client.send_message("/noise/telem/tap/enable", [slot, 0])
```

#### Step 4: Export for AI Analysis

```python
import pandas as pd

# Convert to DataFrame for analysis
df = pd.DataFrame(forensic_log)

# Export CSV for AI analysis
df.to_csv('forensic_saturation_sweep.csv', index=False)

# Generate summary report
summary = {
    'generator': 'unknown (Slot 3)',
    'test': 'saturation_sweep',
    'findings': {
        'badval_count': int((df['badval'] > 0).sum()),
        'clip_count': int((df['peak'] > 1.0).sum()),
        'first_clip_sat': float(df[df['peak'] > 1.0]['saturation'].min()) if (df['peak'] > 1.0).any() else None,
        'max_peak': float(df['peak'].max()),
        'max_rms': float(df['rms'].max())
    }
}

print("\n=== FORENSIC SUMMARY ===")
print(json.dumps(summary, indent=2))
```

**AI Analysis Prompt:**

```
I have telemetry data from a Noise Engine generator showing distortion above saturation=0.8.

Attached: forensic_saturation_sweep.csv

Columns:
- time: Unix timestamp
- freq: Estimated frequency (Hz)
- saturation: Parameter value (0.0-1.0)
- rms: RMS amplitude
- peak: Peak amplitude
- badval: BadValue flag (0=clean, 1=NaN/Inf)

Findings:
- 15 BadValue detections starting at saturation=0.82
- Peak exceeds 1.0 at saturation=0.78

Question: What is the likely cause of this behavior, and how should I fix the SynthDef?
```

---

## OSC Command Reference

### Enable/Disable EXTERNAL Telemetry (Embedded)

**Path:** `/noise/telem/enable`  
**Args:** `[slot, rate]`

- `slot`: Generator slot (1-8)
- `rate`: Telemetry rate in Hz (0 = disable, 1-100 = enabled)

**Example:**
```python
client.send_message("/noise/telem/enable", [1, 10])  # Slot 1, 10 Hz
client.send_message("/noise/telem/enable", [1, 0])   # Disable
```

**Effect:**
- Sets `telemetryRate` parameter on generator synth
- Only works if generator has embedded `SendReply.kr()` with `telemetryRate` gate

---

### Enable/Disable INTERNAL Tap (Infrastructure)

**Path:** `/noise/telem/tap/enable`  
**Args:** `[slot, rate, calGain]`

- `slot`: Generator slot (1-8)
- `rate`: Telemetry rate in Hz (0 = disable, 1-100 = enabled)
- `calGain`: Optional calibration gain (default 1.0)

**Example:**
```python
# Enable INTERNAL tap on Slot 2 at 20 Hz
client.send_message("/noise/telem/tap/enable", [2, 20, 1.0])

# Disable
client.send_message("/noise/telem/tap/enable", [2, 0])
```

**Effect:**
- Spawns `forge_internal_telem_tap` synth
- Taps intermediate bus + customBus0
- Works with **any generator** (no SynthDef modification required)

---

### Enable/Disable Waveform Capture

**Path:** `/noise/telem/wave/enable`  
**Args:** `[slot, enable]`

- `slot`: Generator slot (1-8)
- `enable`: 1 = enable, 0 = disable

**Example:**
```python
client.send_message("/noise/telem/wave/enable", [1, 1])  # Enable
client.send_message("/noise/telem/wave/enable", [1, 0])  # Disable
```

**Effect:**
- Allocates 256-sample buffer
- Spawns `forge_telemetry_wave_capture` synth
- Sends `/noise/telem/wave/ready` when frame captured
- Python receives 128 samples via `/noise/telem/wave`

---

## Data Format Specifications

### `/noise/telem/gen` Message Format

**Source:** EXTERNAL (embedded) or INTERNAL (infrastructure tap)

**Args:** `[slot, freq, phase, p0, p1, p2, p3, p4, rms1, rms2, rms3, peak, badval, peak3]`

| Index | Field | Type | Description |
|-------|-------|------|-------------|
| 0 | `slot` | int | Generator slot (0-7 internal index) |
| 1 | `freq` | float | Estimated frequency (Hz) via ZeroCrossing |
| 2 | `phase` | float | Phase (0.0-1.0) — always 0 for INTERNAL tap |
| 3 | `p0` | float | Custom parameter 1 (0.0-1.0) |
| 4 | `p1` | float | Custom parameter 2 (0.0-1.0) |
| 5 | `p2` | float | Custom parameter 3 (0.0-1.0) |
| 6 | `p3` | float | Custom parameter 4 (0.0-1.0) |
| 7 | `p4` | float | Custom parameter 5 (0.0-1.0) |
| 8 | `rms1` | float | Stage 1 RMS (EXTERNAL) or mono RMS (INTERNAL) |
| 9 | `rms2` | float | Stage 2 RMS (EXTERNAL) or mono RMS (INTERNAL) |
| 10 | `rms3` | float | Stage 3 RMS (EXTERNAL) or mono RMS (INTERNAL) |
| 11 | `peak` | float | Peak amplitude (INTERNAL only) |
| 12 | `badval` | float | BadValue flag (EXTERNAL only, always 0 for INTERNAL) |
| 13 | `peak3` | float | Stage 3 peak (EXTERNAL) or peak (INTERNAL) |

**INTERNAL Tap Notes:**
- `rms1 == rms2 == rms3` (single mono RMS repeated)
- `phase` always 0 (no phase bus available)
- `badval` always 0 (not monitored in tap)

---

### `/noise/telem/wave` Message Format

**Source:** Waveform capture buffer

**Args:** `[slot, sample0, sample1, ..., sample127]`

| Index | Field | Type | Description |
|-------|-------|------|-------------|
| 0 | `slot` | int | Generator slot (0-7 internal index) |
| 1-128 | `samples` | float | 128 audio samples (mono, -1.0 to +1.0) |

**Notes:**
- Captures exactly **one cycle** of the waveform (adaptive frame size)
- Triggered on zero-crossing (rising edge)
- Buffer size is 256 samples, but only first 128 sent to Python

---

## Troubleshooting

### Problem: No telemetry data received

**Check:**
1. Generator is loaded and playing (visible output on meters)
2. OSC server running in Python on port 57130
3. Correct slot number (1-8 for user, 0-7 internal index in data)
4. For EXTERNAL: Generator has `telemetryRate` parameter
5. For INTERNAL: Intermediate bus exists for slot

**Debug:**
```python
# Test OSC connectivity
client.send_message("/noise/telem/enable", [1, 10])
# Check SuperCollider post window for confirmation
```

---

### Problem: Waveform capture sends no data

**Check:**
1. Waveform capture enabled: `/noise/telem/wave/enable [slot, 1]`
2. Generator producing audio (check RMS > 0.001)
3. Zero-crossings detected (requires bipolar signal, not DC offset)

**Debug:**
```supercollider
// In SuperCollider post window
~telemetry.waveBuffers[0].plot;  // Slot 1 (0-indexed)
```

---

### Problem: BadValue flags constantly triggering

**Cause:** Generator producing NaN or Inf values

**Fix:**
1. Check parameter ranges (extreme values may break DSP)
2. Add `CheckBadValues.ar(sig, post: 1)` to generator for debugging
3. Use `LeakDC.ar()` and `Limiter.ar()` in output stage
4. Review division by zero or `log(negative)` operations

---

### Problem: INTERNAL tap shows wrong parameter values

**Cause:** Mismatch between `customBus0` index and actual bus allocation

**Fix:**
1. Verify generator is using unified bus architecture
2. Check `endstage.scd` for correct `customBus` index lookup
3. For legacy generators, use EXTERNAL telemetry instead

---

### Problem: Telemetry rate too slow/fast

**Adjust:**
```python
# Increase rate for faster updates (max ~100 Hz)
client.send_message("/noise/telem/tap/enable", [1, 50, 1.0])

# Decrease rate to reduce CPU load
client.send_message("/noise/telem/tap/enable", [1, 5, 1.0])
```

**Note:** Rates above 50 Hz may saturate OSC bandwidth

---

## Advanced Use Cases

### Calibration Gain for Hardware Profiling

When creating digital twins of hardware synthesizers, output levels may not match Noise Engine's internal scaling.

**Solution:** Use `calGain` parameter to match RMS levels

```python
# Hardware outputs at -6 dBFS, Noise Engine expects -12 dBFS
cal_gain = 10 ** ((-6 - (-12)) / 20)  # = 2.0

client.send_message("/noise/telem/tap/enable", [1, 10, cal_gain])
```

---

### Multi-Slot Comparative Analysis

Capture telemetry from multiple slots simultaneously to compare generators:

```python
# Enable INTERNAL taps on Slots 1-4
for slot in range(1, 5):
    client.send_message("/noise/telem/tap/enable", [slot, 10, 1.0])

# Data will be tagged with slot index for differentiation
```

---

### Exporting for Machine Learning

Telemetry data can train AI models to predict generator behavior:

```python
import numpy as np

# Convert captured data to feature matrix
X = np.array([[d['params'][0], d['params'][1], d['params'][2], 
               d['params'][3], d['params'][4]] for d in data_log if d['type'] == 'gen'])
y = np.array([d['stages']['rms3'] for d in data_log if d['type'] == 'gen'])

# Train model (e.g., sklearn RandomForest)
from sklearn.ensemble import RandomForestRegressor
model = RandomForestRegressor()
model.fit(X, y)

# Predict output RMS from parameter settings
predicted_rms = model.predict([[0.5, 0.7, 0.3, 0.5, 0.8]])
```

---

## Summary

**Digital Twin Creation:**
1. Load generator (e.g., `core/b258_dual_morph`)
2. Enable EXTERNAL telemetry: `/noise/telem/enable [slot, rate]`
3. Enable waveform capture: `/noise/telem/wave/enable [slot, 1]`
4. Capture data via OSC server
5. Export JSON with full state + waveforms

**Forensic Analysis:**
1. Enable INTERNAL tap: `/noise/telem/tap/enable [slot, rate, calGain]`
2. Perform parameter sweeps or user interactions
3. Monitor for BadValue, clipping, RMS anomalies
4. Export CSV for AI-assisted debugging

**Key Files:**
- SuperCollider: `supercollider/core/telemetry_tap.scd`
- Python OSC: `pythonosc` library (`pip install python-osc`)

**Support:**
- Telemetry infrastructure in `~setupTelemetryTap` and `~bootTelemetryTap`
- Generator example: `forge_core_b258_dual_morph` (embedded telemetry)
- Python example: See above OSC server implementations

---

**End of Guide**
