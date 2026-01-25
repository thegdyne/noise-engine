# Modulation Unification Specification v1.0

## Status: DRAFT
## Author: Claude
## Date: 2025-01-24

---

## 1. Executive Summary

Unify all modulation systems (generator params, extended targets, boids) into a single bus-based architecture where:

1. **UI writes base values** to a queue
2. **Mod sources write** to mod buses (existing)
3. **Single apply tick** computes `effective = base + modulation + boid`
4. **Synths read from buses** via `In.kr(bus)` - never `.set()`

This eliminates race conditions, simplifies the codebase, and provides a single source of truth for all parameter values.

---

## 2. Current Problems

### 2.1 Generator Modulation (`mod_apply.scd`)
- Uses 40 passthrough synths that call `.set()` on generators
- Expensive: 40 synths running continuously
- Race condition: UI `.set()` can collide with mod `.set()`
- No boid integration

### 2.2 Extended Modulation (`ext_mod.scd`)
- 500Hz Task that calls `.set()` on target synths
- Caches base values at route creation (stale if UI changes)
- Separate code path from generator modulation
- No boid integration

### 2.3 Bus Unification (`bus_unification.scd`)
- Only covers 71 extended targets (mod slots, channels, FX)
- Not used by generators yet
- Has boid integration
- Correct architecture, needs expansion

---

## 3. Unified Architecture

### 3.1 Core Principle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Python    │     │  Mod Source │     │    Boid     │
│  (UI Base)  │     │   Synths    │     │   Python    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       ▼                   ▼                   ▼
  ~queueBaseUpdate    ~modBuses[0-15]    ~queueBoidOp
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │  Apply Tick │
                    │   (500Hz)   │
                    └──────┬──────┘
                           │
              effective = base + mod + boid
                           │
                    ┌──────▼──────┐
                    │ Target Bus  │
                    │  (In.kr)    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Synth     │
                    │ reads bus   │
                    └─────────────┘
```

### 3.2 Single Apply Tick

One 500Hz tick handles ALL modulation:

```supercollider
~applyTick = Task({
    inf.do {
        // 1. Drain base value queue
        while({ ~pendingBaseUpdates.size > 0 }, {
            var update = ~pendingBaseUpdates.pop;
            var state = ~modTargetState[update.key];
            if(state.notNil) { state.baseValue = update.value };
        });

        // 2. Drain route operation queue
        while({ ~pendingRouteOps.size > 0 }, {
            var op = ~pendingRouteOps.pop;
            // Apply add/remove/clear operations
        });

        // 3. Snapshot mod buses (for routing)
        ~snapshotModBuses.();

        // 4. For each target with routes OR boid enabled:
        ~modTargetState.keysValuesDo { |targetKey, state|
            var meta = ~targetMeta[targetKey];
            var routes = ~modRoutes[targetKey];
            var modSum = 0;
            var boidOffset = 0;
            var effective;

            // Sum all route contributions
            if(routes.notNil, {
                routes.do { |route|
                    var sourceVal = ~getModSourceValue.(route.sourceKey);
                    var delta = /* apply polarity, invert, depth, amount, offset */;
                    modSum = modSum + delta;
                };
            });

            // Add boid contribution
            if(~boidEnabled, {
                var idx = meta.busIndex - ~unifiedBusBase;
                var scale = ~boidScales[targetKey] ? 1.0;
                boidOffset = ~boidOffsets[idx] * scale * (meta.max - meta.min);
            });

            // Compute and write effective value
            effective = state.baseValue + (modSum * (meta.max - meta.min)) + boidOffset;
            effective = effective.clip(meta.min, meta.max);
            state.bus.set(effective);
        };

        0.002.wait;  // 500Hz
    };
}).play(SystemClock);
```

---

## 4. Bus Allocation

### 4.1 Overview

| Category        | Count | Description                                    |
|-----------------|-------|------------------------------------------------|
| Generator Params| 40    | 8 slots × 5 params (freq, cutoff, res, atk, dec) |
| Custom Params   | 40    | 8 slots × 5 custom params (custom0-4)          |
| Mod Slots       | 28    | 4 slots × 7 params (P0-P6)                     |
| Channels        | 24    | 8 channels × 3 params (echo, verb, pan)        |
| FX: Heat        | 2     | drive, mix                                      |
| FX: Echo        | 6     | time, feedback, tone, wow, spring, verbSend    |
| FX: Reverb      | 3     | size, decay, tone                               |
| FX: Dual Filter | 8     | drive, freq1, freq2, reso1, reso2, syncAmt, harmonics, mix |
| **Total**       | **151** |                                              |

### 4.2 Target Key Naming Convention

```
Generator params:  gen_<slot>_<param>   e.g., gen_1_cutoff, gen_3_frequency
Custom params:     gen_<slot>_custom<n> e.g., gen_1_custom0, gen_2_custom3
Mod slot params:   mod_<slot>_p<n>      e.g., mod_1_p0, mod_2_p4
Channel params:    chan_<ch>_<param>    e.g., chan_1_echo, chan_3_pan
FX params:         fx_<fx>_<param>      e.g., fx_heat_drive, fx_echo_time
```

### 4.3 Generator Parameter Ranges

| Param     | Min   | Max    | Default | Unit    |
|-----------|-------|--------|---------|---------|
| frequency | 20    | 20000  | 440     | Hz      |
| cutoff    | 20    | 20000  | 8000    | Hz      |
| resonance | 0     | 1      | 0.3     | ratio   |
| attack    | 0.001 | 10     | 0.01    | seconds |
| decay     | 0.001 | 30     | 1.0     | seconds |
| custom0-4 | 0     | 1      | 0.5     | norm    |

---

## 5. SynthDef Requirements

### 5.1 Generator SynthDefs

Generators MUST read modulated params from buses:

```supercollider
SynthDef(\myGenerator, { |out,
    freqBus, cutoffBus, resBus, attackBus, decayBus,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    /* other non-modulated params */|

    var freq = In.kr(freqBus);
    var cutoff = In.kr(cutoffBus);
    var res = In.kr(resBus);
    var attack = In.kr(attackBus);
    var decay = In.kr(decayBus);
    var custom0 = In.kr(customBus0);
    // ... etc

    // Generate sound using these values
    var sig = /* synthesis */;

    Out.ar(out, sig);
}).add;
```

### 5.2 FX SynthDefs

FX synths MUST read modulated params from buses:

```supercollider
SynthDef(\heat, { |out, in, bypassBus, driveBus, mixBus|
    var drive = In.kr(driveBus);
    var mix = In.kr(mixBus);
    var bypass = In.kr(bypassBus);
    // ... apply heat effect
}).add;
```

### 5.3 Channel Strip SynthDefs

```supercollider
SynthDef(\channelStrip, { |in, out, echoBus, verbBus, panBus, /* ... */|
    var echoSend = In.kr(echoBus);
    var verbSend = In.kr(verbBus);
    var pan = In.kr(panBus);
    // ... apply channel processing
}).add;
```

---

## 6. OSC Interface

### 6.1 Base Value Updates (Python → SC)

All UI knob changes go through these endpoints:

```
/noise/bus/base [targetKey, value]
  - Sets base value for any target
  - Example: /noise/bus/base gen_1_cutoff 0.75

