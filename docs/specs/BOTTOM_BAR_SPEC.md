# Bottom Bar Specification

**Status:** Draft
**Version:** 1.0
**Date:** 2026-01-26
**Supersedes:** UI_REFRESH_SPEC.md (bottom bar sections), UI_CONSISTENCY_HOTFIX_SPEC.md (HF-3)

---

## Overview

This spec defines the bottom bar architecture: 4 FX send slots on the left, unified Master section on the right. Consolidates and clarifies the planned architecture from UI_REFRESH_SPEC with current implementation state.

---

## Current State

### What's Working (More Than Expected!)

**SuperCollider - COMPLETE:**
- ✅ `fx1-4 send/return buses` in buses.scd
- ✅ `channel_strips.scd` has all 4 FX sends (fx1Send-fx4Send)
- ✅ `fx_slots.scd` - slot manager with hot-swap support
- ✅ `fx_echo.scd`, `fx_reverb.scd`, `fx_chorus.scd`, `fx_lofi.scd`, `fx_empty.scd`
- ✅ OSC handlers for `/noise/fx/slot/N/type`, `/noise/fx/slot/N/p1`, etc.
- ✅ Bus unification support for boid modulation of p1-p4

**GUI - Partially Complete:**
- ✅ `FXGrid` with `fx_slot_1` through `fx_slot_4`
- ✅ Channel strips have `chan_N_fx1` through `chan_N_fx4` (4 send knobs)
- ✅ FX slots have p1-p4 sliders + return

### What's Broken

The bottom bar shows **two overlapping systems**:

```
fxContainer (600x180)
├── fx_grid (FXGrid)      → fx_slot_1-4  [NEW - working]
└── InlineFXStrip         → Heat, Echo, Reverb, Filter modules  [OLD - should be removed]
```

**Actual Problems:**
1. **Old `InlineFXStrip` still visible** alongside new `FXGrid` (visual clutter)
2. **Heat/Filter in wrong location** (should be master inserts, not FX strip)
3. **No unified `master_chain.py`** (Heat + Filter + EQ + Comp + Output)
4. **Old Echo/Reverb modules redundant** (new FX slots handle these)

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

**Note:** SC foundation is COMPLETE. Only GUI cleanup remains.

### Phase 1: Hide Old FX Strip (Quick Win)

1. **Comment out `InlineFXStrip`** creation in main_frame.py
2. **Verify FXGrid works alone** - should show 4 clean FX slots
3. **Test:** FX slots should still control SC effects

### Phase 2: Create Master Chain Widget

1. **New file:** `src/gui/master_chain.py`
2. **Move Heat controls** from InlineFXStrip → MasterChain
3. **Move Filter controls** from InlineFXStrip → MasterChain
4. **Integrate existing:** EQ, Compressor, Limiter, Output from master_section.py
5. **Flat layout** matching generator_slot_new.py pattern

### Phase 3: Integration & Cleanup

1. **Update main_frame.py** bottom bar layout (FXGrid left, MasterChain right)
2. **Delete deprecated:** inline_fx_strip.py (after Heat/Filter migrated)
3. **Delete deprecated:** master_section.py (after absorbed into master_chain.py)
4. **Preset schema updates** (if any widget names changed)

### NO LONGER NEEDED (Already Done):

- ~~Add FX3, FX4 send knobs~~ → Already have `chan_N_fx1-4`
- ~~Add fx3/fx4 buses~~ → Already in buses.scd
- ~~Create FX slot manager~~ → Already in fx_slots.scd
- ~~Implement Chorus, LoFi~~ → Already have fx_chorus.scd, fx_lofi.scd

---

## File Changes

### Create
| File | Purpose |
|------|---------|
| `src/gui/master_chain.py` | Unified master section (Heat + Filter + EQ + Comp + Output) |

### Modify
| File | Changes |
|------|---------|
| `src/gui/main_frame.py` | Remove InlineFXStrip, add MasterChain |

### Deprecate (after migration)
| File | Replacement |
|------|-------------|
| `src/gui/inline_fx_strip.py` | master_chain.py (Heat/Filter only) |
| `src/gui/master_section.py` | master_chain.py |

### Already Complete (no changes needed)
| File | Status |
|------|--------|
| `src/gui/fx_grid.py` | ✅ Working |
| `src/gui/fx_slot.py` | ✅ Working |
| `src/gui/mixer_panel.py` | ✅ Has 4 FX sends |
| `supercollider/core/buses.scd` | ✅ Has fx1-4 buses |
| `supercollider/core/channel_strips.scd` | ✅ Has fx1-4 sends |
| `supercollider/core/fx_slots.scd` | ✅ Slot manager complete |
| `supercollider/effects/fx_*.scd` | ✅ echo, reverb, chorus, lofi, empty |

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
