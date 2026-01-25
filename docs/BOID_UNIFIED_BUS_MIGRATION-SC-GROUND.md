# SuperCollider Unified 149-Bus Boid Modulation - Implementation Spec

## Overview

Implement the SuperCollider side of a **149-control-bus** boid modulation system. Python sends additive offsets via OSC; SC maintains canonical state and writes effective values to buses.

**Core formula:** `effective = clamp(base + offset, min, max)`

**No drift allowed:** Never read current bus value as input to calculations.

---

## File Structure

Create a single file: `unified_boids.scd`

This file should be loadable via `"unified_boids.scd".load` and expose all functionality through environment variables (`~variableName`).

---

## Phase 1: Constants & Variables

### Constants
```supercollider
~UNIFIED_BUS_COUNT = 149;
~APPLY_INTERVAL_SEC = 0.03;  // 30ms tick rate
```

### Runtime Variables (all must be declared)
```supercollider
~unifiedBuses = nil;           // Bus object (149 channels)
~unifiedBusBase = nil;         // Int: absolute starting bus index
~targetMetaByIndex = nil;      // Array[149] of metadata entries
~targetMetaByKey = nil;        // Dictionary: Symbol -> metadata
~baseValues = nil;             // Array[149] of Float
~boidOffsets = nil;            // Array[149] of Float
~boidEnabled = false;          // Bool
~initialized = false;          // Bool
~applyTask = nil;              // Task reference
~applyInProgress = false;      // Reentrancy guard
~needsFollowUpApply = false;   // Flag for deferred apply
```

### Pending Update Buffers
```supercollider
~pendingBaseUpdates = nil;     // Dictionary: Int -> Float
~pendingOffsetUpdates = nil;   // Dictionary: Int -> Float
~pendingEnableState = nil;     // nil or Bool
~pendingClearOffsets = false;  // Bool flag
```

---

## Phase 2: Target Metadata

### Metadata Entry Structure
Each entry is an Event with keys: `\targetIndex`, `\key`, `\min`, `\max`, `\default`

### Target Layout (149 total)

#### Indices 0-39: Generator Core (8 slots × 5 params)
For slot `s` (1-8), base index = `(s-1) * 5`:
| Offset | Key Pattern | Min | Max | Default |
|--------|-------------|-----|-----|---------|
| +0 | `\gen_N_freq` | 20.0 | 20000.0 | 440.0 |
| +1 | `\gen_N_cutoff` | 20.0 | 20000.0 | 5000.0 |
| +2 | `\gen_N_res` | 0.0 | 1.0 | 0.5 |
| +3 | `\gen_N_attack` | 0.0001 | 10.0 | 0.01 |
| +4 | `\gen_N_decay` | 0.0001 | 10.0 | 0.5 |

**Example:** Slot 3 → indices 10-14 → keys `\gen_3_freq`, `\gen_3_cutoff`, etc.

#### Indices 40-79: Generator Custom (8 slots × 5 params)
For slot `s` (1-8), base index = `40 + (s-1) * 5`:
| Offset | Key Pattern | Min | Max | Default |
|--------|-------------|-----|-----|---------|
| +0 | `\gen_N_custom0` | 0.0 | 1.0 | 0.5 |
| +1 | `\gen_N_custom1` | 0.0 | 1.0 | 0.5 |
| +2 | `\gen_N_custom2` | 0.0 | 1.0 | 0.5 |
| +3 | `\gen_N_custom3` | 0.0 | 1.0 | 0.5 |
| +4 | `\gen_N_custom4` | 0.0 | 1.0 | 0.5 |

