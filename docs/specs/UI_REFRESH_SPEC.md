# Noise Engine UI Refresh Specification

## Overview

This specification outlines a systematic UI refresh to bring the FX, Mixer, Master, and Boids sections up to the same flat, slot-based visual standard as the Generator and Modulator grids.

---

## Current FX Signal Flow (IMPORTANT CONTEXT)

Before redesigning the UI, we need to understand the actual SuperCollider routing:

### Signal Chain

```
GENERATORS (1-8)
      â”‚
      â–¼
CHANNEL STRIPS (per-gen, in ~stripGroup)
  â”œâ”€â”€ EQ (3-band isolator)
  â”œâ”€â”€ Mute/Solo logic
  â”œâ”€â”€ Gain stage (+0/+6/+12dB)
  â”œâ”€â”€ Pan
  â”œâ”€â”€ Volume fader
  â”‚
  â”œâ”€â”€â–º [POST-FADER] Echo Send â”€â”€â–º ~echoSendBus â”€â”€â–º TAPE ECHO â”€â”€â–º ~echoReturnBus
  â”‚                                                    â”‚
  â”‚                                                    â”œâ”€â”€â–º verbSend (cross-feed to reverb)
  â”‚
  â”œâ”€â”€â–º [POST-FADER] Verb Send â”€â”€â–º ~verbSendBus â”€â”€â–º REVERB â”€â”€â–º ~verbReturnBus
  â”‚
  â””â”€â”€â–º ~masterBus (dry signal)
             â”‚
             â–¼
      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
      â”‚                    MASTER GROUP                          â”‚
      â”‚  (order determined by synth creation, ~masterGroup)      â”‚
      â”‚                                                          â”‚
      â”‚  1. HEAT (insert on masterBus, ReplaceOut)              â”‚
      â”‚       â””â”€â–º inBus: masterBus, outBus: masterBus           â”‚
      â”‚                                                          â”‚
      â”‚  2. DUAL FILTER (insert after Heat)                     â”‚
      â”‚       â””â”€â–º inBus: masterBus, outBus: masterBus           â”‚
      â”‚                                                          â”‚
      â”‚  3. MASTER PASSTHROUGH (last in chain)                  â”‚
      â”‚       â”œâ”€â–º Reads: masterBus + echoReturnBus + verbReturnBusâ”‚
      â”‚       â”œâ”€â–º EQ (master isolator)                          â”‚
      â”‚       â”œâ”€â–º LO CUT (75Hz HPF)                             â”‚
      â”‚       â”œâ”€â–º COMPRESSOR (SSL G-style)                      â”‚
      â”‚       â”œâ”€â–º LIMITER (brickwall)                           â”‚
      â”‚       â”œâ”€â–º Master Volume                                 â”‚
      â”‚       â””â”€â–º OUT to hardware                               â”‚
      â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### Key Architectural Points

1. **Echo & Reverb are SEND effects** - controlled per-channel from the mixer strips
2. **Heat & Dual Filter are INSERT effects** - permanently in master chain, use bypass
3. **No slot-based FX routing currently** - effects are hard-wired by synth creation order
4. **Channel sends are POST-fader** - send amounts modulated by boids via bus unification

### UI Implications

The current FX architecture means a "slot-based FX system" would require significant SC changes. For the UI refresh, we have two options:

**Option A: Visual Refresh Only** (Recommended for Phase 1)
- Reorganize existing FX controls into cleaner layout
- Keep Heat, Dual Filter, Echo, Reverb as fixed modules
- Match visual style to generators/modulators

**Option B: Full FX Slot System** (Future Phase)
- Redesign SC routing for flexible FX slots
- Insert vs Send selection per slot
- Would require bus rewiring and synth management

## Current State Analysis

### What Works Well (Reference Standard)
- **Generator Grid**: 2Ã—4 flat slots with absolute positioning, consistent sizing, clean visual hierarchy
- **Modulator Grid**: 2Ã—2 flat slots with per-type layouts (LFO/Sloth/ARSEq+/SauceOfGrav), scopes integrated cleanly
- **Design pattern**: SLOT_LAYOUT dicts define all positions, fixed slot dimensions, accent borders for active state

### Current Problems

| Section | Issue | Impact |
|---------|-------|--------|
| FX Strip | Horizontal module layout, not slot-based | Inconsistent with rest of UI |
| FX Strip | Different height than Master section | Visual imbalance in bottom bar |
| Master Section | Long and thin horizontal layout | Compressor dominates, poor hierarchy |
| Mixer Panel | Excessive vertical space | Squeezes other content unnecessarily |
| Boid Panel | Overlays modulator section | Obscures modulators, feels tacked-on |
| Overall | Right side (Mixer/Boids) not unified | Wasted space, awkward proportions |

---

## Proposed Layout Architecture

### High-Level Grid Structure

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ HEADER BAR                                                                       â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚              â”‚                                            â”‚                     â”‚
â”‚  MODULATOR   â”‚           GENERATOR GRID                   â”‚   RIGHT PANEL      â”‚
â”‚    GRID      â”‚              (2Ã—4)                         â”‚                     â”‚
â”‚   (2Ã—2)      â”‚                                            â”‚   â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚              â”‚                                            â”‚   â”‚  BOIDS      â”‚  â”‚
â”‚  320px fixed â”‚                                            â”‚   â”‚  MINI VIZ   â”‚  â”‚
â”‚              â”‚                                            â”‚   â”‚  + CONTROLS â”‚  â”‚
â”‚              â”‚                                            â”‚   â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤  â”‚
â”‚              â”‚                                            â”‚   â”‚             â”‚  â”‚
â”‚              â”‚                                            â”‚   â”‚   MIXER     â”‚  â”‚
â”‚              â”‚                                            â”‚   â”‚  8-CHANNEL  â”‚  â”‚
â”‚              â”‚                                            â”‚   â”‚  COMPACT    â”‚  â”‚
â”‚              â”‚                                            â”‚   â”‚             â”‚  â”‚
â”‚              â”‚                                            â”‚   â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                              BOTTOM BAR                                          â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚ FX 1   â”‚ FX 2   â”‚ FX 3   â”‚ FX 4   â”‚          MASTER SECTION               â”‚ â”‚
â”‚  â”‚ SLOT   â”‚ SLOT   â”‚ SLOT   â”‚ SLOT   â”‚   â”Œâ”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚ â”‚
â”‚  â”‚        â”‚        â”‚        â”‚        â”‚   â”‚ EQ  â”‚COMP â”‚  OUTPUT   â”‚ METER  â”‚  â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”´â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚ â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### Key Changes

1. **Right Panel Consolidation**: Boids + Mixer share vertical space on right side
2. **FX Slot System**: 4 identical FX slots, selectable effect type per slot
3. **Master Section Restructure**: Horizontal sub-sections with consistent heights
4. **Bottom Bar Unified Height**: FX slots and Master align perfectly

---

## Component Specifications

### 1. Four-Slot Send FX System

The FX section becomes a true 4-slot system where each slot can be assigned different effect types. Each slot has its own send bus from the channel strips.

#### Architecture Overview

```
CHANNEL STRIPS (per-gen)
  â”‚
  â”œâ”€â”€â–º FX1 Send â”€â”€â–º ~fx1SendBus â”€â”€â–º FX SLOT 1 [selectable type] â”€â”€â–º ~fx1ReturnBus â”€â”€â”
  â”œâ”€â”€â–º FX2 Send â”€â”€â–º ~fx2SendBus â”€â”€â–º FX SLOT 2 [selectable type] â”€â”€â–º ~fx2ReturnBus â”€â”€â”¼â”€â”€â–º masterBus
  â”œâ”€â”€â–º FX3 Send â”€â”€â–º ~fx3SendBus â”€â”€â–º FX SLOT 3 [selectable type] â”€â”€â–º ~fx3ReturnBus â”€â”€â”¤
  â”œâ”€â”€â–º FX4 Send â”€â”€â–º ~fx4SendBus â”€â”€â–º FX SLOT 4 [selectable type] â”€â”€â–º ~fx4ReturnBus â”€â”€â”˜
  â”‚
  â””â”€â”€â–º masterBus (dry)
