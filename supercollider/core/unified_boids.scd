/*
 * Unified Boid Modulation System
 *
 * Implements the SuperCollider side of the 176-control-bus boid modulation system (v3).
 * Python sends additive offsets via OSC; SC maintains canonical state and writes
 * effective values to buses.
 *
 * Core formula: effective = clamp(base + offset, min, max)
 * No drift: Never read current bus value as input to calculations.
 *
 * v3 layout (176 targets - UI Refresh):
 * - 0-107: UNCHANGED (gen_core, gen_custom, mod_slots)
 * - 108-147: Channels (8 x 5: fx1, fx2, fx3, fx4, pan)
 * - 148-167: FX Slots (4 x 5: p1, p2, p3, p4, return)
 * - 168-175: Master Inserts (DualFilter 7 + Heat 1)
 *
 * Per: docs/BOID_UNIFIED_BUS_MIGRATION-SC-GROUND.md
 */

(
// ============================================================================
// Phase 1: Constants & Variables
// ============================================================================

~unifiedBusCount = 176;
~applyIntervalSec = 0.03;  // 30ms tick rate

// Runtime Variables
~unifiedBuses = nil;           // Bus object (176 channels - v3)
~unifiedBusBase = nil;         // Int: absolute starting bus index
~targetMetaByIndex = nil;      // Array[176] of metadata entries
~targetMetaByKey = nil;        // Dictionary: Symbol -> metadata
~baseValues = nil;             // Array[176] of Float
~boidOffsets = nil;            // Array[176] of Float
~boidEnabled = false;          // Bool
~boidInitialized = false;          // Bool
~boidApplyTask = nil;              // Task reference
~boidApplyInProgress = false;      // Reentrancy guard
~boidNeedsFollowUp = false;   // Flag for deferred apply

// Pending Update Buffers (initialized as empty Dicts so they're safe before init)
~boidPendingBase = Dictionary.new;
~boidPendingOffsets = Dictionary.new;
~boidPendingEnableState = nil;     // nil or Bool
~boidPendingClear = false;  // Bool flag

// ============================================================================
// Phase 2: Target Metadata
// ============================================================================

~buildTargetMetadata = {
    // Helper to add entry (var must be declared first in SC)
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

    ~targetMetaByIndex = Array.newClear(176);
    ~targetMetaByKey = Dictionary.new;

    // Gen Core (0-39): 8 slots x 5 params - UNCHANGED
    8.do { |s|
        var slot = s + 1;
        var base = s * 5;
        addMeta.(base + 0, ("gen_" ++ slot ++ "_freq").asSymbol, 20.0, 20000.0, 440.0);
        addMeta.(base + 1, ("gen_" ++ slot ++ "_cutoff").asSymbol, 20.0, 20000.0, 5000.0);
        addMeta.(base + 2, ("gen_" ++ slot ++ "_res").asSymbol, 0.0, 1.0, 0.5);
        addMeta.(base + 3, ("gen_" ++ slot ++ "_attack").asSymbol, 0.0001, 10.0, 0.01);
        addMeta.(base + 4, ("gen_" ++ slot ++ "_decay").asSymbol, 0.0001, 10.0, 0.5);
    };

    // Gen Custom (40-79): 8 slots x 5 params - UNCHANGED
    8.do { |s|
        var slot = s + 1;
        var base = 40 + (s * 5);
        5.do { |p|
            addMeta.(base + p, ("gen_" ++ slot ++ "_custom" ++ p).asSymbol, 0.0, 1.0, 0.5);
        };
    };

    // Mod Slots (80-107): 4 slots x 7 params - UNCHANGED
    4.do { |m|
        var slot = m + 1;
        var base = 80 + (m * 7);
        7.do { |p|
            addMeta.(base + p, ("mod_" ++ slot ++ "_p" ++ p).asSymbol, 0.0, 1.0, 0.5);
        };
    };

    // Channels (108-147): 8 channels x 5 params - v3 EXPANDED
    // New params: fx1, fx2, fx3, fx4, pan
    8.do { |c|
        var chan = c + 1;
        var base = 108 + (c * 5);
        addMeta.(base + 0, ("chan_" ++ chan ++ "_fx1").asSymbol, 0.0, 1.0, 0.0);
        addMeta.(base + 1, ("chan_" ++ chan ++ "_fx2").asSymbol, 0.0, 1.0, 0.0);
        addMeta.(base + 2, ("chan_" ++ chan ++ "_fx3").asSymbol, 0.0, 1.0, 0.0);
        addMeta.(base + 3, ("chan_" ++ chan ++ "_fx4").asSymbol, 0.0, 1.0, 0.0);
        addMeta.(base + 4, ("chan_" ++ chan ++ "_pan").asSymbol, -1.0, 1.0, 0.0);
    };

    // FX Slots (148-167): 4 slots x 5 params - v3 NEW
    // Params: p1, p2, p3, p4, return
    4.do { |s|
        var slot = s + 1;
        var base = 148 + (s * 5);
        addMeta.(base + 0, ("fx_slot" ++ slot ++ "_p1").asSymbol, 0.0, 1.0, 0.5);
        addMeta.(base + 1, ("fx_slot" ++ slot ++ "_p2").asSymbol, 0.0, 1.0, 0.5);
        addMeta.(base + 2, ("fx_slot" ++ slot ++ "_p3").asSymbol, 0.0, 1.0, 0.5);
        addMeta.(base + 3, ("fx_slot" ++ slot ++ "_p4").asSymbol, 0.0, 1.0, 0.5);
        addMeta.(base + 4, ("fx_slot" ++ slot ++ "_return").asSymbol, 0.0, 1.0, 0.5);
    };

    // Master Inserts (168-175): 8 params - v3 REORGANIZED
    // DualFilter (7 params) + Heat (1 param)
    addMeta.(168, \fx_fb_drive, 0.0, 1.0, 0.0);
    addMeta.(169, \fx_fb_freq1, 20.0, 20000.0, 500.0);
    addMeta.(170, \fx_fb_reso1, 0.0, 1.0, 0.5);
    addMeta.(171, \fx_fb_freq2, 20.0, 20000.0, 2000.0);
    addMeta.(172, \fx_fb_reso2, 0.0, 1.0, 0.5);
    addMeta.(173, \fx_fb_syncAmt, 0.0, 1.0, 0.0);
    addMeta.(174, \fx_fb_harmonics, 0.0, 7.0, 0.0);
    addMeta.(175, \fx_heat_drive, 0.0, 1.0, 0.0);

    "Built metadata for % targets".format(~targetMetaByIndex.size).postln;
};

// ============================================================================
// Phase 3: Helper Functions
// ============================================================================

~isFinite = { |v|
    v.isNaN.not and: { v.abs < inf }
};

~normalizeTargetIndex = { |x|
    case
    { x.isInteger and: { (x >= 0) and: { x <= 175 } } } { x }
    { ~boidInitialized and: { x.isInteger } and: {
        (x >= ~unifiedBusBase) and: { x <= (~unifiedBusBase + 175) }
    } } { x - ~unifiedBusBase }
    { nil }  // Invalid
};

~getAbsoluteBusIndex = { |targetIndex|
    ~unifiedBusBase + targetIndex
};

// ============================================================================
// Phase 4: Apply Function
// ============================================================================

~applyOnce = {
    // Step 0: Guard - must be initialized
    if(~boidInitialized.not) { nil } {

        // Step 1: Reentrancy guard
        if(~boidApplyInProgress) {
            ~boidNeedsFollowUp = true;
        } {
            ~boidApplyInProgress = true;

            // Step 2: Drain pending updates

            // 2a: Handle pending clear flag
            if(~boidPendingClear) {
                176.do { |i| ~boidOffsets[i] = 0.0 };
                ~boidPendingOffsets.clear;
                ~boidPendingClear = false;
            };

            // 2b: Apply pending base updates
            ~boidPendingBase.keysValuesDo { |i, v|
                if(~isFinite.(v)) {
                    var meta = ~targetMetaByIndex[i];
                    if(meta.notNil) {
                        ~baseValues[i] = v.clip(meta[\min], meta[\max]);
                    };
                } {
                    "WARNING: Non-finite base value rejected for index %".format(i).postln;
                };
            };
            ~boidPendingBase.clear;

            // 2c: Apply pending offset updates
            ~boidPendingOffsets.keysValuesDo { |i, off|
                if(~isFinite.(off)) {
                    ~boidOffsets[i] = off;
                } {
                    ~boidOffsets[i] = 0.0;
                    "WARNING: Non-finite offset treated as 0.0 for index %".format(i).postln;
                };
            };
            ~boidPendingOffsets.clear;

            // Step 3: Repair canonical arrays (safety net)
            176.do { |i|
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

            // Step 4: Compute and write all 176 buses
            176.do { |i|
                var meta = ~targetMetaByIndex[i];
                if(meta.notNil) {
                    var base = ~baseValues[i];
                    var off = if(~boidEnabled) { ~boidOffsets[i] } { 0.0 };
                    var effective = (base + off).clip(meta[\min], meta[\max]);
                    ~unifiedBuses.setAt(i, effective);
                };
            };

            ~boidApplyInProgress = false;

            // Handle follow-up apply if requested during this tick
            if(~boidNeedsFollowUp) {
                ~boidNeedsFollowUp = false;
                ~applyOnce.value;
            };
        };
    };
};

// ============================================================================
// Phase 5: Base Value API
// ============================================================================

~setBaseValue = { |targetIndex, value|
    var i = ~normalizeTargetIndex.(targetIndex);
    if(i.notNil) {
        if(~isFinite.(value)) {
            ~boidPendingBase[i] = value;
        } {
            "WARNING: Rejected non-finite base value for index %".format(i).postln;
        };
    } {
        "WARNING: Invalid target index %".format(targetIndex).postln;
    };
};

~setBaseValues = { |pairs|
    // pairs is flat array: [idx1, val1, idx2, val2, ...]
    pairs.pairsDo { |idx, val|
        ~setBaseValue.(idx, val);
    };
};

~setBaseByKey = { |key, value|
    var meta = ~targetMetaByKey[key];
    if(meta.notNil) {
        ~setBaseValue.(meta[\targetIndex], value);
    } {
        "WARNING: Unknown target key %".format(key).postln;
    };
};

// ============================================================================
// Phase 6: OSC Handlers
// ============================================================================

OSCdef(\boidOffsets, { |msg|
    var pairs = msg[1..];

    // Ignore if payload too short
    if(pairs.size >= 2) {
        // Process pairs (ignore odd trailing element)
        (pairs.size div: 2).do { |pairIdx|
            var rawIndex = pairs[pairIdx * 2];
            var offset = pairs[(pairIdx * 2) + 1];
            var i;

            // Normalize index
            if(~boidInitialized) {
                i = ~normalizeTargetIndex.(rawIndex);
            } {
                // Before init, only accept 0-175 form
                if(rawIndex.isInteger and: { (rawIndex >= 0) and: { rawIndex <= 175 } }) {
                    i = rawIndex;
                } { i = nil };
            };

            // Store if valid
            if(i.notNil) {
                if(~isFinite.(offset)) {
                    ~boidPendingOffsets[i] = offset;
                } {
                    ~boidPendingOffsets[i] = 0.0;
                    "WARNING: Non-finite offset for index % treated as 0.0".format(i).postln;
                };
            };
        };
    };
}, '/noise/boid/offsets');

OSCdef(\boidEnable, { |msg|
    var state = msg[1].asInteger;
    var enableFlag = (state == 1);

    if(~boidInitialized.not) {
        // Buffer for later
        ~boidPendingEnableState = enableFlag;
        "Buffered boid enable state: %".format(enableFlag).postln;
    } {
        if(enableFlag) {
            // Enable
            ~boidEnabled = true;
            "Boids ENABLED".postln;
        } {
            // Disable - atomic: clear offsets + pending + set flag
            ~boidEnabled = false;
            176.do { |i| ~boidOffsets[i] = 0.0 };
            ~boidPendingOffsets.clear;
            "Boids DISABLED (offsets cleared)".postln;
        };
        // Immediate apply
        ~applyOnce.value;
    };
}, '/noise/boid/enable');

OSCdef(\boidClear, { |msg|
    if(~boidInitialized.not) {
        ~boidPendingClear = true;
        "Buffered boid clear command".postln;
    } {
        // Clear immediately
        176.do { |i| ~boidOffsets[i] = 0.0 };
        ~boidPendingOffsets.clear;
        "Boid offsets CLEARED".postln;
        // Immediate apply
        ~applyOnce.value;
    };
}, '/noise/boid/clear');

// ============================================================================
// Phase 7: Initialization Sequence
// ============================================================================

~initUnifiedBoids = {
    // Prevent double-init
    if(~boidInitialized) {
        "Already initialized - call ~shutdownUnifiedBoids first".postln;
    } {
        // Step 1: Allocate buses
        ~unifiedBuses = Bus.control(s, 176);
        if(~unifiedBuses.isNil) {
            "ERROR: Failed to allocate 176 control buses".postln;
        } {
            // Step 2: Derive base index
            ~unifiedBusBase = ~unifiedBuses.index;

            // Step 3: Build metadata
            ~buildTargetMetadata.value;

            // Step 4: Initialize canonical arrays
            ~baseValues = Array.fill(176, { |i|
                var meta = ~targetMetaByIndex[i];
                meta[\default].clip(meta[\min], meta[\max])
            });
            ~boidOffsets = Array.fill(176, { 0.0 });

            // Step 5: Initialize pending buffers
            ~boidPendingBase = Dictionary.new;
            ~boidPendingOffsets = Dictionary.new;
            ~boidPendingEnableState = nil;
            ~boidPendingClear = false;
            ~boidNeedsFollowUp = false;

            // Step 6: Mark initialized
            ~boidInitialized = true;
            ~boidEnabled = false;

            // Step 7: Apply buffered pre-init commands
            if(~boidPendingClear) {
                176.do { |i| ~boidOffsets[i] = 0.0 };
                ~boidPendingClear = false;
            };

            ~boidPendingOffsets.keysValuesDo { |i, off|
                if(~isFinite.(off)) {
                    ~boidOffsets[i] = off;
                } {
                    ~boidOffsets[i] = 0.0;
                };
            };
            ~boidPendingOffsets.clear;

            if(~boidPendingEnableState.notNil) {
                ~boidEnabled = ~boidPendingEnableState;
                ~boidPendingEnableState = nil;
            };

            // Step 8: Initial apply (write all buses)
            ~applyOnce.value;

            // Step 9: Start periodic apply task
            ~boidApplyTask = Task({
                loop {
                    ~applyIntervalSec.wait;
                    ~applyOnce.value;
                };
            }).play(SystemClock);

            "=== Unified Boid System Initialized ===".postln;
            "  Bus count: %".format(176).postln;
            "  Bus base: %".format(~unifiedBusBase).postln;
            "  Tick interval: %s".format(~applyIntervalSec).postln;
            "  Boids enabled: %".format(~boidEnabled).postln;
        };
    };
};

~shutdownUnifiedBoids = {
    // Stop task
    if(~boidApplyTask.notNil) {
        ~boidApplyTask.stop;
        ~boidApplyTask = nil;
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
    ~boidInitialized = false;
    ~boidEnabled = false;
    ~unifiedBusBase = nil;

    "Unified Boid System shutdown complete".postln;
};

// ============================================================================
// Phase 8: Debug/Query Functions
// ============================================================================

~getBoidStatus = {
    (
        initialized: ~boidInitialized,
        enabled: ~boidEnabled,
        busBase: ~unifiedBusBase,
        busCount: 176,
        tickInterval: ~applyIntervalSec
    )
};

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

~dumpAllTargets = {
    "=== All 176 Target Mappings ===".postln;
    176.do { |i|
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

"unified_boids.scd loaded - call ~initUnifiedBoids.value to initialize".postln;
)