#### Indices 80-107: Mod Slots (4 slots × 7 params)
For mod slot `m` (1-4), base index = `80 + (m-1) * 7`:
| Offset | Key Pattern | Min | Max | Default |
|--------|-------------|-----|-----|---------|
| +0 | `\mod_N_p0` | 0.0 | 1.0 | 0.5 |
| +1 | `\mod_N_p1` | 0.0 | 1.0 | 0.5 |
| +2 | `\mod_N_p2` | 0.0 | 1.0 | 0.5 |
| +3 | `\mod_N_p3` | 0.0 | 1.0 | 0.5 |
| +4 | `\mod_N_p4` | 0.0 | 1.0 | 0.5 |
| +5 | `\mod_N_p5` | 0.0 | 1.0 | 0.5 |
| +6 | `\mod_N_p6` | 0.0 | 1.0 | 0.5 |

#### Indices 108-131: Channels (8 channels × 3 params)
For channel `c` (1-8), base index = `108 + (c-1) * 3`:
| Offset | Key Pattern | Min | Max | Default |
|--------|-------------|-----|-----|---------|
| +0 | `\chan_N_echo` | 0.0 | 1.0 | 0.0 |
| +1 | `\chan_N_verb` | 0.0 | 1.0 | 0.0 |
| +2 | `\chan_N_pan` | -1.0 | 1.0 | 0.0 |

#### Indices 132-148: FX Parameters (17 total)
| Index | Key | Min | Max | Default |
|-------|-----|-----|-----|---------|
| 132 | `\fx_heat_drive` | 0.0 | 1.0 | 0.0 |
| 133 | `\fx_echo_time` | 0.01 | 2.0 | 0.3 |
| 134 | `\fx_echo_feedback` | 0.0 | 0.95 | 0.3 |
| 135 | `\fx_echo_tone` | 0.0 | 1.0 | 0.5 |
| 136 | `\fx_echo_wow` | 0.0 | 1.0 | 0.0 |
| 137 | `\fx_echo_spring` | 0.0 | 1.0 | 0.0 |
| 138 | `\fx_echo_verbSend` | 0.0 | 1.0 | 0.0 |
| 139 | `\fx_reverb_size` | 0.0 | 1.0 | 0.5 |
| 140 | `\fx_reverb_decay` | 0.0 | 1.0 | 0.5 |
| 141 | `\fx_reverb_tone` | 0.0 | 1.0 | 0.5 |
| 142 | `\fx_dualFilter_drive` | 0.0 | 1.0 | 0.0 |
| 143 | `\fx_dualFilter_freq1` | 20.0 | 20000.0 | 500.0 |
| 144 | `\fx_dualFilter_freq2` | 20.0 | 20000.0 | 2000.0 |
| 145 | `\fx_dualFilter_reso1` | 0.0 | 1.0 | 0.5 |
| 146 | `\fx_dualFilter_reso2` | 0.0 | 1.0 | 0.5 |
| 147 | `\fx_dualFilter_syncAmt` | 0.0 | 1.0 | 0.0 |
| 148 | `\fx_dualFilter_harmonics` | 0.0 | 1.0 | 0.5 |

### Implementation: `~buildTargetMetadata`

Create a function that:
1. Initializes `~targetMetaByIndex = Array.newClear(149)`
2. Initializes `~targetMetaByKey = Dictionary.new`
3. Loops through all 149 indices, creating metadata Events
4. Stores each entry in both the array and dictionary