```

#### FX Slot Layout

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                                    SEND FX                                           â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚      FX SLOT 1    â”‚     FX SLOT 2     â”‚     FX SLOT 3     â”‚       FX SLOT 4         â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ FX1 [Echo      â–¼] â”‚ FX2 [Reverb    â–¼] â”‚ FX3 [Chorus    â–¼] â”‚ FX4 [Phaser     â–¼]      â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚                   â”‚                   â”‚                   â”‚                         â”‚
â”‚ â”Œâ”€â”€â”â”Œâ”€â”€â”â”Œâ”€â”€â”â”Œâ”€â”€â”  â”‚ â”Œâ”€â”€â”â”Œâ”€â”€â”â”Œâ”€â”€â”â”Œâ”€â”€â”  â”‚ â”Œâ”€â”€â”â”Œâ”€â”€â”â”Œâ”€â”€â”â”Œâ”€â”€â”  â”‚ â”Œâ”€â”€â”â”Œâ”€â”€â”â”Œâ”€â”€â”â”Œâ”€â”€â”        â”‚
â”‚ â”‚  â”‚â”‚  â”‚â”‚  â”‚â”‚  â”‚  â”‚ â”‚  â”‚â”‚  â”‚â”‚  â”‚â”‚  â”‚  â”‚ â”‚  â”‚â”‚  â”‚â”‚  â”‚â”‚  â”‚  â”‚ â”‚  â”‚â”‚  â”‚â”‚  â”‚â”‚  â”‚        â”‚
â”‚ â””â”€â”€â”˜â””â”€â”€â”˜â””â”€â”€â”˜â””â”€â”€â”˜  â”‚ â””â”€â”€â”˜â””â”€â”€â”˜â””â”€â”€â”˜â””â”€â”€â”˜  â”‚ â””â”€â”€â”˜â””â”€â”€â”˜â””â”€â”€â”˜â””â”€â”€â”˜  â”‚ â””â”€â”€â”˜â””â”€â”€â”˜â””â”€â”€â”˜â””â”€â”€â”˜        â”‚
â”‚ (params vary by   â”‚ (params vary by   â”‚ (params vary by   â”‚ (params vary by         â”‚
â”‚  selected type)   â”‚  selected type)   â”‚  selected type)   â”‚  selected type)         â”‚
â”‚                   â”‚                   â”‚                   â”‚                         â”‚
â”‚ [BYP] [INI][T1]   â”‚ [BYP] [INI][T1]   â”‚ [BYP] [INI][T1]   â”‚ [BYP] [INI][T1]         â”‚
â”‚            [T2]   â”‚            [T2]   â”‚            [T2]   â”‚            [T2]         â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
       ~160px              ~160px              ~160px              ~160px
```

