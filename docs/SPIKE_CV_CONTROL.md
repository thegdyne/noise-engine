# Spike: CV Control via MIDI-CV.OCD

**Date:** 2026-02-03
**Status:** Complete
**Branch:** `claude/cv-scaler-7sNCO`

## Summary

Built tooling to send CV from Python via MIDI→CV.OCD for controlling external hardware (Buchla 258). This enables closed-loop hardware profiling: CV out to control parameters, audio in via existing telemetry capture.

## Hardware Chain

```
┌─────────────────────────────────────────────────────────────────┐
│                        CV OUTPUT PATH                           │
├─────────────────────────────────────────────────────────────────┤
│  Python (MidiCV class)                                          │
│      │                                                          │
│      ▼ MIDI CC1, Channel 1                                      │
│  MOTU M6 MIDI Out                                               │
│      │                                                          │
│      ▼                                                          │
│  CV.OCD (MIDI-to-CV converter)                                  │
│      │                                                          │
│      ▼ CVA output (0-5V)                                        │
│  Buchla 258 Morph CV input                                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                     AUDIO CAPTURE PATH                          │
│                   (existing telemetry)                          │
├─────────────────────────────────────────────────────────────────┤
│  Buchla 258 Audio Out                                           │
│      │                                                          │
│      ▼                                                          │
│  MOTU M6 Audio In (device 3, 10 inputs)                         │
│      │                                                          │
│      ▼                                                          │
│  Generic Hardware Profiler (external_telemetry pack)            │
│      │                                                          │
│      ▼                                                          │
│  Telemetry Widget (waveform + metrics display)                  │
└─────────────────────────────────────────────────────────────────┘
```

## Files Created

### `src/hardware/midi_cv.py`

MIDI-CV controller class for sending control voltages via CV.OCD.

```python
from hardware.midi_cv import MidiCV, find_motu_port

# Context manager usage
with MidiCV(port_name="M6", cc_number=1, channel=0) as cv:
    cv.send_cv(0)        # Send CC value 0-127
    cv.send_cv(127)
    cv.send_cv_normalized(0.5)  # Send normalized 0.0-1.0

    # Sweep with callback
    cv.sweep(start=0, end=127, step=4, delay=0.1,
             callback=lambda v: print(f"CV={v}"))

# List available ports
print(MidiCV.list_ports())  # ['IAC Driver Bus 1', 'M6']

# Auto-find MOTU
port = find_motu_port()  # Returns 'M6' or None
```

**Key methods:**
| Method | Description |
|--------|-------------|
| `list_ports()` | Static method, returns available MIDI output ports |
| `open()` / `close()` | Manual port management (or use context manager) |
| `send_cv(value)` | Send CC value 0-127 |
| `send_cv_normalized(value)` | Send normalized value 0.0-1.0 |
| `sweep(start, end, step, delay, callback)` | Sweep through CV range |

### `tools/hw_characterize.py`

CLI tool for hardware characterization sweeps.

```bash
# List devices
python tools/hw_characterize.py --list-devices

# Manual interactive test
python tools/hw_characterize.py --manual --midi-port "M6"

# Automated sweep with audio capture
python tools/hw_characterize.py --sweep --midi-port "M6" --audio-device 3

# Custom sweep range
python tools/hw_characterize.py --sweep --midi-port "M6" --audio-device 3 \
    --start 0 --end 127 --step 4 --settle 0.1 --capture 0.2
```

**CLI options:**
| Option | Default | Description |
|--------|---------|-------------|
| `--list-devices` | - | List MIDI ports and audio devices |
| `--manual` | - | Interactive CC test mode |
| `--sweep` | - | Automated sweep with audio capture |
| `--midi-port` | auto | MIDI output port name |
| `--audio-device` | - | Audio input device index |
| `--cc` | 1 | CC number (CV.OCD CVA = CC1) |
| `--channel` | 1 | MIDI channel 1-16 |
| `--start` | 0 | Sweep start CC value |
| `--end` | 127 | Sweep end CC value |
| `--step` | 4 | Sweep increment |
| `--settle` | 0.1 | Seconds to wait after CC change |
| `--capture` | 0.2 | Audio capture duration per step |
| `--output` | `characterization_results.json` | Output file |

## CV.OCD Configuration

Configure via https://six4pix.net/cvocd/

