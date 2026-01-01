# Cross-Modulation Bus Design

## Overview

Add an 8-channel cross-modulation bus where generators can modulate each other's parameters via audio-derived control signals (envelope followers).

**Status:** Implementation ready  
**Spec Version:** 1.2  
**Reviewed by:** AI1, AI2

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CROSS-MODULATION SYSTEM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Generator 1 ──► ~genBus[0] ──► EnvFollower ──► ~crossModBus[0] ──┐       │
│   Generator 2 ──► ~genBus[1] ──► EnvFollower ──► ~crossModBus[1] ──┤       │
│   Generator 3 ──► ~genBus[2] ──► EnvFollower ──► ~crossModBus[2] ──┤       │
│   Generator 4 ──► ~genBus[3] ──► EnvFollower ──► ~crossModBus[3] ──┼──► Mod │
│   Generator 5 ──► ~genBus[4] ──► EnvFollower ──► ~crossModBus[4] ──┤  Route │
│   Generator 6 ──► ~genBus[5] ──► EnvFollower ──► ~crossModBus[5] ──┤       │
│   Generator 7 ──► ~genBus[6] ──► EnvFollower ──► ~crossModBus[6] ──┤       │
│   Generator 8 ──► ~genBus[7] ──► EnvFollower ──► ~crossModBus[7] ──┘       │
│                                                                             │
│   Source IDs: 16-23 (slots 1-8) - uses unified ~getModSourceBus resolver   │
│   ~crossModBus[n] routes to any slot's param via mod_apply_v2              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### 1. Envelope Follower Based (Not Direct Audio)

Audio-rate cross-modulation is computationally expensive and introduces phase-dependent artifacts. Instead, we derive a control signal from each generator's audio output using envelope followers.

**Benefits:**
- Control-rate efficiency (kr, not ar)
- No phase artifacts
- Musically useful (amplitude tracking)
- Configurable attack/release for different behaviors

**Latency:** One control-block latency (~1.3ms @ 64 samples, ~2.7ms @ 128 samples at 48kHz). Self-modulation creates a feedback loop that is stable due to envelope smoothing.

### 2. Signal Range: Unipolar (0 to 1)

Crossmod follower output is **unipolar** 0..1:
- Silence → 0
- Max amplitude → 1

This is intentionally different from LFO/Sloth sources (-1..+1). Rationale: **silence=0 is intuitive** — users expect "no audio = no modulation."

#### Polarity Mapping (Implementation Detail)

The existing `mod_apply_v2` polarity logic assumes bipolar -1..+1 sources. With 0..1 crossmod sources, the formulas produce **half-range** results:

| Polarity | Formula (s=source) | s=0 (silence) | s=1 (loud) | Effective |
|----------|-------------------|---------------|------------|-----------|
| bipolar | `s × r` | 0 | +r | Direct positive |
| uni+ | `((s+1)×0.5) × r` | 0.5r | r | Upper half |
| uni- | `-((s+1)×0.5) × r` | -0.5r | -r | Lower half |

Where `r = depth × amount`.

**For crossmod sources, `polarity=bipolar` behaves as "direct unipolar"** (0..r) because we do not remap 0..1 → -1..+1. This is the most intuitive mode for envelope followers.

**We avoid changing polarity mapping semantics in v1.2** to preserve existing mod-routing behavior and presets. Only bus resolution is changed (via `~getModSourceBus`).

#### Practical Recipes

| Goal | Polarity | Invert | Result |
|------|----------|--------|--------|
| **Positive mod** (silence=0, loud=up) | bipolar | 0 | 0..+r |
| **Negative mod / duck** (silence=0, loud=down) | bipolar | 1 | 0..-r |

These two recipes cover most use cases. The `invert` flag is the cleanest way to flip direction.

#### Future Enhancement

A future version may add `source_unipolar` flag to `mod_apply_v2` for proper 0..1 → -1..+1 mapping, enabling full-range polarity modes for crossmod sources.

### 3. Integration with Existing Mod Routing

Cross-mod buses appear as additional modulation sources in the existing `mod_apply_v2` system:
- Current mod buses: indices 0-15 (4 slots × 4 outputs)
- Cross-mod buses: indices 16-23 (8 generators)

