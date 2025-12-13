# Master Out - Design Document

**Status:** Planning  
**Created:** 2025-12-13

---

## Overview

The master output section handles final signal processing, metering, output routing, and recording. Designed for stereo now, with quadraphonic expansion in mind.

---

## Signal Flow

```
Generators → Mixer → Master Bus → Compression → EQ → Limiter → Output Assignment → Hardware
                                      ↓
                                  Recording
                                      ↓
                                   Metering
```

---

## Implementation Phases

### Phase 1: Fader + Meter
**Effort:** Low  
**Dependencies:** None

**Features:**
- Master fader (already exists in SC, needs proper UI)
- Level meter (L/R bars)
- Peak hold indicators
- Clip detection (red indicator, latches 1-2 sec)

**SC Requirements:**
```supercollider
// Send levels to Python ~20-30fps
SendReply.kr(Impulse.kr(24), '/master/levels', [ampL, ampR, peakL, peakR]);
```

**Python Requirements:**
- OSC listener for `/master/levels`
- Meter widget with peak hold
- Clip indicator with auto-reset

**Files:**
- `src/gui/master_section.py` (new)
- `supercollider/core/master.scd` (new or extend init.scd)

---

### Phase 2: Output Assignment
**Effort:** Medium  
**Dependencies:** Phase 1

**Features:**
- Output pair selector: 1-2, 3-4, 5-6 (depends on device)
- Multi-output mode: same stereo to multiple pairs simultaneously
- Query available outputs from current device

**UI:**
- Dropdown or toggle buttons for output pairs
- Checkboxes for multi-output mode

**SC Requirements:**
```supercollider
// Dynamic output assignment
Out.ar(~outputBusL, sigL);
Out.ar(~outputBusR, sigR);
```

**Config:**
```yaml
master:
  outputs:
    - pair: [0, 1]  # 1-2
      enabled: true
    - pair: [2, 3]  # 3-4
      enabled: false
```

---

### Phase 3: Device Selection
**Effort:** Medium  
**Dependencies:** Phase 2

**Features:**
- Dropdown showing available audio devices
- Aggregated devices supported (BlackHole + M6)
- Remember last selection
- Graceful handling of disconnected devices

**SC Requirements:**
```supercollider
ServerOptions.devices;  // List available
s.options.device = "MOTU M6";
s.reboot;  // Required after device change
```

**Python Requirements:**
- Query devices from SC on startup
- Store selection in config
- Handle device change (warn about SC restart)

**Config:**
```yaml
audio:
  device: "MOTU M6"
  sample_rate: 48000
  buffer_size: 256
```

**Known Devices (your setup):**
- MOTU M6
- BlackHole (virtual)
- Aggregate Device (M6 + BlackHole)
- MacBook Pro Speakers (built-in)

---

### Phase 4: Limiter
**Effort:** Low  
**Dependencies:** Phase 1

**Features:**
- Brickwall limiter (always on, safety)
- Ceiling control (-0.1dB default)
- Bypass option
- Gain reduction meter (optional)

**SC Requirements:**
```supercollider
// Simple limiter
sig = Limiter.ar(sig, ceiling, lookahead);
```

**Parameters:**
| Param | Default | Range | Unit |
|-------|---------|-------|------|
| ceiling | -0.1 | -6 to 0 | dB |
| lookahead | 0.01 | 0.001 to 0.1 | sec |
| enabled | true | bool | - |

---

### Phase 5: Compression
**Effort:** Medium  
**Dependencies:** Phase 4

**Features:**
- Stereo bus compressor
- Standard controls: threshold, ratio, attack, release, makeup
- Bypass option
- Gain reduction meter

**SC Requirements:**
```supercollider
// Stereo compression
sig = Compander.ar(sig, sig, 
    thresh: thresh,
    slopeBelow: 1,
    slopeAbove: 1/ratio,
    clampTime: attack,
    relaxTime: release
);
sig = sig * makeupGain;
```

**Parameters:**
| Param | Default | Range | Unit |
|-------|---------|-------|------|
| threshold | -12 | -40 to 0 | dB |
| ratio | 4 | 1 to 20 | :1 |
| attack | 10 | 0.1 to 100 | ms |
| release | 100 | 10 to 1000 | ms |
| makeup | 0 | 0 to 24 | dB |
| enabled | false | bool | - |

**UI:**
- Vertical sliders matching generator slot style
- GR meter (could be horizontal bar)

---

### Phase 6: 3-Band EQ
**Effort:** Medium  
**Dependencies:** Phase 5

**Features:**
- Low shelf (~200Hz)
- Mid bell (~1kHz)
- High shelf (~4kHz)
- Gain per band (-12 to +12 dB)
- Bypass option

**SC Requirements:**
```supercollider
// 3-band EQ
sig = BLowShelf.ar(sig, lowFreq, 1, lowGain);
sig = MidEQ.ar(sig, midFreq, 1, midGain);
sig = BHiShelf.ar(sig, highFreq, 1, highGain);
```

