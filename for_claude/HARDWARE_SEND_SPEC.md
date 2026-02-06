# Hardware Send via Telemetry Tap Infrastructure

---
status: approved
date: 2026-02-06
effort: small-medium (1-2 sessions)
session-type: build
---

## What

Route generator audio from the intermediate bus to configurable MOTU M6 physical outputs (3-4 or 5-6), bypassing end-stage/channel/master. Reuses the telemetry tap point — same bus, new consumer.

## Why

The morph mapper can characterize external hardware (filters, wavefolders, VCAs) but currently requires an external oscillator as the input signal. External oscillators drift and are fiddly to set up. We already have `reference_sine` and 30 other generators — we just can't route them out to hardware independently.

**Unlocks:** Fully automated external hardware profiling. Load `reference_sine` → send to outputs 3-4 → patch into wavefolder → capture response on input 1 → morph mapper sweeps CV while telemetry captures the result. No external oscillator needed.

## How

### Signal Path

```
Generator → Intermediate Bus → [existing tap point]
                                      ↓
                          ┌───────────┴───────────┐
                    Telemetry Analysis       Hardware Send (NEW)
                    (existing, unchanged)          ↓
                                            Out.ar(physicalBus)
                                            → MOTU 3-4 or 5-6
```

Normal signal flow (→ end-stage → channel → master → outputs 1-2) is unaffected.

### Output Pair Mapping

`output_pair` is **1-based** (0 is blocked — see D4). Maps to physical outputs and SC bus indices as follows:

| output_pair | Physical Outputs | SC base channel (0-based) | Formula |
|------------:|-----------------|--------------------------|---------|
| 1 | 3–4 | 2 | `2 + (1-1)*2 = 2` |
| 2 | 5–6 | 4 | `2 + (2-1)*2 = 4` |

**Formula:** `baseChan = 2 + ((outPair - 1) * 2)`

Outputs 1–2 (SC channels 0–1) are the main mix and are never used by hardware send.

```supercollider
// Illustrative — output_pair to SC bus index
var baseChan = 2 + ((outPair - 1) * 2);
Out.ar(baseChan, sig);  // sig is stereo [2 channels]
```

### Components

**1. SynthDef: `forge_hardware_send`**
- Reads intermediate bus for slot (same as telemetry tap)
- Applies gain trim (dB) + safety `Limiter.ar(0.95)`
- Writes to physical output pair via `Out.ar(baseChan, sig)`
- Args: `|slot, outPair, gainDB|`

**2. Python API (on TelemetryController)**
```python
enable_hardware_send(slot, output_pair=1, level_db=0.0)
disable_hardware_send(slot)
```
- Validation: slot 0-7, output_pair must be integer >= 1 (raises `ValueError` otherwise), level -40 to +6 dB
- Default `level_db=0.0` is transparent; `-6.0` dB recommended for sensitive hardware profiling
- Sends OSC to spawn/free the send synth
- Tracks active sends in `self.hardware_sends` dict

**3. OSC path pair**
- `/noise/telem/hw_send/enable [slot, outPair, gainDB]`
- `/noise/telem/hw_send/disable [slot]`

**4. SC responders** — spawn/free `forge_hardware_send` synth, store in `~hardwareSendSynths[slot]`

### Persistence Across Generator Swaps

Hardware send is **disabled** when a generator is swapped, unloaded, or the slot is otherwise reconfigured. User must explicitly re-enable hardware send after a swap. This matches existing telemetry behavior where telemetry disables on generator swap — hardware send follows the same lifecycle.

### Integration with Morph Mapper

```python
# Send reference_sine out to hardware via outputs 3-4
telem.enable_hardware_send(slot=1, output_pair=1, level_db=-6.0)

# Morph mapper captures hardware response on input 1
mapper = MorphMapper(
    device_type="wavefolder",
    input_reference={'type': 'sine', 'freq_hz': 220, 'source': 'hardware_send/slot1'},
    # ... rest of config
)
```

Physical patch: MOTU Out 3 → Wavefolder In → Wavefolder Out → MOTU In 1

## Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Tap intermediate bus (pre-end-stage) | Pure generator output, zero coloration, matches telemetry tap |
| D2 | Allow summing if multiple sends target same outputs | Standard SC `Out.ar` behavior, user manages conflicts |
| D3 | Mandatory safety limiter | Prevents hardware/speaker damage, minimal coloration below threshold |
| D4 | Block output_pair=0; output_pair must be >= 1 | Prevents accidental conflict with main mix on outputs 1-2. Validation raises `ValueError`. |
| D5 | Hardware send disabled on generator swap | Matches telemetry lifecycle. User re-enables explicitly after swap. |
| D6 | Telemetry + hardware send can coexist on same slot | Both read intermediate bus non-destructively |

## Scope Boundaries

**In scope:**
- SynthDef, Python API, OSC handlers, SC responders
- Safety limiting
- Works alongside existing telemetry (same tap point, parallel consumer)

**Out of scope (defer):**
- UI controls (console-only for now, like early morph mapper)
- Preset integration
- Return path routing (hardware FX loops)
- Pre/post end-stage tap selection
- Mono send option

## Verification

```python
# 1. Load reference_sine into slot 0, enable hardware send
audio_controller.load_generator(slot=0, pack="core", gen="reference_sine")
audio_controller.set_frequency(slot=0, freq=440)
telem.enable_hardware_send(slot=0, output_pair=1, level_db=-6.0)
# CHECK: 440Hz tone on MOTU outputs 3-4, still in main mix

# 2. Disable
telem.disable_hardware_send(slot=0)
# CHECK: Gone from 3-4, still in main mix

# 3. Coexist with telemetry on slot 0
telem.enable(slot=0, rate=15)
telem.enable_hardware_send(slot=0, output_pair=1)
# CHECK: Both working simultaneously

# 4. Multiple slots — independent routing
telem.enable_hardware_send(slot=0, output_pair=1)  # Slot 0 → outputs 3-4
telem.enable_hardware_send(slot=1, output_pair=2)  # Slot 1 → outputs 5-6
# CHECK: Independent routing

# 5. P0: Generator swap disables hardware send
telem.enable_hardware_send(slot=0, output_pair=1)
audio_controller.load_generator(slot=0, pack="core", gen="bright_saw")
# CHECK: Hardware send on slot 0 is now disabled, outputs 3-4 silent
# P0 REQUIREMENT: Generator load/swap code path MUST call
# telem.disable_hardware_send(slot) (or equivalent OSC /disable)
# to prevent lingering synths.

# 6. Validation rejects invalid output_pair
telem.enable_hardware_send(slot=0, output_pair=0)  # Raises ValueError
```

## Open Questions

None. (Resolved: default `level_db=0.0` dB for transparency; docs recommend `-6.0` dB for profiling; limiter is mandatory.)

## Files Changed

- `supercollider/core/telemetry_tap.scd` — SynthDef + responders
- `supercollider/core/init.scd` — boot call
- `src/audio/telemetry_controller.py` — Python API
- `src/audio/osc_bridge.py` — OSC handler mapping