**SSOT Constants:**
- SuperCollider: `~CROSSMOD_BUS_OFFSET = 16`, `~CROSSMOD_BUS_COUNT = 8`
- Python: `CROSSMOD_BUS_OFFSET = 16`, `CROSSMOD_BUS_COUNT = 8`

**Unified Bus Resolver:** `~getModSourceBus.(sourceBus)` handles both domains:
- 0-15 → `~modBuses[i]`
- 16-23 → `~crossModBus[i-16]`

### 4. Route Slot Competition

Crossmod routes compete with standard mod routes for the **4-slot limit per destination param**. If a destination already has 4 routes, adding crossmod fails with a warning.

### 5. Non-Invasive to Generators

No changes to generator templates. The envelope followers tap from `~genBus[n]` which already exists.

### 6. Tap Point: Post-Trim, Pre-Fader

Followers tap `~genBus[n]` (after generator, before channel strip) and apply the loudness trim to normalize loud/quiet generators.

**`~stripTrimState` is the canonical trim value for each slot**, shared by both channel strip and crossmod follower. The `/noise/gen/trim` OSC handler syncs trim to both.

### 7. Group Placement

Followers run in `~genGroup` at tail (after generator, before strip group). This ensures:
- Follower reads generator output after it's written
- Follower runs before channel strip processing

## OSC Interface

| Path | Args | Description |
|------|------|-------------|
| `/noise/crossmod/attack` | `[slot, seconds]` | Follower attack time (1ms-2s) |
| `/noise/crossmod/release` | `[slot, seconds]` | Follower release time (10ms-5s) |
| `/noise/crossmod/enabled` | `[slot, 0\|1]` | Enable/disable per-slot output |
| `/noise/crossmod/route` | `[src, tgt, param, depth, amount, offset, polarity, invert]` | Add/update route |
| `/noise/crossmod/unroute` | `[src, tgt, param]` | Remove route |
| `/noise/crossmod/clear` | `[]` | Clear all crossmod routes |
| `/noise/crossmod/debug` | `[]` | Dump follower and route state |

### Route Semantics

**`/route` is idempotent** — overwrites existing (src, tgt, param) route if present. No need to unroute before changing parameters.

### Enabled Behavior

When disabled (`/noise/crossmod/enabled slot 0`):
- Follower synth is **freed** (CPU efficient)
- Bus outputs **0** (silence)
- Routes remain configured but receive 0
- Re-enabling **recreates follower** if generator is running

### Parameters

- `src, tgt`: slot numbers **1-8** (OSC is 1-based; internal SC arrays are 0-based, use `slot-1`)
- `param`: **canonical names only** (no aliases):
  - `frequency`, `cutoff`, `resonance`, `attack`, `decay`
  - `p1`, `p2`, `p3`, `p4`, `p5` (custom params)
- `depth`: 0.0-1.0 (range width)
- `amount`: 0.0-1.0 (VCA level)
- `offset`: -1.0-1.0 (shifts mod range up/down from base)
- `polarity`: 0=bipolar, 1=uni+, 2=uni-
- `invert`: 0=normal, 1=inverted

## Implementation Files

### SuperCollider Core

| File | Purpose |
|------|---------|
| `crossmod_buses.scd` | Bus allocation, SSOT constants, `~getModSourceBus` resolver |
| `crossmod_followers.scd` | `\crossModFollower` SynthDef, start/stop helpers, trim sync |
| `crossmod_osc.scd` | OSC handlers, route tracking |

### Load Order in `init.scd`

These files are **required includes** in `supercollider/init.scd` alongside existing `core/*` loads:

```
mod_buses.scd        // ~modBuses (0-15)
crossmod_buses.scd   // ~crossModBus (16-23) + ~getModSourceBus resolver
mod_apply_v2.scd     // Uses ~getModSourceBus for both domains
...
crossmod_followers.scd
crossmod_osc.scd
```

**Critical:** `crossmod_buses.scd` must load BEFORE `mod_apply_v2.scd` because the latter uses `~getModSourceBus`.

### Integration Points