**CVA settings:**
- CV Source: `MIDI CC`
- Channel: `1`
- CC#: `Modwheel` (CC1)
- Range: `5V` (0-5V unipolar)

Send configuration to device via USB before use.

## Hardware Discovery

On the test system (macOS + MOTU M6):

```
=== MIDI Output Ports ===
  [0] IAC Driver Bus 1
  [1] M6                    ← Use this

=== Audio Devices ===
  0 BlackHole 2ch
  1 MacBook Pro Microphone
  2 MacBook Pro Speakers
* 3 M6 (10 in, 4 out)       ← Use this (index 3)
  4 MOTU+BH
  5 M6 Multi Output Device
```

## Characterization Results

Sample output from `characterization_results.json`:

```json
{
  "metadata": {
    "timestamp": "2026-02-03T10:52:34.863156",
    "midi_port": "M6",
    "audio_device": 3,
    "sample_rate": 48000,
    "cc_number": 1,
    "channel": 1
  },
  "measurements": [
    {"cc_value": 0, "frequency_hz": 43.57, "rms": 0.301473},
    {"cc_value": 64, "frequency_hz": 43.46, "rms": 0.294679},
    {"cc_value": 124, "frequency_hz": 43.54, "rms": 0.272912}
  ]
}
```

**Observation:** Frequency constant (~43.5 Hz) because CV controls morph (waveshape), not pitch. RMS decreases slightly as morph increases, indicating timbral change.

## Integration with Existing Telemetry

### Current State

The telemetry system already handles the **audio capture side**:

1. **Generic Hardware Profiler** (`packs/external_telemetry/`)
   - Reads MOTU M6 inputs (P0 selects channel 0-5)
   - Level normalization (P1)
   - Reference shape selection (P2: sine/square/saw)

2. **Telemetry Widget** (`src/gui/telemetry_widget.py`)
   - Real-time waveform display
   - Living Proof metrics (Crest Factor, HF Energy, DC Shift)
   - Digital Twin comparison with ideal overlay

### Missing Integration

The CV output path is **not yet integrated** into the app. Current tools are standalone Python scripts.

### Proposed Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                   INTEGRATED CV SCALER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TelemetryWidget                                                │
│      │                                                          │
│      ├── [existing] Audio capture via HW Profiler               │
│      │                                                          │
│      └── [NEW] CV Output Control                                │
│              │                                                  │
│              ▼                                                  │
│          CVController (wrapper around MidiCV)                   │
│              │                                                  │
│              ├── Manual CV slider in telemetry widget           │
│              ├── Automated sweep button                         │
│              └── Sync CV value with generator params?           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Integration options:**

1. **Telemetry Widget Extension**
   - Add CV output slider/control to telemetry widget
   - "CV Sweep" button that runs sweep while capturing waveforms
   - Display CV value alongside captured metrics

2. **New Hardware Control Module**
   - `src/hardware/cv_controller.py` - App-integrated CV controller
   - OSC commands for CV control from SC or Python
   - Settings persistence for MIDI port configuration

3. **Generator Integration**
   - Map generator custom params (P0-P4) to CV outputs
   - Bidirectional: app param → CV out, or external CV → app display

## Dependencies

```bash
pip install mido python-rtmidi numpy sounddevice
```

**Note:** `sounddevice` requires PortAudio. On macOS this is included; on Linux install `libportaudio2`.

## Next Steps

1. **Decide integration approach** - Telemetry widget extension vs. separate module
2. **Add MIDI port configuration** - Settings UI or auto-detection
3. **Implement CVController** - App-aware wrapper with Qt signals
4. **Add CV controls to telemetry widget** - Slider + sweep button
5. **Test closed-loop workflow** - CV out → 258 morph → audio in → waveform display

## Files Reference

| File | Purpose |
|------|---------|
| `src/hardware/__init__.py` | Package init |
| `src/hardware/midi_cv.py` | MidiCV controller class |
| `tools/hw_characterize.py` | CLI characterization tool |
| `characterization_results.json` | Sample sweep output (on cv-scaler branch) |

## Related Documentation

- `docs/TELEMETRY_USER_GUIDE.md` - Existing telemetry system docs
- `packs/external_telemetry/manifest.json` - Hardware profiler pack
- `src/audio/telemetry_controller.py` - Telemetry controller implementation
- `src/gui/telemetry_widget.py` - Telemetry UI widget