#### Available FX Types (Per Slot)

| Type | Description | Key Params |
|------|-------------|------------|
| **Empty** | Pass-through (muted) | - |
| **Echo** | Tape delay with degradation | Time, Feedback, Wow, Tone, Spring |
| **Reverb** | Plate/Room reverb | Size, Decay, Tone, Damping |
| **Chorus** | Stereo chorus/ensemble | Rate, Depth, Mix, Voices |
| **Phaser** | Multi-stage phaser | Rate, Depth, Feedback, Stages |
| **Flanger** | Through-zero flanger | Rate, Depth, Feedback, Manual |
| **Tremolo** | Amplitude modulation | Rate, Depth, Shape, Stereo |
| **LoFi** | Bit crush / sample rate reduction | Bits, Rate, Noise, Filter |
| **Ring Mod** | Ring modulator | Freq, Mix, LFO Rate |
| **Grain** | Granular delay/stretch | Size, Pitch, Density, Spread |

#### FX Slot Widget Structure

Each slot follows the flat layout pattern from generators/modulators:

```python
FX_SLOT_LAYOUT = {
    'slot_width': 160,
    'slot_height': 150,
    
    # Header
    'id_x': 5, 'id_y': 4,
    'selector_x': 30, 'selector_y': 2,
    'selector_w': 120, 'selector_h': 22,
    
    # Params (4 sliders standard, type-specific)
    'slider_y': 28,
    'slider_h': 80,
    'slider_w': 18,
    'slider_spacing': 6,
    'p1_x': 15, 'p2_x': 45, 'p3_x': 75, 'p4_x': 105,
    
    # Return level (all types)
    'return_x': 135, 'return_y': 28,
    
    # Bottom row
    'bypass_x': 5, 'bypass_y': 125,
    'turbo_x': 60, 'turbo_y': 125,
}
```

---

### 2. Channel Strip Send Expansion

Each channel strip gets 4 send knobs instead of 2:

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚      CH 1       â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚   [EQ KNOBS]    â”‚
â”‚   HI  MID  LO   â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚    â”Œâ”€â”€â”€â”€â”€â”€â”     â”‚
â”‚    â”‚ VOL  â”‚     â”‚  â† Volume fader
â”‚    â”‚      â”‚     â”‚
â”‚    â””â”€â”€â”€â”€â”€â”€â”˜     â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚   SENDS         â”‚
â”‚  FX1 FX2 FX3 FX4â”‚  â† 4 send knobs
â”‚   â—‹   â—‹   â—‹   â—‹ â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚   [M] [S]       â”‚  â† Mute/Solo
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Send Labels**: Could show abbreviated FX type (e.g., "ECH", "VRB", "CHO", "PHA") or just FX1-4.