```supercollider
~buildTargetMetadata = {
    ~targetMetaByIndex = Array.newClear(149);
    ~targetMetaByKey = Dictionary.new;
    
    // Helper to add entry
    var addMeta = { |idx, key, min, max, default|
        var entry = (
            targetIndex: idx,
            key: key,
            min: min,
            max: max,
            default: default
        );
        ~targetMetaByIndex[idx] = entry;
        ~targetMetaByKey[key] = entry;
    };
    
    // Gen Core (0-39)
    8.do { |s|
        var slot = s + 1;
        var base = s * 5;
        addMeta.(base + 0, ("gen_" ++ slot ++ "_freq").asSymbol, 20.0, 20000.0, 440.0);
        addMeta.(base + 1, ("gen_" ++ slot ++ "_cutoff").asSymbol, 20.0, 20000.0, 5000.0);
        addMeta.(base + 2, ("gen_" ++ slot ++ "_res").asSymbol, 0.0, 1.0, 0.5);
        addMeta.(base + 3, ("gen_" ++ slot ++ "_attack").asSymbol, 0.0001, 10.0, 0.01);
        addMeta.(base + 4, ("gen_" ++ slot ++ "_decay").asSymbol, 0.0001, 10.0, 0.5);
    };
    
    // Gen Custom (40-79)
    8.do { |s|
        var slot = s + 1;
        var base = 40 + (s * 5);
        5.do { |p|
            addMeta.(base + p, ("gen_" ++ slot ++ "_custom" ++ p).asSymbol, 0.0, 1.0, 0.5);
        };
    };
    
    // Mod Slots (80-107)
    4.do { |m|
        var slot = m + 1;
        var base = 80 + (m * 7);
        7.do { |p|
            addMeta.(base + p, ("mod_" ++ slot ++ "_p" ++ p).asSymbol, 0.0, 1.0, 0.5);
        };
    };
    
    // Channels (108-131)
    8.do { |c|
        var chan = c + 1;
        var base = 108 + (c * 3);
        addMeta.(base + 0, ("chan_" ++ chan ++ "_echo").asSymbol, 0.0, 1.0, 0.0);
        addMeta.(base + 1, ("chan_" ++ chan ++ "_verb").asSymbol, 0.0, 1.0, 0.0);
        addMeta.(base + 2, ("chan_" ++ chan ++ "_pan").asSymbol, -1.0, 1.0, 0.0);
    };
    
    // FX (132-148) - add each explicitly
    addMeta.(132, \fx_heat_drive, 0.0, 1.0, 0.0);
    addMeta.(133, \fx_echo_time, 0.01, 2.0, 0.3);
    addMeta.(134, \fx_echo_feedback, 0.0, 0.95, 0.3);
    addMeta.(135, \fx_echo_tone, 0.0, 1.0, 0.5);
    addMeta.(136, \fx_echo_wow, 0.0, 1.0, 0.0);
    addMeta.(137, \fx_echo_spring, 0.0, 1.0, 0.0);
    addMeta.(138, \fx_echo_verbSend, 0.0, 1.0, 0.0);
    addMeta.(139, \fx_reverb_size, 0.0, 1.0, 0.5);
    addMeta.(140, \fx_reverb_decay, 0.0, 1.0, 0.5);
    addMeta.(141, \fx_reverb_tone, 0.0, 1.0, 0.5);
    addMeta.(142, \fx_dualFilter_drive, 0.0, 1.0, 0.0);
    addMeta.(143, \fx_dualFilter_freq1, 20.0, 20000.0, 500.0);
    addMeta.(144, \fx_dualFilter_freq2, 20.0, 20000.0, 2000.0);
    addMeta.(145, \fx_dualFilter_reso1, 0.0, 1.0, 0.5);
    addMeta.(146, \fx_dualFilter_reso2, 0.0, 1.0, 0.5);
    addMeta.(147, \fx_dualFilter_syncAmt, 0.0, 1.0, 0.0);
    addMeta.(148, \fx_dualFilter_harmonics, 0.0, 1.0, 0.5);
    
    "Built metadata for % targets".format(~targetMetaByIndex.size).postln;
};
```

---

## Phase 3: Helper Functions

### `~isFinite` - Check for valid float
```supercollider
~isFinite = { |v|
    v.isNaN.not and: { v.isInfinite.not }
};
```

### `~normalizeTargetIndex` - Convert to valid 0-148 index
```supercollider
~normalizeTargetIndex = { |x|
    case
    { x.isInteger and: { (x >= 0) and: { x <= 148 } } } { x }
    { ~initialized and: { x.isInteger } and: {
        (x >= ~unifiedBusBase) and: { x <= (~unifiedBusBase + 148) }
    } } { x - ~unifiedBusBase }
    { nil }  // Invalid
};
```

### `~getAbsoluteBusIndex` - Get actual bus index
```supercollider
~getAbsoluteBusIndex = { |targetIndex|
    ~unifiedBusBase + targetIndex
};
```

