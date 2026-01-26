# Bottom Bar Specification

**Status:** Draft
**Version:** 1.0
**Date:** 2026-01-26
**Supersedes:** UI_REFRESH_SPEC.md (bottom bar sections), UI_CONSISTENCY_HOTFIX_SPEC.md (HF-3)

---

## Overview

This spec defines the bottom bar architecture: 4 FX send slots on the left, unified Master section on the right. Consolidates and clarifies the planned architecture from UI_REFRESH_SPEC with current implementation state.

---

## Current State (Broken)

The bottom bar currently shows **two overlapping systems**:

```
fxContainer (600x180)
├── fx_grid (FXGrid)      → fx_slot_1, fx_slot_2, fx_slot_3, fx_slot_4  [NEW]
└── InlineFXStrip         → HeatModule, EchoModule, ReverbModule, FilterModule  [OLD]
```

**Problems:**
1. Both old and new FX systems visible simultaneously
2. Heat/Filter are in FX strip but should be master inserts
3. Echo/Reverb exist as both old modules AND new slot types
4. Only 2 FX sends from channel strips (need 4)
5. Master section separate from Heat/Filter

---

## Target Architecture

### Signal Flow

```
CHANNEL STRIPS (1-8)
  │
  ├──► FX1 Send ──► ~fx1SendBus ──► FX SLOT 1 [selectable] ──► ~fx1ReturnBus ──┐
  ├──► FX2 Send ──► ~fx2SendBus ──► FX SLOT 2 [selectable] ──► ~fx2ReturnBus ──┼──► masterBus
  ├──► FX3 Send ──► ~fx3SendBus ──► FX SLOT 3 [selectable] ──► ~fx3ReturnBus ──┤
  ├──► FX4 Send ──► ~fx4SendBus ──► FX SLOT 4 [selectable] ──► ~fx4ReturnBus ──┘
  │
  └──► masterBus (dry)
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         MASTER CHAIN                                │
│                                                                     │
│  masterBus + FX Returns                                             │
│         │                                                           │
│         ▼                                                           │
│      HEAT (saturation insert, ReplaceOut)                          │
│         │                                                           │
│         ▼                                                           │
│      FILTER (dual filter insert)                                    │
│         │                                                           │
│         ▼                                                           │
│      EQ (3-band master isolator)                                    │
│         │                                                           │
│         ▼                                                           │
│      COMPRESSOR (SSL G-style)                                       │
│         │                                                           │
│         ▼                                                           │
│      LIMITER (brickwall)                                            │
│         │                                                           │
│         ▼                                                           │
│      OUTPUT (master fader + meters)                                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Bottom Bar Layout

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ BOTTOM BAR (180px height, full width ~1512px)                                  │
├────────────────────────────────────────────────┬───────────────────────────────┤
│          FX SENDS (~640px)                     │      MASTER SECTION (~870px)  │
├──────────┬──────────┬──────────┬──────────┬────┼───────────────────────────────┤
│ FX SLOT 1│ FX SLOT 2│ FX SLOT 3│ FX SLOT 4│    │ HEAT │ FILT │ EQ │COMP│ OUT  │
│  160px   │  160px   │  160px   │  160px   │gap │ 80px │120px │100px│120px│~250px│
│          │          │          │          │    │      │      │    │    │      │
│ [type ▼] │ [type ▼] │ [type ▼] │ [type ▼] │    │insert│insert│    │    │fader │
│ p1 p2 p3 │ p1 p2 p3 │ p1 p2 p3 │ p1 p2 p3 │    │      │      │    │    │meters│
│ p4  rtn  │ p4  rtn  │ p4  rtn  │ p4  rtn  │    │[byp] │[byp] │    │[byp]│      │
│ [bypass] │ [bypass] │ [bypass] │ [bypass] │    │      │      │    │    │      │
└──────────┴──────────┴──────────┴──────────┴────┴──────┴──────┴────┴────┴──────┘
```

---

## Component Specifications

### 1. FX Slots (Send Effects)

Each of the 4 slots can load any available FX type. All are **send effects** - fed by channel strip sends, returning to master bus.

#### FX Slot Widget

```
┌─────────────────────────────────┐
│ FX1 [Echo              ▼]      │  ← Type selector dropdown
├─────────────────────────────────┤
│ ┌──┐ ┌──┐ ┌──┐ ┌──┐    ┌──┐   │
│ │p1│ │p2│ │p3│ │p4│    │RT│   │  ← 4 params + return level
│ │  │ │  │ │  │ │  │    │  │   │
│ └──┘ └──┘ └──┘ └──┘    └──┘   │
│ TIME  FBK  WOW TONE    RTN    │  ← Labels (vary by type)
├─────────────────────────────────┤
│ [BYP]              [T1] [T2]  │  ← Bypass + Turbo buttons
└─────────────────────────────────┘
        160px × 150px
```

**Dimensions:**
- Slot: 160px × 150px (fixed)
- Param sliders: 18px × 80px
- Return slider: 18px × 80px
- Type selector: 120px × 22px

