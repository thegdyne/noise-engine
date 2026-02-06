# CA Instructions: Hardware Send Implementation

**Spec:** `HARDWARE_SEND_SPEC.md` (approved, 2026-02-06)
**Session type:** build
**Effort:** small-medium

---

## Context

Implement a hardware send system that routes generator audio from the intermediate bus to configurable MOTU M6 physical outputs (3-4 or 5-6). This reuses the existing telemetry tap point as a parallel consumer. The morph mapper can then characterize external hardware (filters, wavefolders, VCAs) using internal generators as known reference signals.

Read the spec first: `HARDWARE_SEND_SPEC.md`

---

## Implementation (4 files)

### 1. SuperCollider SynthDef + responders (`supercollider/core/telemetry_tap.scd`)

**SynthDef `forge_hardware_send`:**
- Args: `|slot=0, outPair=1, gainDB=0|`
- Read intermediate bus for slot: `In.ar(~intermediateBuses[slot], 2)`
- Compute output bus: `baseChan = 2 + ((outPair - 1) * 2)`
- Apply gain: `gainDB.dbamp` (optional: `.lag(0.05)` for smooth transitions)
- **Mandatory** safety limiter: `Limiter.ar(sig, 0.95, 0.01)`
- Output: `Out.ar(baseChan, sig)`
- Belt-and-braces: if `outPair < 1`, post warning and return silently (Python already blocks this, but defend in depth)

**OSC responders:**
- `/noise/telem/hw_send/enable [slot, outPair, gainDB]` — free existing synth for slot if any, spawn new `forge_hardware_send`, store in `~hardwareSendSynths[slot]`
- `/noise/telem/hw_send/disable [slot]` — free synth, set `~hardwareSendSynths[slot] = nil`

**Boot function:** `~bootHardwareSend` — register both OSC responders, initialize `~hardwareSendSynths` as 8-element nil array

### 2. SuperCollider init (`supercollider/core/init.scd`)

Call `~bootHardwareSend.value;` during startup (after `~bootTelemetryTap` is fine).

### 3. Python API (`src/audio/telemetry_controller.py`)

Add two methods to `TelemetryController`:

```python
def enable_hardware_send(self, slot: int, output_pair: int = 1, level_db: float = 0.0):
    """Route slot intermediate bus to physical outputs.
    
    Default 0.0 dB is transparent; -6.0 dB recommended for sensitive hardware profiling.
    """
    if not (0 <= slot < 8):
        raise ValueError(f"slot must be 0-7, got {slot}")
    if not isinstance(output_pair, int) or output_pair < 1:
        raise ValueError(f"output_pair must be int >= 1, got {output_pair}")
    if not (-40.0 <= level_db <= 6.0):
        raise ValueError(f"level_db must be -40 to +6, got {level_db}")
    
    self.sc_client.send_message("/noise/telem/hw_send/enable", [slot, output_pair, level_db])
    self.hardware_sends[slot] = {'output_pair': output_pair, 'level_db': level_db}

def disable_hardware_send(self, slot: int):
    """Disable hardware send for slot."""
    if slot in self.hardware_sends:
        self.sc_client.send_message("/noise/telem/hw_send/disable", [slot])
        del self.hardware_sends[slot]
```

Initialize `self.hardware_sends = {}` in `__init__`.

**P0 — Generator swap must disable hardware send:**
Find the code path where generators are swapped/loaded/unloaded for a slot. Add `self.disable_hardware_send(slot)` there. This is the single most important safety behavior — prevents lingering synths routing stale audio to hardware outputs.

### 4. OSC handler mapping (`src/audio/osc_bridge.py`)

Register the two OSC paths in `_map_handlers()`:
- `/noise/telem/hw_send/enable`
- `/noise/telem/hw_send/disable`

---

## Output pair mapping (normative)

| output_pair | Physical Outputs | SC base channel (0-based) |
|------------:|-----------------|--------------------------|
| 1 | 3–4 | 2 |
| 2 | 5–6 | 4 |

Formula: `baseChan = 2 + ((outPair - 1) * 2)`

`output_pair=0` is invalid (blocked by Python validation AND SC belt-and-braces).

---

## Verification (run these in order)

```python
# 1. Basic send
audio_controller.load_generator(slot=0, pack="core", gen="reference_sine")
audio_controller.set_frequency(slot=0, freq=440)
telem.enable_hardware_send(slot=0, output_pair=1, level_db=-6.0)
# CHECK: 440Hz tone on MOTU outputs 3-4, still in main mix

# 2. Disable
telem.disable_hardware_send(slot=0)
# CHECK: Gone from 3-4, still in main mix

# 3. Coexist with telemetry
telem.enable(slot=0, rate=15)
telem.enable_hardware_send(slot=0, output_pair=1)
# CHECK: Both working simultaneously

# 4. Multiple slots
telem.enable_hardware_send(slot=0, output_pair=1)  # Slot 0 → outputs 3-4
telem.enable_hardware_send(slot=1, output_pair=2)  # Slot 1 → outputs 5-6
# CHECK: Independent routing

# 5. P0: Generator swap disables hardware send
telem.enable_hardware_send(slot=0, output_pair=1)
audio_controller.load_generator(slot=0, pack="core", gen="bright_saw")
# CHECK: Hardware send on slot 0 is now disabled, outputs 3-4 silent
# This is the critical safety test.

# 6. Validation
telem.enable_hardware_send(slot=0, output_pair=0)  # Must raise ValueError
```

**Priority:** Test #5 is P0. If swap doesn't disable the send, ghost audio routes to hardware outputs indefinitely.

---

## Design decisions (locked — do not deviate)

- D1: Tap intermediate bus (pre-end-stage, zero coloration)
- D2: Allow summing if multiple sends target same outputs
- D3: Mandatory safety limiter always on
- D4: Block output_pair=0 (ValueError)
- D5: Hardware send disabled on generator swap (matches telemetry lifecycle)
- D6: Telemetry + hardware send coexist on same slot

---

## Scope boundaries

**Do not build:** UI controls, preset integration, return paths, pre/post tap selection, mono send, MorphMapper integration changes. Console-only.