---

## Phase 4: Apply Function

### `~applyOnce` - Core tick function

**CRITICAL:** This is the single source of truth for bus writes.

```supercollider
~applyOnce = {
    // Step 0: Guard - must be initialized
    if(~initialized.not) { ^nil };
    
    // Step 1: Reentrancy guard
    if(~applyInProgress) {
        ~needsFollowUpApply = true;
        ^nil
    };
    ~applyInProgress = true;
    
    // Step 2: Drain pending updates
    
    // 2a: Handle pending clear flag
    if(~pendingClearOffsets) {
        149.do { |i| ~boidOffsets[i] = 0.0 };
        ~pendingOffsetUpdates.clear;
        ~pendingClearOffsets = false;
    };
    
    // 2b: Apply pending base updates
    ~pendingBaseUpdates.keysValuesDo { |i, v|
        if(~isFinite.(v)) {
            var meta = ~targetMetaByIndex[i];
            if(meta.notNil) {
                ~baseValues[i] = v.clip(meta[\min], meta[\max]);
            };
        } {
            "WARNING: Non-finite base value rejected for index %".format(i).postln;
        };
    };
    ~pendingBaseUpdates.clear;
    
    // 2c: Apply pending offset updates
    ~pendingOffsetUpdates.keysValuesDo { |i, off|
        if(~isFinite.(off)) {
            ~boidOffsets[i] = off;
        } {
            ~boidOffsets[i] = 0.0;
            "WARNING: Non-finite offset treated as 0.0 for index %".format(i).postln;
        };
    };
    ~pendingOffsetUpdates.clear;
    
    // Step 3: Repair canonical arrays (safety net)
    149.do { |i|
        var meta = ~targetMetaByIndex[i];
        if(meta.notNil) {
            if(~isFinite.(~baseValues[i]).not) {
                ~baseValues[i] = meta[\default].clip(meta[\min], meta[\max]);
                "WARNING: Repaired non-finite baseValues[%]".format(i).postln;
            };
            if(~isFinite.(~boidOffsets[i]).not) {
                ~boidOffsets[i] = 0.0;
                "WARNING: Repaired non-finite boidOffsets[%]".format(i).postln;
            };
        };
    };
    
    // Step 4: Compute and write all 149 buses
    149.do { |i|
        var meta = ~targetMetaByIndex[i];
        if(meta.notNil) {
            var base = ~baseValues[i];
            var off = if(~boidEnabled) { ~boidOffsets[i] } { 0.0 };
            var effective = (base + off).clip(meta[\min], meta[\max]);
            ~unifiedBuses.setAt(i, effective);
        };
    };
    
    ~applyInProgress = false;
    
    // Handle follow-up apply if requested during this tick
    if(~needsFollowUpApply) {
        ~needsFollowUpApply = false;
        ~applyOnce.value;
    };
};
```

---

## Phase 5: Base Value API

### `~setBaseValue` - Set single base value
```supercollider
~setBaseValue = { |targetIndex, value|
    var i = ~normalizeTargetIndex.(targetIndex);
    if(i.notNil) {
        if(~isFinite.(value)) {
            ~pendingBaseUpdates[i] = value;
        } {
            "WARNING: Rejected non-finite base value for index %".format(i).postln;
        };
    } {
        "WARNING: Invalid target index %".format(targetIndex).postln;
    };
};
```

### `~setBaseValues` - Set multiple base values
```supercollider
~setBaseValues = { |pairs|
    // pairs is flat array: [idx1, val1, idx2, val2, ...]
    pairs.pairsDo { |idx, val|
        ~setBaseValue.(idx, val);
    };
};
```

### `~setBaseByKey` - Set base value by key symbol
```supercollider
~setBaseByKey = { |key, value|
    var meta = ~targetMetaByKey[key];
    if(meta.notNil) {
        ~setBaseValue.(meta[\targetIndex], value);
    } {
        "WARNING: Unknown target key %".format(key).postln;
    };
};
```