#### Available FX Types

**Priority 1 (Ship with 4-slot system):**
| Type | Description | p1 | p2 | p3 | p4 |
|------|-------------|----|----|----|----|
| Empty | Pass-through | - | - | - | - |
| Echo | Tape delay | Time | Feedback | Wow | Tone |
| Reverb | Plate/Room | Size | Decay | Tone | Damping |
| Chorus | Stereo ensemble | Rate | Depth | Mix | Voices |
| LoFi | Bitcrush/downsample | Rate | Bits | Noise | Filter |

**Priority 2 (Essential):**
| Type | p1 | p2 | p3 | p4 |
|------|----|----|----|----|
| Phaser | Rate | Depth | Feedback | Stages |
| Flanger | Rate | Depth | Feedback | Manual |
| Tremolo | Rate | Depth | Shape | Stereo |

**Priority 3 (Creative):**
| Type | p1 | p2 | p3 | p4 |
|------|----|----|----|----|
| Ring Mod | Freq | Mix | LFO Rate | LFO Depth |
| Grain | Size | Pitch | Density | Spread |
| Shimmer | Size | Shift | Mix | Decay |

**Default Slot Assignment:**
- Slot 1: Echo
- Slot 2: Reverb
- Slot 3: Chorus
- Slot 4: LoFi

---

### 2. Master Section

Heat and Filter move here as **fixed inserts** (not selectable). Followed by EQ, Compressor, and Output.

#### Master Section Layout

```
┌─────┬───────────┬───────┬─────────┬──────────────────────┐
│HEAT │  FILTER   │  EQ   │  COMP   │       OUTPUT         │
│     │           │       │         │                      │
│ ┌─┐ │ ┌─┐ ┌─┐   │┌─┐┌─┐ │ ┌─┐┌─┐  │  ┌────┐             │
│ │D│ │ │F│ │F│   ││L││M│ │ │T││M│  │  │    │  ┌─┐  ┌─┐   │
│ │R│ │ │1│ │2│   ││O││D│ │ │H││K│  │  │ V  │  │▓│  │▓│   │
│ └─┘ │ └─┘ └─┘   │└─┘└─┘ │ └─┘└─┘  │  │ O  │  │▓│  │▓│   │
│ ┌─┐ │ ┌─┐ ┌─┐   │┌─┐┌─┐ │ ┌─┐┌─┐  │  │ L  │  │▓│  │▓│   │
│ │M│ │ │R│ │R│   ││H││L│ │ │A││R│  │  │    │  │▓│  │▓│   │
│ │X│ │ │1│ │2│   ││I││C│ │ │T││L│  │  └────┘  └─┘  └─┘   │
│ └─┘ │ └─┘ └─┘   │└─┘└─┘ │ └─┘└─┘  │  [LIM]   L    R     │
│     │           │       │         │                      │
│[CIR]│[LP1][HP1] │       │  [GR]   │  ceiling            │
│[BYP]│[LP2][HP2] │       │  [BYP]  │  ┌─┐                │
│     │[SER][PAR] │       │         │  └─┘                │
│     │[BYP]      │       │         │                      │
├─────┼───────────┼───────┼─────────┼──────────────────────┤
│80px │   120px   │ 100px │  120px  │       ~250px         │
└─────┴───────────┴───────┴─────────┴──────────────────────┘
```

#### Heat Module (Master Insert)

**Function:** Saturation/warmth on master bus
**Signal:** Insert (ReplaceOut on masterBus)

| Control | Type | Range | Default |
|---------|------|-------|---------|
| Drive | Slider | 0-1 | 0.3 |
| Mix | Slider | 0-1 | 0.5 |
| Circuit | Cycle | Tape/Tube/Transistor | Tape |
| Bypass | Toggle | on/off | off |

#### Filter Module (Master Insert)

**Function:** Dual resonant filter on master bus
**Signal:** Insert (ReplaceOut on masterBus, after Heat)

| Control | Type | Range | Default |
|---------|------|-------|---------|
| Freq 1 | Slider | 20Hz-20kHz | 1000Hz |
| Reso 1 | Slider | 0-1 | 0.3 |
| Freq 2 | Slider | 20Hz-20kHz | 5000Hz |
| Reso 2 | Slider | 0-1 | 0.3 |
| Mode 1 | Toggle | LP/HP | LP |
| Mode 2 | Toggle | LP/HP | HP |
| Routing | Toggle | Serial/Parallel | Serial |
| Sync 1 | Toggle | on/off | off |
| Sync 2 | Toggle | on/off | off |
| Bypass | Toggle | on/off | off |

#### EQ Module

| Control | Type |
|---------|------|
| LO | Slider (±12dB) |
| MID | Slider (±12dB) |
| HI | Slider (±12dB) |
| LO CUT | Slider (off-150Hz) |

#### Compressor Module

