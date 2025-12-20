# Master Out - Design Document

**Status:** Phase 5 & 6 Complete, Phase 2 & 7 Remaining  
**Created:** 2025-12-13  
**Updated:** 2025-12-14

---

## Overview

The master output section handles final signal processing, metering, output routing, and recording. Designed for stereo now, with quadraphonic expansion in mind.

---

## Signal Flow

```
Generators → Mixer → Master Bus → PRE Meter → EQ → Compressor → Limiter → Master Vol → POST Meter → Output
                                                        ↓
                                                   GR Meter
```

---

## Phase Summary

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 1 | Fader + Meter | ✅ Complete | Master fader, stereo level meter, peak hold, clip detection |
| 1.5 | PRE/POST Toggle | ✅ Complete | Meter mode switch (pre-fader vs post-fader) |
| 2 | Output Assignment | ⬜ Not started | Route to different output pairs (1-2, 3-4, etc) |
| 3 | Device Display | ✅ Complete | Shows current audio device (display-only, no switching) |
| 4 | Limiter | ✅ Complete | Brickwall limiter with ceiling control and bypass |
| 5 | Compressor | ✅ Complete | SSL G-style bus compressor with GR meter |
| 6 | Master EQ | ✅ Complete | DJ-style 3-band isolator with kill buttons |
| 7 | Recording | ⬜ Not started | Record to disk with file management |

---

## Phase Details

### Phase 1: Fader + Meter ✅ COMPLETE

**Features:**
- Master fader with dB display
- Stereo level meter (L/R bars)
- Peak hold indicators (1.5s hold, decay after)
- Clip detection (red indicator, 2s latch)
- ValuePopup on drag showing dB value

**Files:**
- `src/gui/master_section.py`
- `supercollider/core/master.scd`
- `supercollider/effects/master_passthrough.scd`

---

### Phase 1.5: PRE/POST Toggle ✅ COMPLETE

**Features:**
- Toggle button switches meter between PRE and POST fader
- PRE shows sum from channel strips before processing
- POST shows actual output level after all processing

**OSC:**
- `/noise/master/meter/toggle` - 0=PRE, 1=POST

---

### Phase 2: Output Assignment ⬜ NOT STARTED

**Features:**
- Output pair selector: 1-2, 3-4, 5-6 (depends on device)
- Multi-output mode: same stereo to multiple pairs simultaneously
- Query available outputs from current device

**UI:**
- Dropdown or toggle buttons for output pairs
- Checkboxes for multi-output mode

---

### Phase 3: Device Display ✅ COMPLETE

**Features:**
- Label showing current audio device name
- Display-only (no switching - SC reboot too fragile)
- Queries device list on connect for future use

**Decision:** Device switching disabled because SC reboot causes audio dropouts and sync issues. Showing current device is informational only.

---

### Phase 4: Limiter ✅ COMPLETE

**Features:**
- Brickwall limiter (safety/protection)
- Ceiling control: -6dB to 0dB (default -0.1dB)
- Bypass toggle
- 10ms lookahead

**See:** `docs/MASTER_LIMITER.md` for full specification

---

### Phase 5: Compressor ✅ COMPLETE

**Features:**
- SSL G-Series style bus compressor
- Stepped controls: ratio, attack, release
- Sidechain HPF with true bypass
- Dominant stereo detection
- Auto-release mode
- Real-time GR meter

**See:** `docs/MASTER_COMPRESSOR.md` for full specification

---

### Phase 6: Master EQ ✅ COMPLETE

**Features:**
- DJ-style 3-band isolator (not traditional EQ)
- Full kill capability per band
- Kill buttons for instant mute
- LO CUT rumble filter
- Phase-coherent LR4 crossovers

**See:** `docs/MASTER_EQ.md` for full specification

---

### Phase 7: Recording ⬜ NOT STARTED

**Features:**
- Record button (arm/disarm)
- File format selection (WAV 24-bit default)
- Auto-naming with timestamp
- Recording indicator (red dot, elapsed time)
- Stop creates file, ready for next recording

**SC Requirements:**
```supercollider
~recorder = DiskOut.ar(~recBuffer, sig);
~recBuffer = Buffer.alloc(s, 65536, 2);
~recBuffer.write(path, "wav", "int24", 0, 0, true);
```

**File Naming:**
```
noise-engine_2025-12-14_143052.wav
noise-engine_2025-12-14_143052_02.wav  (if exists)
```

---

## UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ MASTER OUT                                                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────┐  ┌───────────────────┐  ┌─────┐  ┌──────┐  ┌────────┐ │
│  │ VOL │  │        EQ         │  │ LIM │  │METER │  │  PEAK  │ │
│  │  █  │  │  LO   MID   HI    │  │ ON  │  │ L  R │  │  -2.1  │ │
│  │  █  │  │   █     █     █   │  │     │  │ █  █ │  │        │ │
│  │  █  │  │  [LO] [MID] [HI]  │  │  █  │  │ █  █ │  │ [PRE]  │ │
│  │  █  │  │  [CUT]     [BYP]  │  │     │  │ █  █ │  │        │ │
│  │-2dB │  └───────────────────┘  │-0.1 │  │ █  █ │  │ [CLIP] │ │
│  └─────┘                         └─────┘  └──────┘  └────────┘ │
├─────────────────────────────────────────────────────────────────┤
│ COMP  [ON]                                         GR ████░░░░ │
│ THR   RAT    ATK    REL    MKP    SC                           │
│  █   [4:1]  [10]  [Auto]   █    [OFF]                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Files

**Python:**
- `src/gui/master_section.py` - Master section UI component
- `src/gui/main_frame.py` - Signal connections
- `src/audio/osc_bridge.py` - OSC handling
- `src/config/__init__.py` - OSC paths

**SuperCollider:**
- `supercollider/effects/master_passthrough.scd` - All processing (EQ, comp, limiter)
- `supercollider/core/master.scd` - Volume OSC handler

---

## Future: Quadraphonic

**Not in scope now, but architecture supports:**
- Output assignment already designed for 4+ outputs
- Would need: front L/R, rear L/R
- Mixer pan becomes 2D
- Master processing needs 4-channel variants

---

## Related Documents

- `docs/MASTER_EQ.md` - DJ isolator specification
- `docs/MASTER_COMPRESSOR.md` - SSL compressor specification  
- `docs/MASTER_LIMITER.md` - Limiter specification
- `docs/DECISIONS.md` - Design decisions log