---

## Phase 6: OSC Handlers

### `/noise/boid/offsets` - Receive offset pairs
```supercollider
OSCdef(\boidOffsets, { |msg|
    var pairs = msg[1..];
    
    // Ignore if payload too short
    if(pairs.size < 2) { ^nil };
    
    // Process pairs (ignore odd trailing element)
    (pairs.size div: 2).do { |pairIdx|
        var rawIndex = pairs[pairIdx * 2];
        var offset = pairs[(pairIdx * 2) + 1];
        var i;
        
        // Normalize index
        if(~initialized) {
            i = ~normalizeTargetIndex.(rawIndex);
        } {
            // Before init, only accept 0-148 form
            if(rawIndex.isInteger and: { (rawIndex >= 0) and: { rawIndex <= 148 } }) {
                i = rawIndex;
            } { i = nil };
        };
        
        // Store if valid
        if(i.notNil) {
            if(~isFinite.(offset)) {
                ~pendingOffsetUpdates[i] = offset;
            } {
                ~pendingOffsetUpdates[i] = 0.0;
                "WARNING: Non-finite offset for index % treated as 0.0".format(i).postln;
            };
        };
    };
}, '/noise/boid/offsets');
```

### `/noise/boid/enable` - Enable/disable boids
```supercollider
OSCdef(\boidEnable, { |msg|
    var state = msg[1].asInteger;
    var enableFlag = (state == 1);
    
    if(~initialized.not) {
        // Buffer for later
        ~pendingEnableState = enableFlag;
        "Buffered boid enable state: %".format(enableFlag).postln;
    } {
        if(enableFlag) {
            // Enable
            ~boidEnabled = true;
            "Boids ENABLED".postln;
        } {
            // Disable - atomic: clear offsets + pending + set flag
            ~boidEnabled = false;
            149.do { |i| ~boidOffsets[i] = 0.0 };
            ~pendingOffsetUpdates.clear;
            "Boids DISABLED (offsets cleared)".postln;
        };
        // Immediate apply
        ~applyOnce.value;
    };
}, '/noise/boid/enable');
```

### `/noise/boid/clear` - Clear all offsets
```supercollider
OSCdef(\boidClear, { |msg|
    if(~initialized.not) {
        ~pendingClearOffsets = true;
        "Buffered boid clear command".postln;
    } {
        // Clear immediately
        149.do { |i| ~boidOffsets[i] = 0.0 };
        ~pendingOffsetUpdates.clear;
        "Boid offsets CLEARED".postln;
        // Immediate apply
        ~applyOnce.value;
    };
}, '/noise/boid/clear');
```

---

## Phase 7: Initialization Sequence

### `~initUnifiedBoids` - Main init function

**CRITICAL:** Steps MUST execute in this exact order. No tick before completion.