---

### 3. Master Section (Heat + Filter + Processing)

Heat and Dual Filter move into Master as fixed inserts, followed by EQ, Compressor, and Output:

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚ MASTER                                                                            â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚   HEAT   â”‚    FILTER     â”‚    EQ     â”‚    COMP     â”‚          OUTPUT             â”‚
â”‚ (insert) â”‚   (insert)    â”‚           â”‚             â”‚                             â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ â”Œâ”€â”€â”â”Œâ”€â”€â” â”‚ â”Œâ”€â”€â”â”Œâ”€â”€â”â”Œâ”€â”€â”  â”‚ â”Œâ”€â”€â”â”Œâ”€â”€â”  â”‚ â”Œâ”€â”€â” â”Œâ”€â”€â”  â”‚   â”Œâ”€â”€â”€â”€â”                    â”‚
â”‚ â”‚DRâ”‚â”‚MXâ”‚ â”‚ â”‚F1â”‚â”‚R1â”‚â”‚F2â”‚  â”‚ â”‚LOâ”‚â”‚MDâ”‚  â”‚ â”‚THâ”‚ â”‚RTâ”‚  â”‚   â”‚    â”‚  â”Œâ”€â”€â”  â”Œâ”€â”€â”        â”‚
â”‚ â””â”€â”€â”˜â””â”€â”€â”˜ â”‚ â””â”€â”€â”˜â””â”€â”€â”˜â””â”€â”€â”˜  â”‚ â””â”€â”€â”˜â””â”€â”€â”˜  â”‚ â””â”€â”€â”˜ â””â”€â”€â”˜  â”‚   â”‚    â”‚  â”‚â–“â–“â”‚  â”‚â–“â–“â”‚        â”‚
â”‚          â”‚ â”Œâ”€â”€â”          â”‚ â”Œâ”€â”€â”â”Œâ”€â”€â”  â”‚ â”Œâ”€â”€â” â”Œâ”€â”€â”  â”‚   â”‚ V  â”‚  â”‚â–“â–“â”‚  â”‚â–“â–“â”‚        â”‚
â”‚ [CIRCUIT]â”‚ â”‚R2â”‚ [LP][LP] â”‚ â”‚HIâ”‚â”‚LCâ”‚  â”‚ â”‚ATâ”‚ â”‚RLâ”‚  â”‚   â”‚ O  â”‚  â”‚â–“â–“â”‚  â”‚â–“â–“â”‚        â”‚
â”‚          â”‚ â””â”€â”€â”˜          â”‚ â””â”€â”€â”˜â””â”€â”€â”˜  â”‚ â””â”€â”€â”˜ â””â”€â”€â”˜  â”‚   â”‚ L  â”‚  â”‚â–“â–“â”‚  â”‚â–“â–“â”‚        â”‚
â”‚          â”‚ [SER/PAR]     â”‚           â”‚ â”Œâ”€â”€â” â”Œâ”€â”€â”  â”‚   â”‚    â”‚  â”‚â–“â–“â”‚  â”‚â–“â–“â”‚        â”‚
â”‚ [BYP]    â”‚ [SYNC1][SYNC2]â”‚ [K][K][K] â”‚ â”‚MKâ”‚ â”‚HPâ”‚  â”‚   â”‚    â”‚  â”‚â–“â–“â”‚  â”‚â–“â–“â”‚        â”‚
â”‚          â”‚ [BYP]         â”‚ [BYP]     â”‚ â””â”€â”€â”˜ â””â”€â”€â”˜  â”‚   â””â”€â”€â”€â”€â”˜  â””â”€â”€â”˜  â””â”€â”€â”˜        â”‚
â”‚          â”‚               â”‚           â”‚ [BYP] [GR] â”‚   [LIM]                      â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
   ~100px      ~140px         ~100px       ~120px            ~100px