1. **mod_apply_v2.scd:** Updated to use `~getModSourceBus.(sourceBus)` instead of `~modBuses[sourceBus]`
2. **helpers.scd:** `~startGenerator` calls `~startCrossModFollower`, `~stopGenerator` calls `~stopCrossModFollower`
3. **osc_handlers.scd:** `/noise/gen/trim` handler calls `~setCrossModTrim` to sync loudness (shares `~stripTrimState`)

### Python Integration

| File | Purpose |
|------|---------|
| `src/gui/crossmod_state.py` | State management (matches mod_routing_state.py pattern) |
| `src/config/__init__.py` | SSOT constants + OSC paths |
| `src/presets/preset_schema.py` | Validation for crossmod section |

### Preset Schema

```json
{
  "crossmod": {
    "attack": [0.01, 0.01, ...],     // 8 values, seconds
    "release": [0.1, 0.1, ...],       // 8 values, seconds
    "enabled": [true, true, ...],     // 8 values, bool
    "connections": [
      {
        "source_slot": 1,
        "target_slot": 2,
        "target_param": "cutoff",
        "depth": 0.5,
        "amount": 1.0,
        "offset": 0.0,
        "polarity": 0,
        "invert": false
      }
    ]
  }
}
```

## Use Cases

### 1. Sidechain Ducking
Generator 1 (kick) ducks Generator 2 (pad) cutoff:
```
/noise/crossmod/route 1 2 cutoff 1.0 1.0 0.0 0 1
```
- `polarity=0` (bipolar): direct 0..r mapping
- `invert=1`: flips to 0..-r
- Silence = no change, loud = cutoff drops

### 2. Sympathetic Resonance
Generator 3 boosts Generator 4 decay when active:
```
/noise/crossmod/route 3 4 decay 0.3 1.0 0.0 0 0
```
- `polarity=0`, `invert=0`: 0..+0.3
- When GEN3 is loud, GEN4 decay lengthens

### 3. Amplitude-Coupled Pitch (Pseudo-FM)
Generator 5 modulates Generator 6 frequency based on amplitude:
```
/noise/crossmod/route 5 6 frequency 0.2 1.0 0.0 0 0
```
Not true FM (audio-rate), but creates pitch movement coupled to GEN5's loudness.

### 4. Brightness Tracking
Generator 7 brightens Generator 8 cutoff when playing:
```
/noise/crossmod/route 7 8 cutoff 0.5 1.0 0.0 0 0
```
- Silence = no change, loud = cutoff rises by 0.5×range

## Testing

### Basic Functionality
```bash
# In SuperCollider post-boot:
~debugCrossModFollowers.()   # Show follower states
~debugCrossModRoutes.()      # Show active routes

# Via OSC - test sidechain duck (bipolar + invert):
/noise/crossmod/route 1 2 cutoff 1.0 1.0 0.0 0 1
# GEN1 loud → GEN2 cutoff drops

# Via OSC - test positive mod:
/noise/crossmod/route 1 2 cutoff 0.5 1.0 0.0 0 0
# GEN1 loud → GEN2 cutoff rises

/noise/crossmod/debug  # Dump state
```

### Edge Cases
- Self-modulation (GEN1 → GEN1.param) - creates feedback loop, stable with envelope
- Multiple sources to same target - limit 4 per mod_apply_v2 design, warns on overflow
- Generator stop/start while route active - follower lifecycle managed in helpers.scd
- Trim changes while active - `/noise/gen/trim` syncs to follower via `~setCrossModTrim`
- Disable/re-enable - follower freed on disable, recreated on enable if generator running

## UI Considerations (Deferred)

### Matrix View
8×8 grid showing which generator modulates which:
- Rows: Source generators (1-8)
- Columns: Target slots (1-8)
- Click cell to configure route

### Per-Route Controls
- Depth (0-1)
- Amount (0-1)
- Offset (-1 to 1)
- Polarity (bipolar/uni+/uni-)
- Invert toggle

### Per-Follower Controls
- Attack time (1ms - 2s)
- Release time (10ms - 5s)
- Enabled toggle

## Future Enhancements

1. **Sidechain EQ** - Frequency-selective cross-mod (filter before follower)
2. **Lag/Slew** - Smoothing beyond attack/release
3. **Threshold** - Gate below certain level
4. **Mix modes** - Different combining methods for multiple sources

---
**Status:** Signed off 2025-12-30