```supercollider
~initUnifiedBoids = {
    // Prevent double-init
    if(~initialized) {
        "Already initialized - call ~shutdownUnifiedBoids first".postln;
        ^nil
    };
    
    // Step 1: Allocate buses
    ~unifiedBuses = Bus.control(s, 149);
    if(~unifiedBuses.isNil) {
        "ERROR: Failed to allocate 149 control buses".postln;
        ^nil
    };
    
    // Step 2: Derive base index
    ~unifiedBusBase = ~unifiedBuses.index;
    
    // Step 3: Build metadata
    ~buildTargetMetadata.value;
    
    // Step 4: Initialize canonical arrays
    ~baseValues = Array.fill(149, { |i|
        var meta = ~targetMetaByIndex[i];
        meta[\default].clip(meta[\min], meta[\max])
    });
    ~boidOffsets = Array.fill(149, { 0.0 });
    
    // Step 5: Initialize pending buffers
    ~pendingBaseUpdates = Dictionary.new;
    ~pendingOffsetUpdates = Dictionary.new;
    ~pendingEnableState = nil;
    ~pendingClearOffsets = false;
    ~needsFollowUpApply = false;
    
    // Step 6: Mark initialized
    ~initialized = true;
    ~boidEnabled = false;
    
    // Step 7: Apply buffered pre-init commands
    if(~pendingClearOffsets) {
        149.do { |i| ~boidOffsets[i] = 0.0 };
        ~pendingClearOffsets = false;
    };
    
    ~pendingOffsetUpdates.keysValuesDo { |i, off|
        if(~isFinite.(off)) {
            ~boidOffsets[i] = off;
        } {
            ~boidOffsets[i] = 0.0;
        };
    };
    ~pendingOffsetUpdates.clear;
    
    if(~pendingEnableState.notNil) {
        ~boidEnabled = ~pendingEnableState;
        ~pendingEnableState = nil;
    };
    
    // Step 8: Initial apply (write all buses)
    ~applyOnce.value;
    
    // Step 9: Start periodic apply task
    ~applyTask = Task({
        loop {
            ~APPLY_INTERVAL_SEC.wait;
            ~applyOnce.value;
        };
    }).play(SystemClock);
    
    "=== Unified Boid System Initialized ===".postln;
    "  Bus count: %".format(149).postln;
    "  Bus base: %".format(~unifiedBusBase).postln;
    "  Tick interval: %s".format(~APPLY_INTERVAL_SEC).postln;
    "  Boids enabled: %".format(~boidEnabled).postln;
};
```

### `~shutdownUnifiedBoids` - Cleanup function
```supercollider
~shutdownUnifiedBoids = {
    // Stop task
    if(~applyTask.notNil) {
        ~applyTask.stop;
        ~applyTask = nil;
    };
    
    // Free buses
    if(~unifiedBuses.notNil) {
        ~unifiedBuses.free;
        ~unifiedBuses = nil;
    };
    
    // Clear OSCdefs
    OSCdef(\boidOffsets).free;
    OSCdef(\boidEnable).free;
    OSCdef(\boidClear).free;
    
    // Reset state
    ~initialized = false;
    ~boidEnabled = false;
    ~unifiedBusBase = nil;
    
    "Unified Boid System shutdown complete".postln;
};
```

---

## Phase 8: Debug/Query Functions

### `~getBoidStatus` - Return current state
```supercollider
~getBoidStatus = {
    (
        initialized: ~initialized,
        enabled: ~boidEnabled,
        busBase: ~unifiedBusBase,
        busCount: 149,
        tickInterval: ~APPLY_INTERVAL_SEC
    )
};
```

### `~getTargetInfo` - Query single target
```supercollider
~getTargetInfo = { |indexOrKey|
    var meta, i;
    
    if(indexOrKey.isKindOf(Symbol)) {
        meta = ~targetMetaByKey[indexOrKey];
    } {
        i = ~normalizeTargetIndex.(indexOrKey);
        if(i.notNil) { meta = ~targetMetaByIndex[i] };
    };
    
    if(meta.notNil) {
        (
            targetIndex: meta[\targetIndex],
            key: meta[\key],
            min: meta[\min],
            max: meta[\max],
            default: meta[\default],
            absoluteBus: if(~unifiedBusBase.notNil) { ~unifiedBusBase + meta[\targetIndex] } { nil },
            currentBase: if(~baseValues.notNil) { ~baseValues[meta[\targetIndex]] } { nil },
            currentOffset: if(~boidOffsets.notNil) { ~boidOffsets[meta[\targetIndex]] } { nil }
        )
    } {
        "Unknown target: %".format(indexOrKey).postln;
        nil
    }
};
```

### `~dumpAllTargets` - Print all 149 mappings
```supercollider
~dumpAllTargets = {
    "=== All 149 Target Mappings ===".postln;
    149.do { |i|
        var meta = ~targetMetaByIndex[i];
        "  [%] % : % - % (default %)".format(
            i.asString.padLeft(3),
            meta[\key],
            meta[\min],
            meta[\max],
            meta[\default]
        ).postln;
    };
};
```