**Parameters:**
| Param | Default | Range | Unit |
|-------|---------|-------|------|
| lowFreq | 200 | 60 to 400 | Hz |
| lowGain | 0 | -12 to +12 | dB |
| midFreq | 1000 | 400 to 4000 | Hz |
| midGain | 0 | -12 to +12 | dB |
| highFreq | 4000 | 2000 to 12000 | Hz |
| highGain | 0 | -12 to +12 | dB |
| enabled | false | bool | - |

**UI Options:**
1. Simple: 3 vertical gain sliders, fixed frequencies
2. Advanced: Gain + frequency per band (6 controls)

Recommend starting simple.

---

### Phase 7: Recording
**Effort:** Medium-High  
**Dependencies:** Phase 1

**Features:**
- Record button (arm/disarm)
- File format selection (WAV 24-bit default)
- Auto-naming with timestamp
- Recording indicator (red dot, elapsed time)
- Stop creates file, ready for next recording

**SC Requirements:**
```supercollider
// Recording to disk
~recorder = DiskOut.ar(~recBuffer, sig);

// Start recording
~recBuffer = Buffer.alloc(s, 65536, 2);
~recBuffer.write(path, "wav", "int24", 0, 0, true);

// Stop recording
~recBuffer.close;
~recBuffer.free;
```

**Python Requirements:**
- Recording state management
- File path handling (`~/noise-engine-recordings/` default)
- Timer display
- OSC commands: `/master/record/start`, `/master/record/stop`

**Config:**
```yaml
recording:
  directory: "~/noise-engine-recordings"
  format: "wav"
  bit_depth: 24
  auto_increment: true
```

**File Naming:**
```
noise-engine_2025-12-13_143052.wav
noise-engine_2025-12-13_143052_02.wav  (if exists)
```

---

## Future: Quadraphonic

**Not in scope now, but keep in mind:**

- Output assignment already supports 4 outputs
- Would need: front L/R, rear L/R
- Mixer pan becomes 2D (or separate front/back control)
- Master processing needs 4-channel variants
- Recording would be 4-channel file

**Placeholder in config:**
```yaml
master:
  mode: "stereo"  # or "quad"
  outputs:
    front: [0, 1]
    rear: [2, 3]  # only used in quad mode
```

---

## UI Layout

```
┌─────────────────────────────────────────────────┐
│ MASTER OUT                                      │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌──────┐  │
│  │ EQ  │  │COMP │  │ LIM │  │ OUT │  │METER │  │
│  │     │  │     │  │     │  │     │  │ L  R │  │
│  │ L   │  │ THR │  │ CEL │  │ 1-2 │  │ █  █ │  │
│  │ M   │  │ RAT │  │     │  │ 3-4 │  │ █  █ │  │
│  │ H   │  │ ATK │  │     │  │     │  │ █  █ │  │
│  │     │  │ REL │  │     │  │     │  │ █  █ │  │
│  │[byp]│  │[byp]│  │[byp]│  │     │  │      │  │
│  └─────┘  └─────┘  └─────┘  └─────┘  └──────┘  │
│                                                 │
│  ┌─────────────────────┐  ┌─────────────────┐  │
│  │ 🔴 REC  00:00:00    │  │ DEVICE ▼ MOTU   │  │
│  └─────────────────────┘  └─────────────────┘  │
│                                                 │
│  ┌─────────────────────────────────────────┐   │
│  │               MASTER FADER              │   │
│  └─────────────────────────────────────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Dependencies & Order

```
Phase 1 (Fader + Meter)
    ↓
Phase 2 (Output Assignment) ←── Phase 3 (Device Selection)
    ↓
Phase 4 (Limiter)
    ↓
Phase 5 (Compression)
    ↓
Phase 6 (3-Band EQ)

Phase 7 (Recording) ←── can start after Phase 1
```

---

## Files to Create/Modify

**New Files:**
- `src/gui/master_section.py` - Master out UI component
- `src/gui/meter_widget.py` - Reusable level meter
- `supercollider/core/master.scd` - Master bus processing

**Modify:**
- `src/gui/main_frame.py` - Add master section to layout
- `src/config/__init__.py` - Add master out config/OSC paths
- `supercollider/init.scd` - Load master.scd

---

## Open Questions

1. **Master section placement** - Right panel below mixer? Or dedicated bottom-right area?
2. **EQ visualization** - Simple gain readout or frequency curve display?
3. **Compression style** - Transparent (SSL-style) or colored (distressor-style)?
4. **Recording format** - Just WAV or also FLAC/AIFF options?

---

## References

- SC Limiter: https://doc.sccode.org/Classes/Limiter.html
- SC Compander: https://doc.sccode.org/Classes/Compander.html
- SC DiskOut: https://doc.sccode.org/Classes/DiskOut.html