/noise/bus/base/batch [key1, val1, key2, val2, ...]
  - Batch update for efficiency
```

### 6.2 Route Operations (Python → SC)

```
/noise/bus/route/set [sourceKey, targetKey, depth, amount, offset, polarity, invert]
  - Add or update a modulation route
  - sourceKey: "modBus_0" through "modBus_15"
  - targetKey: any valid target key

/noise/bus/route/remove [sourceKey, targetKey]
  - Remove a specific route

/noise/bus/route/clear [targetKey]
  - Clear all routes to a target (or all if targetKey omitted)
```

### 6.3 Boid Operations (Python → SC)

```
/noise/boid/enable [0|1]
  - Enable/disable boid modulation globally

/noise/boid/offsets [busIndex1, offset1, busIndex2, offset2, ...]
  - Complete snapshot of all boid offsets
  - busIndex is the unified bus index

/noise/boid/clear
  - Zero all boid offsets
```

### 6.4 Value Stream (SC → Python)

```
/noise/bus/values [key1, val1, key2, val2, ...]
  - Sent at 20Hz for UI feedback
  - Only includes targets with active modulation
```

---

## 7. Migration Plan

### Phase 1: Expand Bus Unification (1-2 days)
1. Add generator param targets (40 buses) to bus_unification.scd
2. Add custom param targets (40 buses) to bus_unification.scd
3. Update ~targetMeta with proper ranges for all new targets
4. Test bus allocation succeeds

### Phase 2: Update Generator SynthDefs (2-3 days)
1. Modify all generator SynthDefs to read from buses
2. Update generator startup code to pass bus indices
3. Test each generator manually
4. Verify existing presets still work

### Phase 3: Update Python UI (1-2 days)
1. Add new OSC endpoint usage for generator params
2. Route all generator knob changes through /noise/bus/base
3. Update mod routing state to use unified target keys
4. Test UI responsiveness

### Phase 4: Remove Legacy Systems (1 day)
1. Remove mod_apply.scd passthrough synths
2. Remove ext_mod.scd apply task (keep value stream temporarily)
3. Remove duplicate OSCdef handlers
4. Clean up dead code

### Phase 5: Testing & Polish (1-2 days)
1. Full regression test of all modulation
2. Performance profiling (should be faster)
3. Edge case testing (rapid UI changes, etc.)
4. Documentation updates

---

## 8. Data Structures

### 8.1 ~targetMeta (Dictionary)

```supercollider
~targetMeta[targetKey] = (
    busIndex: Integer,      // Unified bus index
    min: Float,             // Parameter minimum
    max: Float,             // Parameter maximum
    default: Float,         // Default value (normalized 0-1 for most)
    curve: Symbol,          // \lin, \exp, \log (for UI display)
    unit: String            // "Hz", "s", "dB", etc.
);
```

### 8.2 ~modTargetState (Dictionary)

```supercollider
~modTargetState[targetKey] = (
    bus: Bus,               // Control bus object
    baseValue: Float,       // Current base value (denormalized)
    lastModSum: Float       // Last modulation sum (for delta detection)
);
```

### 8.3 ~modRoutes (Dictionary)

```supercollider
~modRoutes[targetKey] = List[
    (
        sourceKey: Symbol,  // e.g., \modBus_0
        depth: Float,       // 0-1
        amount: Float,      // 0-1
        offset: Float,      // -1 to +1
        polarity: Integer,  // 0=bipolar, 1=uni+, 2=uni-
        invert: Integer     // 0=normal, 1=invert
    ),
    // ... more routes
];
```

### 8.4 ~boidOffsets (Array)

```supercollider
~boidOffsets = Array[151];  // Indexed by (busIndex - baseIndex)
                            // Values in range -1 to +1 (already scaled by depth)