| Control | Type | Range |
|---------|------|-------|
| Threshold | Slider | -40 to 0 dB |
| Makeup | Slider | 0 to +20 dB |
| Attack | Slider | 0.1-100ms |
| Release | Slider | 50-1000ms |
| Ratio | Cycle | 2:1, 4:1, 8:1, 20:1 |
| Bypass | Toggle | on/off |
| GR Meter | Display | 0 to -20dB |

#### Output Module

| Control | Type |
|---------|------|
| Limiter Ceiling | Slider (-6 to 0 dB) |
| Master Fader | Slider (0-1) |
| L Meter | VU display |
| R Meter | VU display |

---

## Implementation Plan

### Phase 1: Clean Up Current State

1. **Hide old InlineFXStrip** (don't delete yet - keep for reference)
2. **Verify FXGrid (fx_slot_1-4) works** standalone
3. **Document what's missing** from FX slots

### Phase 2: Create Master Chain Widget

1. **New file:** `src/gui/master_chain.py`
2. **Migrate Heat** from InlineFXStrip → MasterChain
3. **Migrate Filter** from InlineFXStrip → MasterChain
4. **Integrate existing:** EQ, Compressor, Limiter, Output from master_section.py
5. **Flat layout** matching generator_slot_new.py pattern

### Phase 3: Channel Strip Updates

1. **Add FX3, FX4 send knobs** to mixer_panel.py
2. **Update channel strip SynthDef** with fx3Send, fx4Send
3. **Wire OSC handlers**

### Phase 4: SC FX Slot System

1. **Add buses:** fx3SendBus, fx4SendBus, fx3ReturnBus, fx4ReturnBus
2. **Create FX slot manager** for swapping synth types
3. **Implement new FX types:** Chorus, LoFi, Phaser, etc.

### Phase 5: Integration

1. **Update main_frame.py** bottom bar layout
2. **Remove deprecated files:** inline_fx_strip.py, old master_section.py
3. **Preset schema updates**
4. **Bus unification metadata**

---

## File Changes

### Create
| File | Purpose |
|------|---------|
| `src/gui/master_chain.py` | Unified master section widget |
| `supercollider/effects/chorus.scd` | Chorus SynthDef |
| `supercollider/effects/lofi.scd` | LoFi SynthDef |
| `supercollider/effects/phaser.scd` | Phaser SynthDef |
| `supercollider/effects/fx_slot_manager.scd` | Slot swapping logic |

### Modify
| File | Changes |
|------|---------|
| `src/gui/main_frame.py` | New bottom bar layout |
| `src/gui/mixer_panel.py` | Add FX3, FX4 send knobs |
| `supercollider/core/buses.scd` | Add fx3/fx4 buses |
| `supercollider/core/channel_strips.scd` | Add fx3Send, fx4Send |
| `src/config/__init__.py` | FX types list, new OSC paths |

### Deprecate
| File | Replacement |
|------|-------------|
| `src/gui/inline_fx_strip.py` | fx_grid.py + master_chain.py |
| `src/gui/master_section.py` | master_chain.py |

---

## ObjectName Conventions

```python
# FX Slots (send effects)
"fx_slot_1", "fx_slot_2", "fx_slot_3", "fx_slot_4"
"fx_slot1_p1", "fx_slot1_p2", "fx_slot1_p3", "fx_slot1_p4"
"fx_slot1_return", "fx_slot1_bypass"

# Master Chain (inserts + processing)
"master_heat_drive", "master_heat_mix", "master_heat_bypass"
"master_filt_freq1", "master_filt_reso1", "master_filt_freq2", "master_filt_reso2"
"master_filt_bypass"
"master_eq_lo", "master_eq_mid", "master_eq_hi", "master_eq_locut"
"master_comp_threshold", "master_comp_makeup", "master_comp_attack"
"master_comp_release", "master_comp_ratio", "master_comp_bypass"
"master_limiter_ceiling"
"master_fader"
```

---

## Verification

After implementation, F4 dump should show:

```json
{
  "hotfix_status": {
    "HF3_fx_widths": {},  // Old modules removed
    "bottom_bar_correct": true
  },
  "widgets": {
    "fx_slot_1": {"w": 160, "h": 150},
    "fx_slot_2": {"w": 160, "h": 150},
    "fx_slot_3": {"w": 160, "h": 150},
    "fx_slot_4": {"w": 160, "h": 150},
    "master_heat_drive": {"visible": true},
    "master_filt_freq1": {"visible": true},
    "master_fader": {"visible": true}
  }
}
```

No `HeatModule`, `EchoModule`, `ReverbModule`, `FilterModule` should appear.

---

## Open Questions

1. **Turbo buttons on FX slots** - Keep T1/T2 or simplify?
2. **Filter sync controls** - Inline or popup?
3. **Compressor ratio** - Knob or cycle button?
4. **Default FX slot types** - Echo/Reverb/Chorus/LoFi or user preference?

---

## Related Docs

- `UI_REFRESH_SPEC.md` - Original full UI refresh plan
- `DECISIONS.md` - Heat as master effect rationale
- `BUS_UNIFICATION_PLAN.md` - Unified key system for boid modulation
