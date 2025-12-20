# FX Bus Architecture

**Status:** Design Complete, Not Started  
**Created:** 2025-12-14

---

## Overview

Separate send/return FX buses alongside the master insert chain. Classic console architecture - channels can send to shared effect buses which return to the master.

---

## Signal Flow

```
                                    ┌─────────────┐
Channel 1 ──┬──────────────────────→│             │
            ├──→ FX Bus A (Reverb) ─┤             │
            └──→ FX Bus B (Delay) ──┤             │
                                    │             │
Channel 2 ──┬──────────────────────→│ Master Bus  │→ Limiter → Comp → EQ → Master Vol → Output
            ├──→ FX Bus A ──────────┤             │
            └──→ FX Bus B ──────────┤             │
                                    │             │
            ...                     │             │
                                    │             │
FX A Return (with fader) ──────────→│             │
FX B Return (with fader) ──────────→│             │
                                    └─────────────┘
```

---

## Architecture Decisions

### Number of FX Buses
**Decision:** Start with 2 buses (A and B)

**Rationale:** 
- Covers most common use cases (reverb + delay)
- Keeps UI manageable
- Can expand later if needed

### FX Return Routing
**Decision:** FX returns go to their own fader, then to master bus (before master inserts)

**Rationale:**
- Independent control over wet level per bus
- FX returns benefit from master compression/limiting
- Standard console behaviour

### Per-Channel Send Controls
**Decision:** Send knobs located under the channel meters in the mixer panel

**Rationale:**
- Keeps send controls with their channel
- Meters already show channel activity
- Natural top-to-bottom signal flow (fader → meter → sends)

### Effect Selection
**Decision:** User-switchable effects per bus, same click-to-cycle method as generators

**Rationale:**
- Flexibility without complex routing UI
- Familiar interaction pattern
- Each bus can be any effect type

---

## FX Bus Detail

### Per Bus
- Effect type selector (click to cycle)
- Effect parameters (contextual to effect type)
- Return fader (level going to master)
- Return mute button
- Bus meter (shows activity)

### Effect Types (Initial Set)
| Effect | Description |
|--------|-------------|
| Reverb | Room/Hall/Plate modes |
| Delay | Sync to clock, feedback, ping-pong |
| Chorus | Stereo width, rate, depth |
| Phaser | Stages, rate, feedback |

*More can be added following the generator pattern (JSON config + SynthDef)*

---

## Channel Strip Send Controls

Each channel strip gains:
```
┌─────────────┐
│   [slot]    │
│    ████     │  ← Fader
│    ████     │
│   [M] [S]   │  ← Mute/Solo
│    ▮▮▮▮     │  ← Meter
│   [A] [B]   │  ← FX Send knobs (NEW)
│     0       │  ← Pan
└─────────────┘
```

Send controls:
- Small knobs or mini-faders
- 0-100% send level
- Click to toggle on/off, drag to set level
- Visual feedback when sending (LED or colour)

---

## UI Layout - FX Returns

FX returns need a home. Options:

**Option A: Below mixer channels (preferred)**
```
┌─────────────────────────────────────┐
│  1   2   3   4   5   6   7   8      │  ← Channels
│  █   █   █   █   █   █   █   █      │
│  █   █   █   █   █   █   █   █      │
├─────────────────────────────────────┤
│  FX A          │  FX B              │  ← FX Returns
│  [Reverb ▼]    │  [Delay ▼]         │
│  ████          │  ████              │
│  [params]      │  [params]          │
└─────────────────────────────────────┘
```

**Option B: Dedicated FX panel**
- Separate section in the frame layout
- More space for parameters
- But adds UI complexity

**Decision:** Option A - keeps mixing controls together

---

## Implementation Phases

### Phase A: Bus Infrastructure
- Create FX Bus A and B in SuperCollider
- OSC paths for send levels
- Basic passthrough (no effects yet)

### Phase B: Channel Sends
- Add send controls to channel strips
- Send level OSC messages
- Visual feedback

### Phase C: FX Returns
- Return faders in mixer panel
- Return meters
- Mute buttons

### Phase D: Effect Types
- Reverb SynthDef + JSON config
- Delay SynthDef + JSON config
- Effect type selector UI
- Parameter controls

### Phase E: Additional Effects
- Chorus, Phaser, etc.
- Follow generator pattern for adding new types

---

## SuperCollider Architecture

```supercollider
// Buses
~fxBusA = Bus.audio(s, 2);  // Stereo FX bus A
~fxBusB = Bus.audio(s, 2);  // Stereo FX bus B

// Groups (execution order matters)
~genGroup    // Generators write to masterBus AND fxBuses
~fxGroup     // FX processors read from fxBuses, write to masterBus
~masterGroup // Master chain reads from masterBus, writes to output

// Per-channel send levels (0.0 - 1.0)
~sendLevelsA = Array.fill(8, { 0.0 });
~sendLevelsB = Array.fill(8, { 0.0 });

// FX return levels
~fxReturnA = 1.0;
~fxReturnB = 1.0;
```

---

## OSC Paths

```
/noise/gen/sendA      [slot, level]   // Channel send to FX A
/noise/gen/sendB      [slot, level]   // Channel send to FX B
/noise/fx/a/type      [effectIndex]   // FX A effect type
/noise/fx/a/param     [paramIndex, value]  // FX A parameter
/noise/fx/a/return    [level]         // FX A return level
/noise/fx/a/mute      [0/1]           // FX A return mute
/noise/fx/b/...       // Same for FX B
```

---

## Open Questions

1. **Pre/Post fader sends?** 
   - Pre-fader: send level independent of channel fader (useful for reverb tails)
   - Post-fader: send follows channel level (more intuitive)
   - Start with post-fader, add toggle later?

2. **FX parameters UI**
   - How many params visible at once?
   - Contextual to effect type (like generator custom params)?

3. **Preset system interaction**
   - Should presets include FX settings?
   - Or keep FX as a separate "mix" preset?

---

## Dependencies

- Requires channel strips complete ✅
- Requires master bus architecture ✅
- Benefits from preset system (future)
- Benefits from MIDI mapping (future)

---

## References

- Console send/return: Standard mixing practice
- Generator cycle pattern: `src/gui/generator_slot.py`
- Channel strip: `src/gui/mixer_panel.py`