```

### 8.5 ~boidScales (Dictionary)

```supercollider
~boidScales[targetKey] = Float;  // 0-1, how much boid affects this param
                                 // Default 0.5 for most, 0 to disable
```

---

## 9. Performance Considerations

### 9.1 Current Cost
- 40 modApply synths (always running)
- ext_mod 500Hz Task
- bus_unification 500Hz Task
- Total: ~40 synths + 2 tasks

### 9.2 New Cost
- 0 modApply synths (removed)
- 1 unified 500Hz Task
- Total: 0 synths + 1 task

### 9.3 Memory
- ~151 control buses (cheap)
- Dictionary lookups (fast)
- No synth node overhead

---

## 10. Backward Compatibility

### 10.1 Python UI Changes Required

The Python UI must be updated to:
1. Send base values via `/noise/bus/base` instead of direct param OSC
2. Use unified target keys for mod routing
3. Handle new value stream format

### 10.2 Preset Compatibility

Existing presets should work if:
1. Generator param names map to new target keys
2. Route target strings are converted on load

### 10.3 Deprecation Timeline

| Phase | Legacy System | Status |
|-------|---------------|--------|
| Phase 1-3 | mod_apply.scd | Running in parallel |
| Phase 4 | mod_apply.scd | Removed |
| Phase 1-3 | ext_mod.scd | Running in parallel |
| Phase 4 | ext_mod.scd | Removed |

---

## 11. Testing Checklist

### 11.1 Generator Modulation
- [ ] LFO → generator cutoff
- [ ] Multiple sources → same target
- [ ] Route add/remove/update
- [ ] UI knob + modulation simultaneously
- [ ] Preset load with active routes

### 11.2 Extended Modulation
- [ ] Mod slot P1-P4 modulation
- [ ] Channel send modulation
- [ ] Channel pan modulation
- [ ] FX parameter modulation
- [ ] Cross-mod (mod1 → mod2 params)

### 11.3 Boid Integration
- [ ] Boid enable/disable
- [ ] Boid + mod matrix simultaneously
- [ ] Per-parameter boid scales
- [ ] Zone enable/disable

### 11.4 Performance
- [ ] 8 generators, full mod matrix, boids = still smooth
- [ ] No audio glitches during route changes
- [ ] UI responsive during heavy modulation

---

## 12. Open Questions

1. **Mod source expansion**: Should we support more than 16 mod buses?
2. **Audio-rate modulation**: Should some params support audio-rate mod?
3. **Mod visualization**: How to show modulation depth in UI efficiently?
4. **Preset format**: Do we need a migration script for old presets?

---

## Appendix A: Current File Structure

```
supercollider/core/
├── bus_unification.scd      # New unified system (expand this)
├── bus_unification_osc.scd  # OSC handlers for unified system
├── mod_apply.scd            # Legacy - REMOVE in Phase 4
├── mod_routing.scd          # Legacy OSC handlers - REMOVE in Phase 4
├── ext_mod.scd              # Legacy extended mod - REMOVE in Phase 4
├── ext_mod_osc.scd          # Bridge layer - REMOVE in Phase 4
└── mod_snapshot.scd         # Keep - used by unified system
```

---

## Appendix B: Example Implementation

See `bus_unification.scd` for the current implementation pattern. The Phase 1 expansion should follow the same structure for generator params.