```

**Signal Flow in Master**:
```
masterBus (dry + FX returns) â†’ HEAT â†’ FILTER â†’ EQ â†’ COMP â†’ LIMITER â†’ OUTPUT
```

---

### 3. Right Panel (Boids + Mixer)

**Principle**: Combine Boids and Mixer into single vertical strip, each taking appropriate space.

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚       BOIDS SECTION       â”‚  â† ~180px height
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚ [BOIDS] [â—] COUNT: 8 â†•   â”‚
â”‚                           â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚   MINI VISUALIZER   â”‚  â”‚  â† 60px
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â”‚                           â”‚
â”‚ DISP ENGY FADE DPTH       â”‚  â† Compact knob row
â”‚  â—‹    â—‹    â—‹    â—‹        â”‚
â”‚                           â”‚
â”‚ Zones: [G][M][C][F]       â”‚  â† Toggle buttons
â”‚ Rows:  [1][2][3][4]       â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚       MIXER SECTION       â”‚  â† Fills remaining space
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚  1   2   3   4   5   6   7   8  â”‚
â”‚ â”Œâ”€â” â”Œâ”€â” â”Œâ”€â” â”Œâ”€â” â”Œâ”€â” â”Œâ”€â” â”Œâ”€â” â”Œâ”€â”â”‚  â† Mini meters
â”‚ â”‚â–“â”‚ â”‚â–“â”‚ â”‚â–“â”‚ â”‚â–“â”‚ â”‚â–“â”‚ â”‚â–“â”‚ â”‚â–“â”‚ â”‚â–“â”‚â”‚
â”‚ â””â”€â”˜ â””â”€â”˜ â””â”€â”˜ â””â”€â”˜ â””â”€â”˜ â””â”€â”˜ â””â”€â”˜ â””â”€â”˜â”‚
â”‚ â”Œâ”€â” â”Œâ”€â” â”Œâ”€â” â”Œâ”€â” â”Œâ”€â” â”Œâ”€â” â”Œâ”€â” â”Œâ”€â”â”‚  â† Volume sliders
â”‚ â”‚ â”‚ â”‚ â”‚ â”‚ â”‚ â”‚ â”‚ â”‚ â”‚ â”‚ â”‚ â”‚ â”‚ â”‚ â”‚â”‚
â”‚ â””â”€â”˜ â””â”€â”˜ â””â”€â”˜ â””â”€â”˜ â””â”€â”˜ â””â”€â”˜ â””â”€â”˜ â””â”€â”˜â”‚
â”‚ [M][S] [M][S] ... per channel  â”‚  â† Mute/Solo
â”‚                                 â”‚
â”‚ Pan: â—‹  â—‹  â—‹  â—‹  â—‹  â—‹  â—‹  â—‹    â”‚  â† Collapsed EQ (click to expand?)
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Right Panel Width**: 280-300px fixed
**Boids Section Height**: ~180px (compact controls)
**Mixer Section**: Fills remaining vertical space

#### Mixer Compaction Strategy

1. **Remove per-channel EQ knobs** from main view (move to popup or strip detail)
2. **Smaller faders**: 60px height instead of current tall faders
3. **Mini meters**: 30px height, inline with labels
4. **Horizontal Mute/Solo row**: Single row of tiny toggles
5. **Sends as knobs**: Echo/Verb sends as small knobs in a row below faders

---

### 4. Inline FX Strip â†’ FX Slot Grid

**New File**: `src/gui/fx_slot.py` (replaces `inline_fx_strip.py`)

```python
# FX Slot - Flat absolute positioning like generator_slot_new.py

FX_TYPES = ["Empty", "Echo", "Verb", "Chorus", "Heat", "Filter", "Phaser", "Trem"]

class FXSlot(QWidget):
    """Single FX slot with selectable effect type."""
    
    # Signals
    type_changed = pyqtSignal(int, str)  # slot_id, fx_type
    param_changed = pyqtSignal(int, str, float)  # slot_id, param, value
    bypass_changed = pyqtSignal(int, bool)
    turbo_changed = pyqtSignal(int, int)  # slot_id, turbo_level (0/1/2)
```

**New File**: `src/gui/fx_grid.py`

```python
class FXGrid(QWidget):
    """4-slot FX grid for bottom bar."""
    
    def __init__(self, parent=None):
        # Create 4 FXSlot instances in horizontal row
        pass
```

---

## SuperCollider Changes Required

### 1. New Send Buses (`buses.scd`)

```supercollider
// Rename existing for consistency
~fx1SendBus = Bus.audio(s, 2);  // was ~echoSendBus
~fx2SendBus = Bus.audio(s, 2);  // was ~verbSendBus
~fx3SendBus = Bus.audio(s, 2);  // NEW
~fx4SendBus = Bus.audio(s, 2);  // NEW