---

## Verification Tests

After implementation, run these tests:

### Test 1: Metadata Spot Checks
```supercollider
// Should all return true
~targetMetaByIndex[0][\key] == \gen_1_freq;
~targetMetaByIndex[39][\key] == \gen_8_decay;
~targetMetaByIndex[40][\key] == \gen_1_custom0;
~targetMetaByIndex[79][\key] == \gen_8_custom4;
~targetMetaByIndex[80][\key] == \mod_1_p0;
~targetMetaByIndex[107][\key] == \mod_4_p6;
~targetMetaByIndex[108][\key] == \chan_1_echo;
~targetMetaByIndex[131][\key] == \chan_8_pan;
~targetMetaByIndex[132][\key] == \fx_heat_drive;
~targetMetaByIndex[148][\key] == \fx_dualFilter_harmonics;
```

### Test 2: No Drift
```supercollider
// Set base, enable boids, set offset, wait, verify no accumulation
~setBaseValue.(0, 440.0);
~boidEnabled = true;
~pendingOffsetUpdates[0] = 10.0;
// After 5+ ticks, bus 0 should still read 450.0 (not 440 + 10*N)
```

### Test 3: Atomic Disable
```supercollider
// With offsets active, disable should clear them
~boidEnabled = true;
~boidOffsets[0] = 100.0;
// Send: NetAddr.localAddr.sendMsg('/noise/boid/enable', 0);
// Verify: ~boidOffsets[0] == 0.0 and ~boidEnabled == false
```

### Test 4: Index Normalization
```supercollider
// Both should work after init:
~normalizeTargetIndex.(0);  // Returns 0
~normalizeTargetIndex.(~unifiedBusBase + 5);  // Returns 5
~normalizeTargetIndex.(-1);  // Returns nil
~normalizeTargetIndex.(200);  // Returns nil (unless busBase makes it valid)
```

---

## Usage Example

```supercollider
// Boot server first
s.waitForBoot {
    // Load the boid system
    "unified_boids.scd".load;
    
    // Initialize
    ~initUnifiedBoids.value;
    
    // Check status
    ~getBoidStatus.value.postln;
    
    // Query a target
    ~getTargetInfo.(\gen_1_freq).postln;
    ~getTargetInfo.(132).postln;
    
    // Set a base value
    ~setBaseValue.(0, 880.0);  // gen_1_freq
    ~setBaseByKey.(\fx_echo_time, 0.5);
    
    // Enable boids (from Python or manually)
    NetAddr.localAddr.sendMsg('/noise/boid/enable', 1);
    
    // Send offsets (from Python)
    NetAddr.localAddr.sendMsg('/noise/boid/offsets', 0, 50.0, 1, -100.0);
    
    // Clear offsets
    NetAddr.localAddr.sendMsg('/noise/boid/clear');
    
    // Shutdown when done
    // ~shutdownUnifiedBoids.value;
};
```

---

## Summary Checklist

- [ ] Constants defined (`~UNIFIED_BUS_COUNT`, `~APPLY_INTERVAL_SEC`)
- [ ] All runtime variables declared
- [ ] All pending buffers declared
- [ ] `~buildTargetMetadata` creates 149 entries with correct keys/ranges/defaults
- [ ] `~isFinite` helper
- [ ] `~normalizeTargetIndex` helper (handles 0-148 and absolute forms)
- [ ] `~applyOnce` with all 4 steps + reentrancy guard
- [ ] `~setBaseValue` / `~setBaseValues` / `~setBaseByKey` APIs
- [ ] OSCdef for `/noise/boid/offsets`
- [ ] OSCdef for `/noise/boid/enable`
- [ ] OSCdef for `/noise/boid/clear`
- [ ] `~initUnifiedBoids` with correct 9-step order
- [ ] `~shutdownUnifiedBoids` cleanup
- [ ] Debug functions (`~getBoidStatus`, `~getTargetInfo`, `~dumpAllTargets`)
- [ ] All verification tests pass
