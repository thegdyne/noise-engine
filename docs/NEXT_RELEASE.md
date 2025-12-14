# Next Release - Deferred Features

**Version:** 2.0 (Future)  
**Created:** 2025-12-14

---

## Overview

These features are complete in design but deferred to a future release to stabilize the current master section implementation.

---

## Deferred from Master Section

### Phase 2: Output Assignment

**Status:** Designed, not implemented  
**Priority:** Medium  
**Complexity:** Medium

**Features:**
- Output pair selector: 1-2, 3-4, 5-6 (device-dependent)
- Multi-output mode: route stereo to multiple pairs simultaneously
- Query available outputs from current audio device

**UI Concept:**
```
┌─────────────────────┐
│ OUTPUT              │
│ [1-2] [3-4] [5-6]  │  ← Toggle buttons
│ ☑ Multi-out        │  ← Checkbox for simultaneous
└─────────────────────┘
```

**SC Requirements:**
```supercollider
// Dynamic output assignment
Out.ar(~outputBusL, sigL);
Out.ar(~outputBusR, sigR);

// Multi-output
~outputPairs.do { |pair|
    Out.ar(pair[0], sigL);
    Out.ar(pair[1], sigR);
};
```

**Dependencies:**
- Requires querying device output count
- May need SC reboot on change (like device selection)

**Use Cases:**
- Send to headphones (1-2) and monitors (3-4) simultaneously
- Route to different speaker sets for A/B comparison
- Feed recording interface on separate outputs

---

### Phase 7: Recording

**Status:** Designed, not implemented  
**Priority:** Medium-High  
**Complexity:** Medium-High

**Features:**
- Record button (arm/disarm)
- File format: WAV 24-bit (default), optional FLAC/AIFF
- Auto-naming with timestamp
- Recording indicator (red dot, elapsed time)
- Stop creates file, ready for next recording
- Configurable output directory

**UI Concept:**
```
┌─────────────────────────────────────┐
│ 🔴 REC  00:03:42    [STOP]         │
│ noise-engine_2025-12-14_143052.wav │
└─────────────────────────────────────┘
```

**SC Requirements:**
```supercollider
// Start recording
~recBuffer = Buffer.alloc(s, 65536, 2);
~recBuffer.write(path, "wav", "int24", 0, 0, true);
~recorder = DiskOut.ar(~recBuffer, sig);

// Stop recording
~recBuffer.close;
~recBuffer.free;
```

**Python Requirements:**
- Recording state machine (idle → armed → recording → saving)
- File path management
- Timer display (elapsed time)
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
noise-engine_2025-12-14_143052.wav
noise-engine_2025-12-14_143052_02.wav  (if exists)
```

**Considerations:**
- Recording tap point: post-limiter (final output)
- Buffer size affects latency and disk write frequency
- Need graceful handling of disk full / write errors
- Consider pre-roll option (capture N seconds before record hit)

---

## Other Future Features

### Presets System

**Status:** Concept only  
**Priority:** High  
**Complexity:** High

**Requirements:**
- Parameter ID system for all controllable values
- Central ParameterRegistry
- Save/load to JSON
- Preset browser UI

**Blocked by:** Need to add parameter IDs to all sliders first

**See conversation notes:** Parameter ID discussion (parked)

---

### MIDI Learn

**Status:** Concept only  
**Priority:** High  
**Complexity:** High

**Requirements:**
- MIDI CC mapping to parameters
- Learn mode (click param, move CC)
- Save/load mappings
- Visual feedback during learn

**Blocked by:** Need parameter ID system first

**See conversation notes:** Parameter ID discussion (parked)

---

### Thrust Modes (Compressor Enhancement)

**Status:** Designed, not implemented  
**Priority:** Low  
**Complexity:** Low

**Features:**
- Extend SC HPF to weighted sidechain curves
- ThrustM: Mid-focused weighting
- ThrustL: Low-cut plus mid emphasis

**Implementation:**
```supercollider
// SC_MODE = Off | HPF | ThrustM | ThrustL
scSig = Select.ar(scMode, [
    sig,                              // Off
    HPF.ar(sig, scHpfFreq),          // HPF
    // ThrustM/L curves here
]);
```

---

### Compressor Mix Control

**Status:** Concept only  
**Priority:** Low  
**Complexity:** Low

**Features:**
- Wet/dry blend for parallel compression
- 100% = full compression
- 50% = parallel (NY) compression

**Implementation:**
```supercollider
sig = (sigComp * mix) + (sigDry * (1 - mix));
```

---

## Version Planning

### v1.x (Current)
- ✅ Master fader + meter
- ✅ PRE/POST toggle
- ✅ Device display
- ✅ Limiter
- ✅ Compressor (SSL-style)
- ✅ EQ (DJ isolator)
- ✅ ValuePopup on all sliders

### v2.0 (Next)
- ⬜ Output assignment
- ⬜ Recording
- ⬜ Presets system
- ⬜ MIDI learn

### v2.x (Future)
- ⬜ Thrust modes
- ⬜ Compressor mix
- ⬜ Quadraphonic support

---

## Notes

When starting v2.0 development:

1. **Parameter IDs first** - Add unique IDs to all sliders before presets/MIDI
2. **Output assignment** - Simpler than recording, good warmup
3. **Recording** - Most user-requested feature, do after output assignment
4. **Presets** - Requires parameter registry, significant architecture
5. **MIDI learn** - Builds on presets infrastructure