~fx1ReturnBus = Bus.audio(s, 2);  // was ~echoReturnBus
~fx2ReturnBus = Bus.audio(s, 2);  // was ~verbReturnBus
~fx3ReturnBus = Bus.audio(s, 2);  // NEW
~fx4ReturnBus = Bus.audio(s, 2);  // NEW
```

### 2. Channel Strip Updates (`channel_strips.scd`)

```supercollider
SynthDef(\channelStrip, { |inBus, outBus, vol=0.8, mute=0, solo=0, gain=1.0, pan=0,
                          genTrim=0, soloActiveBus, slotID=1,
                          eqLo=1, eqMid=1, eqHi=1,
                          fx1Send=0, fx2Send=0, fx3Send=0, fx4Send=0,  // 4 sends
                          fx1SendBus, fx2SendBus, fx3SendBus, fx4SendBus,
                          fx1ModBus=(-1), fx2ModBus=(-1), fx3ModBus=(-1), fx4ModBus=(-1),
                          panModBus=(-1)|
    // ... existing code ...
    
    // FX Sends (post-fader)
    Out.ar(fx1SendBus, sig * Lag.kr(fx1SendEff, 0.02));
    Out.ar(fx2SendBus, sig * Lag.kr(fx2SendEff, 0.02));
    Out.ar(fx3SendBus, sig * Lag.kr(fx3SendEff, 0.02));
    Out.ar(fx4SendBus, sig * Lag.kr(fx4SendEff, 0.02));
    
    // Main output
    Out.ar(outBus, sig);
}).add;

// State arrays
~stripFx1SendState = Array.fill(8, { 0.0 });
~stripFx2SendState = Array.fill(8, { 0.0 });
~stripFx3SendState = Array.fill(8, { 0.0 });
~stripFx4SendState = Array.fill(8, { 0.0 });
```

### 3. Generic FX Slot SynthDef Pattern

```supercollider
// Base pattern for swappable FX - each type is a separate SynthDef
// All read from assigned send bus, write to assigned return bus

SynthDef(\fxSlot_echo, { |inBus, outBus, time=0.3, feedback=0.4, tone=0.7, 
                          wow=0, spring=0, returnLevel=0.5, bypass=0|
    // ... echo implementation ...
}).add;

SynthDef(\fxSlot_reverb, { |inBus, outBus, size=0.7, decay=0.5, tone=0.6,
                            damping=0.5, returnLevel=0.5, bypass=0|
    // ... reverb implementation ...
}).add;

SynthDef(\fxSlot_chorus, { |inBus, outBus, rate=0.5, depth=0.5, mix=0.5,
                            voices=2, returnLevel=0.5, bypass=0|
    // ... chorus implementation ...
}).add;

// etc for each FX type
```

### 4. FX Slot Manager

```supercollider
// Track which synth is in each slot
~fxSlotSynths = Array.fill(4, { nil });
~fxSlotTypes = Array.fill(4, { \empty });

// Swap effect in slot
~setFxSlotType = { |slotIndex, fxType|
    var inBus, outBus, synthName;
    
    // Free existing
    if(~fxSlotSynths[slotIndex].notNil) {
        ~fxSlotSynths[slotIndex].free;
    };
    
    // Get buses for this slot
    inBus = [~fx1SendBus, ~fx2SendBus, ~fx3SendBus, ~fx4SendBus][slotIndex];
    outBus = [~fx1ReturnBus, ~fx2ReturnBus, ~fx3ReturnBus, ~fx4ReturnBus][slotIndex];
    
    // Create new synth
    synthName = ("fxSlot_" ++ fxType).asSymbol;
    ~fxSlotSynths[slotIndex] = Synth(synthName, [
        \inBus, inBus,
        \outBus, outBus
    ], ~fxGroup);
    
    ~fxSlotTypes[slotIndex] = fxType;
};
```

---

## Implementation Phases

### Phase 1: SC Foundation
1. Add 2 new send/return bus pairs in `buses.scd`
2. Extend channel strip SynthDef with fx3Send, fx4Send
3. Add state arrays and OSC handlers for new sends
4. Create generic FX slot SynthDefs (start with Echo, Reverb, Chorus, Phaser)
5. Implement FX slot manager for swapping types
6. Test in SC directly

### Phase 2: FX Slot GUI
1. Create `fx_slot.py` - single FX slot widget with type selector
2. Create per-type LAYOUT dicts for param arrangement
3. Create `fx_grid.py` - 4-slot container
4. Wire type selection to SC slot manager
5. Wire params to appropriate OSC paths

### Phase 3: Channel Strip GUI Updates
1. Add FX3, FX4 send knobs to `mixer_panel.py`
2. Update channel strip state/preset handling
3. Wire new sends to OSC

### Phase 4: Master Section Refactor
1. Create `master_chain.py` with Heat, Filter, EQ, Comp, Output
2. Migrate from current master_section.py + inline_fx_strip.py
3. Flat layout with consistent heights

### Phase 5: Right Panel Consolidation
1. Create `right_panel.py` combining Boids + Mixer
2. Compact mixer with 4 send knobs per channel
3. Boids section ~180px, mixer fills remainder

### Phase 6: Integration & Polish
1. Update `main_frame.py` layout
2. Preset schema updates for new FX slots
3. Bus unification metadata for new params
4. Full testing pass

---

## Design Tokens (New/Modified)

```python
# In theme.py or skins/active.py

# FX Slots
'accent_fx_slot': '#4a90d9',      # Blue for FX slots
'accent_fx_slot_dim': '#2d5480',
'fx_slot_width': 160,
'fx_slot_height': 150,

# Master chain
'accent_master_insert': '#d94a4a',  # Red for Heat/Filter inserts
'accent_master_dynamics': '#4ad99a', # Green for EQ/Comp
'master_chain_width': 560,

# Bottom bar
'bottom_bar_height': 150,
'send_fx_width': 640,              # 4 slots Ã— 160px

# Right panel
'right_panel_width': 320,
'boids_section_height': 180,
'mixer_compact_fader_height': 60,
'channel_strip_width': 36,         # Compact for 4 sends
```

---

## File Changes Summary

### SuperCollider
| File | Action | Notes |
|------|--------|-------|
| `buses.scd` | MODIFY | Add fx3/fx4 send+return buses |
| `channel_strips.scd` | MODIFY | Add fx3Send, fx4Send params |
| `fx_slots.scd` | CREATE | Generic FX slot manager |
| `tape_echo.scd` | MODIFY | Adapt to fxSlot pattern |
| `reverb.scd` | MODIFY | Adapt to fxSlot pattern |
| `chorus.scd` | CREATE | New chorus SynthDef |
| `lofi.scd` | CREATE | Bitcrush/downsample (resurrects fidelity concept) |
| `phaser.scd` | CREATE | New phaser SynthDef |
| `osc_handlers.scd` | MODIFY | Remove orphaned fidelity_amount handler |
| (more FX types) | CREATE | As needed |

### Python/GUI
| File | Action | Notes |
|------|--------|-------|
| `fx_slot.py` | CREATE | Single FX slot widget with type selector |
| `fx_grid.py` | CREATE | 4-slot container |
| `master_chain.py` | CREATE | Heat, Filter, EQ, Comp, Output unified |
| `right_panel.py` | CREATE | Boids + Mixer combined |
| `mixer_panel.py` | MODIFY | Add FX3, FX4 send knobs |
| `inline_fx_strip.py` | DEPRECATE | Replaced by fx_grid + master_chain |
| `master_section.py` | DEPRECATE | Absorbed into master_chain |
| `main_frame.py` | MODIFY | New bottom bar layout |
| `theme.py` | MODIFY | Add FX slot tokens |
| `config/__init__.py` | MODIFY | FX types list, OSC paths |

---

## New FX Types to Implement

### Priority 1 (Core - Ship With 4-Slot System)
| Type | Description | Params |
|------|-------------|--------|
| Echo | Tape delay (exists, adapt) | Time, Feedback, Wow, Tone, Spring, Return |
| Reverb | Plate/Room (exists, adapt) | Size, Decay, Tone, Damping, Return |
| Chorus | Stereo ensemble | Rate, Depth, Mix, Voices, Return |
| LoFi | Bitcrush/downsample (resurrects old "fidelity") | Rate, Bits, Noise, Filter, Return |

**Note on LoFi**: Previously planned as master insert (`fidelity_amount` OSC path exists but DSP was never implemented). Converting to send effect gives more flexibility - can crush specific channels rather than whole mix.

#### LoFi Implementation (Standard UGens Only)

Use standard SC UGens to avoid sc3-plugins dependency. This keeps the project portable.

```supercollider
SynthDef(\fxSlot_lofi, { |inBus, outBus, rate=1.0, bits=1.0, noise=0, filter=0.5,
                          returnLevel=0.5, bypass=0,
                          rateBus=(-1), bitsBus=(-1), noiseBus=(-1), filterBus=(-1)|
    var sig, dry, wet;
    var rateHz, bitDepth, steps;
    var rateEff, bitsEff, noiseEff, filterEff;
    
    // Bus unification support
    rateEff = Select.kr(rateBus >= 0, [rate, In.kr(rateBus)]);
    bitsEff = Select.kr(bitsBus >= 0, [bits, In.kr(bitsBus)]);
    noiseEff = Select.kr(noiseBus >= 0, [noise, In.kr(noiseBus)]);
    filterEff = Select.kr(filterBus >= 0, [filter, In.kr(filterBus)]);
    
    sig = In.ar(inBus, 2);
    dry = sig;
    
    // Rate: 0-1 maps to 500Hz - 44100Hz (exponential)
    // At 1.0 = clean, at 0.0 = heavily crushed
    rateHz = rateEff.linexp(0, 1, 500, SampleRate.ir);
    
    // Bits: 0-1 maps to 2-16 bits
    // At 1.0 = 16-bit (clean), at 0.0 = 2-bit (destroyed)
    bitDepth = bitsEff.linlin(0, 1, 2, 16);
    steps = 2.pow(bitDepth);
    
    // Sample rate reduction via Latch
    wet = Latch.ar(sig, Impulse.ar(rateHz));
    
    // Bit depth reduction via round
    wet = (wet * steps).round / steps;
    
    // Optional noise/hiss (adds character)
    wet = wet + (PinkNoise.ar(0.02) * noiseEff);
    
    // Post-filter: LPF to tame aliasing artifacts
    // 0 = no filter, 1 = aggressive filter
    wet = LPF.ar(wet, filterEff.linexp(0, 1, 18000, 1000));
    
    // Return level
    wet = wet * Lag.kr(returnLevel, 0.02);
    
    // Bypass (click-free crossfade)
    sig = XFade2.ar(wet, dry * returnLevel, (Lag.kr(bypass, 0.02) * 2) - 1);
    
    Out.ar(outBus, sig);
}).add;
```

**Params**:
- **Rate** (0-1): Sample rate reduction. 1.0 = clean, 0.0 = ~500Hz aliased crunch
- **Bits** (0-1): Bit depth. 1.0 = 16-bit clean, 0.0 = 2-bit destruction  
- **Noise** (0-1): Pink noise mix for analog hiss character
- **Filter** (0-1): Post-LPF to tame aliasing. 0 = bright/harsh, 1 = dark/smooth
- **Return** (0-1): Effect return level

### Priority 2 (Essential)
| Type | Description | Params |
|------|-------------|--------|
| Phaser | Multi-stage | Rate, Depth, Feedback, Stages, Return |
| Flanger | Through-zero | Rate, Depth, Feedback, Manual, Return |
| Tremolo | Amp mod | Rate, Depth, Shape, Stereo, Return |

### Priority 3 (Creative)
| Type | Description | Params |
|------|-------------|--------|
| Filter | Resonant + LFO | Freq, Reso, Mode, LFO Rate, LFO Depth, Return |
| Ring Mod | Ring modulator | Freq, Mix, LFO Rate, LFO Depth, Return |
| Grain | Granular delay | Size, Pitch, Density, Spread, Return |
| Shimmer | Pitch-shifted verb | Size, Shift, Mix, Decay, Return |
| Distortion | Waveshaper | Drive, Tone, Mix, Type, Return |

---

## Questions to Resolve

1. **FX slot defaults**: Slots 1-4 default to Echo, Reverb, Chorus, LoFi?
2. **Mixer send labels**: Show FX type abbreviation or just FX1-4?
3. **Dual Filter controls**: All inline, or expandable/popup for sync params?
4. **Boid zone mapping**: Update for 4 FX slots? (currently targets Heat, Echo, Verb, Filter)
5. **Bus unification**: Add all new FX params to unified bus system?
6. **Legacy cleanup**: Remove orphaned `fidelity_amount` OSC path from config?

---

## Next Steps

1. Review spec - does 4-slot architecture feel right?
2. Confirm Priority 1 FX types: Echo, Reverb, Chorus, LoFi
3. Start with SC changes (buses, channel strips, slot manager)
4. Prototype single FX slot widget
5. Implement in phases with testing gates

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking preset compatibility | Version flag in schema, migration code |
| OSC path changes | Keep same paths, update only GUI |
| Regression in FX functionality | Parallel implementation, feature flag |
| Layout breaks on resize | Fixed widths for critical sections |

---

## Questions to Resolve

1. **Dual Filter controls**: All inline, or expandable/popup for sync params?
2. **Mixer EQ**: Hidden by default (popup on click)? Or remove from compact view?
3. **Boid presets dropdown**: Keep in compact view or move to popup?
4. **Visual separator**: How prominent between Send FX and Master sections?
5. **Limiter controls**: Just bypass toggle, or keep ceiling slider?

---

## Next Steps

1. Review this spec - does the Send FX | Master split feel right?
2. Decide on Dual Filter control density (compact vs expandable)
3. Prototype bottom bar with new layout
4. Get visual mockup approval before full implementation
5. Implement in phases with testing gates
