/*
Bus Unification - Unified Parameter Control Architecture
Replaces ext_mod with bus-based modulation for all continuous parameters.

Problem solved:
- ext_mod cached base values at route creation, causing user knob changes to be overwritten
- Now: UI writes to base, modulation adds to base, synths read combined value from bus

Architecture:
- 71 control buses allocated contiguously at indices 1000-1070
- Single-writer: only apply tick writes to target buses
- Canonical base: one baseValue per target in ~modTargetState
- Bus-only read: SynthDefs read covered params from In.kr(bus) only

Bus Layout (71 total, indices 1000-1070):
| Category     | Count | Indices   | Parameters                                      |
|--------------|-------|-----------|------------------------------------------------|
| Mod Slots    | 28    | 1000-1027 | 4 slots x 7 params (P0-P6)                     |
| Channels     | 24    | 1028-1051 | 8 slots x 3 params (echoSend, verbSend, pan)   |
| FX: HEAT     | 2     | 1052-1053 | drive, mix                                      |
| FX: ECHO     | 6     | 1054-1059 | time, feedback, tone, wow, spring, verbSend     |
| FX: REVERB   | 3     | 1060-1062 | size, decay, tone                               |
| FX: DUAL_FLT | 8     | 1063-1070 | drive, freq1, freq2, reso1, reso2, syncAmt, harmonics, mix |

Mod Slot P0-P6 Mapping:
| P Index | LFO     | ARSeq+  | SauceOfGrav | Sloth   |
|---------|---------|---------|-------------|---------|
| P0      | rate    | rate    | rate        | ignored |
| P1      | shape   | atkA    | depth       | ignored |
| P2      | pattern | atkB    | gravity     | ignored |
| P3      | rotate  | atkC    | resonance   | ignored |
| P4      | waveA   | atkD    | excursion   | ignored |
| P5      | waveB   | relA    | calm        | ignored |
| P6      | waveC   | relB    | tension1    | ignored |
*/

~setupBusUnification = {
    "Setting up Bus Unification...".postln;

    // === BUS ALLOCATION ===
    // Allocate 71 contiguous control buses starting at index 1000
    ~unifiedBusBase = 1000;
    ~unifiedBusCount = 71;

    // Pre-allocate at specific indices (SC requires server to be booted)
    ~unifiedBuses = Bus.alloc(\control, s, ~unifiedBusCount);

    // If allocation didn't give us index 1000, log warning but continue
    if(~unifiedBuses.index != ~unifiedBusBase, {
        "WARNING: Bus allocation at % (wanted %)".format(~unifiedBuses.index, ~unifiedBusBase).postln;
        ~unifiedBusBase = ~unifiedBuses.index;  // Use actual allocated index
    });

    // === TARGET KEY DEFINITIONS ===
    // Maps human-readable keys to bus indices and metadata

    // ~targetMeta: targetKey -> {busIndex, min, max, default}
    ~targetMeta = Dictionary.new;

    // ~busRegistry: targetKey -> Bus object (for convenience)
    ~busRegistry = Dictionary.new;

    // === MOD SLOT BUSES (28 total: 4 slots x 7 params) ===
    // Indices 1000-1027
    4.do { |slotIdx|
        var slot = slotIdx + 1;  // 1-indexed
        7.do { |pIdx|
            var key = ("mod_%_p%").format(slot, pIdx).asSymbol;
            var busIdx = ~unifiedBusBase + (slotIdx * 7) + pIdx;
            ~targetMeta[key] = (
                busIndex: busIdx,
                min: 0.0,
                max: 1.0,
                default: 0.5
            );
        };
    };

    // === CHANNEL BUSES (24 total: 8 channels x 3 params) ===
    // Indices 1028-1051
    8.do { |chanIdx|
        var chan = chanIdx + 1;  // 1-indexed
        var baseIdx = ~unifiedBusBase + 28 + (chanIdx * 3);

        // echoSend
        ~targetMeta[("chan_%_echo").format(chan).asSymbol] = (
            busIndex: baseIdx,
            min: 0.0,
            max: 1.0,
            default: 0.0
        );
        // verbSend
        ~targetMeta[("chan_%_verb").format(chan).asSymbol] = (
            busIndex: baseIdx + 1,
            min: 0.0,
            max: 1.0,
            default: 0.0
        );
        // pan
        ~targetMeta[("chan_%_pan").format(chan).asSymbol] = (
            busIndex: baseIdx + 2,
            min: -1.0,
            max: 1.0,
            default: 0.0
        );
    };

    // === FX: HEAT (2 buses) ===
    // Indices 1052-1053
    ~targetMeta[\fx_heat_drive] = (busIndex: ~unifiedBusBase + 52, min: 0.0, max: 1.0, default: 0.0);
    ~targetMeta[\fx_heat_mix] = (busIndex: ~unifiedBusBase + 53, min: 0.0, max: 1.0, default: 1.0);

    // === FX: ECHO (6 buses) ===
    // Indices 1054-1059
    ~targetMeta[\fx_echo_time] = (busIndex: ~unifiedBusBase + 54, min: 0.0, max: 1.0, default: 0.3);
    ~targetMeta[\fx_echo_feedback] = (busIndex: ~unifiedBusBase + 55, min: 0.0, max: 1.0, default: 0.3);
    ~targetMeta[\fx_echo_tone] = (busIndex: ~unifiedBusBase + 56, min: 0.0, max: 1.0, default: 0.7);
    ~targetMeta[\fx_echo_wow] = (busIndex: ~unifiedBusBase + 57, min: 0.0, max: 1.0, default: 0.1);
    ~targetMeta[\fx_echo_spring] = (busIndex: ~unifiedBusBase + 58, min: 0.0, max: 1.0, default: 0.0);
    ~targetMeta[\fx_echo_verbSend] = (busIndex: ~unifiedBusBase + 59, min: 0.0, max: 1.0, default: 0.0);

    // === FX: REVERB (3 buses) ===
    // Indices 1060-1062
    ~targetMeta[\fx_verb_size] = (busIndex: ~unifiedBusBase + 60, min: 0.0, max: 1.0, default: 0.75);
    ~targetMeta[\fx_verb_decay] = (busIndex: ~unifiedBusBase + 61, min: 0.0, max: 1.0, default: 0.65);
    ~targetMeta[\fx_verb_tone] = (busIndex: ~unifiedBusBase + 62, min: 0.0, max: 1.0, default: 0.7);

    // === FX: DUAL_FILTER (8 buses) ===
    // Indices 1063-1070
    ~targetMeta[\fx_fb_drive] = (busIndex: ~unifiedBusBase + 63, min: 0.0, max: 1.0, default: 0.0);
    ~targetMeta[\fx_fb_freq1] = (busIndex: ~unifiedBusBase + 64, min: 0.0, max: 1.0, default: 0.6);
    ~targetMeta[\fx_fb_freq2] = (busIndex: ~unifiedBusBase + 65, min: 0.0, max: 1.0, default: 0.6);
    ~targetMeta[\fx_fb_reso1] = (busIndex: ~unifiedBusBase + 66, min: 0.0, max: 1.0, default: 0.3);
    ~targetMeta[\fx_fb_reso2] = (busIndex: ~unifiedBusBase + 67, min: 0.0, max: 1.0, default: 0.3);
    ~targetMeta[\fx_fb_syncAmt] = (busIndex: ~unifiedBusBase + 68, min: 0.0, max: 1.0, default: 0.0);
    ~targetMeta[\fx_fb_harmonics] = (busIndex: ~unifiedBusBase + 69, min: 0.0, max: 7.0, default: 0.0);
    ~targetMeta[\fx_fb_mix] = (busIndex: ~unifiedBusBase + 70, min: 0.0, max: 1.0, default: 0.5);

    // === BUILD BUS REGISTRY ===
    // Create Bus objects for each target
    ~targetMeta.keysValuesDo { |key, meta|
        var bus = Bus(\control, meta.busIndex, 1, s);
        ~busRegistry[key] = bus;
        // Initialize bus to default value
        bus.set(meta.default);
    };

    // === BUILD ORDERED KEY ARRAYS ===
    // ~targetKeysOrderedByBusIndex: for deterministic iteration in apply tick
    ~targetKeysOrderedByBusIndex = ~targetMeta.keys.asArray.sort { |a, b|
        ~targetMeta[a].busIndex < ~targetMeta[b].busIndex
    };

    // === MOD TARGET STATE ===
    // ~modTargetState: targetKey -> {baseValue, lastModSum, bus}
    // This is the canonical state for each target
    ~modTargetState = Dictionary.new;
    ~targetMeta.keysValuesDo { |key, meta|
        ~modTargetState[key] = (
            baseValue: meta.default,
            lastModSum: 0.0,
            boidOffset: 0.0,
            bus: ~busRegistry[key]
        );
    };

    // === PENDING QUEUES ===
    // These are drained atomically in the apply tick
    ~pendingBaseUpdates = Dictionary.new;   // targetKey -> value (last-write-wins)
    ~pendingRouteOps = List.new;            // List of route operations
    ~pendingBoidOps = List.new;             // List of boid operations

    // === MOD SOURCE STATE ===
    // Populated by mod_apply or external source readers
    // ~modSourceState: sourceKey -> currentValue (snapshot per tick)
    ~modSourceState = Dictionary.new;
    ~modSourceKeysOrdered = Array.new;

    // === ROUTE STORAGE ===
    // ~modRoutes: targetKey -> List of (sourceKey, depth, amount, offset, polarity, invert)
    ~modRoutes = Dictionary.new;

    // === BOID STATE ===
    // ~boidEnabled: true/false
    // ~boidOffsets: targetKey -> offset value
    ~boidEnabled = false;
    ~boidOffsets = Dictionary.new;

    // === VERIFY BUS ALLOCATION ===
    "  Bus Unification allocated % buses at indices %-%.".format(
        ~unifiedBusCount,
        ~unifiedBusBase,
        ~unifiedBusBase + ~unifiedBusCount - 1
    ).postln;

    // Post sample of targets for verification
    "  Sample targets:".postln;
    [\mod_1_p0, \chan_1_echo, \fx_heat_drive, \fx_echo_time, \fx_verb_size, \fx_fb_freq1].do { |key|
        var meta = ~targetMeta[key];
        if(meta.notNil, {
            "    %: bus=%, default=%".format(key, meta.busIndex, meta.default).postln;
        });
    };

    "  [x] Bus Unification infrastructure ready (% targets)".format(~targetMeta.size).postln;
};

// === HELPER FUNCTIONS ===

// Get bus index for a target key
~getBusIndex = { |targetKey|
    var meta = ~targetMeta[targetKey.asSymbol];
    if(meta.notNil, { meta.busIndex }, { nil });
};

// Get Bus object for a target key
~getBus = { |targetKey|
    ~busRegistry[targetKey.asSymbol];
};

// Get target metadata
~getTargetMeta = { |targetKey|
    ~targetMeta[targetKey.asSymbol];
};

// Queue a base value update (called from OSC handlers)
~queueBaseUpdate = { |targetKey, value|
    ~pendingBaseUpdates[targetKey.asSymbol] = value;
};

// Queue a route operation
~queueRouteOp = { |op, sourceKey, targetKey, depth, amount, offset, polarity, invert|
    ~pendingRouteOps.add((
        op: op,  // \set, \remove, \clear
        sourceKey: sourceKey,
        targetKey: targetKey,
        depth: depth,
        amount: amount,
        offset: offset,
        polarity: polarity,
        invert: invert
    ));
};

// Queue a boid operation
~queueBoidOp = { |op, offsets|
    ~pendingBoidOps.add((
        op: op,  // \enable, \disable, \setOffsets
        offsets: offsets
    ));
};

// =============================================================================
// PHASE 2: APPLY LOOP (500Hz Atomic Tick)
// =============================================================================

/*
Apply Tick (500Hz, Atomic, Non-yielding, Deterministic)

Uses swap-at-drain-start pattern for deterministic cutoff:
1. Swap pending queues with fresh empty ones (defines cutoff)
2. Drain base updates (last-write-wins per target)
3. Drain route ops (in queue order)
4. Drain boid ops FIFO (enable/disable, then offsets replacement)
5. Snapshot mod sources (iterate ordered source keys)
6. Compute & write targets (iterate by ascending bus index)
   effective = clamp(baseValue + nonBoidModSum + boidOffset, min, max)
*/

~applyTickRoutine = nil;
~applyTickRate = 500;  // Hz

~startApplyTick = {
    if(~applyTickRoutine.notNil, {
        ~applyTickRoutine.stop;
    });

    ~applyTickRoutine = Routine({
        inf.do {
            // === SWAP-AT-DRAIN-START (deterministic cutoff) ===
            // Capture current queues and replace with fresh empty ones
            var drainBaseUpdates = ~pendingBaseUpdates;
            var drainRouteOps = ~pendingRouteOps;
            var drainBoidOps = ~pendingBoidOps;

            ~pendingBaseUpdates = Dictionary.new;
            ~pendingRouteOps = List.new;
            ~pendingBoidOps = List.new;

            // === PHASE 1: DRAIN BASE UPDATES ===
            drainBaseUpdates.keysValuesDo { |targetKey, value|
                var state = ~modTargetState[targetKey];
                var meta = ~targetMeta[targetKey];
                if(state.notNil && meta.notNil, {
                    // Clamp value to valid range
                    state.baseValue = value.clip(meta.min, meta.max);
                });
            };

            // === PHASE 2: DRAIN ROUTE OPS ===
            drainRouteOps.do { |routeOp|
                var op = routeOp.op;
                var targetKey = routeOp.targetKey;
                var sourceKey = routeOp.sourceKey;

                case
                { op == \set } {
                    // Add or update route
                    var routes = ~modRoutes[targetKey];
                    var existing;
                    if(routes.isNil, {
                        routes = List.new;
                        ~modRoutes[targetKey] = routes;
                    });
                    // Find existing route from same source
                    existing = routes.detect { |r| r.sourceKey == sourceKey };
                    if(existing.notNil, {
                        // Update existing
                        existing.depth = routeOp.depth;
                        existing.amount = routeOp.amount;
                        existing.offset = routeOp.offset;
                        existing.polarity = routeOp.polarity;
                        existing.invert = routeOp.invert;
                    }, {
                        // Add new
                        routes.add((
                            sourceKey: sourceKey,
                            depth: routeOp.depth,
                            amount: routeOp.amount,
                            offset: routeOp.offset,
                            polarity: routeOp.polarity,
                            invert: routeOp.invert
                        ));
                    });
                }
                { op == \remove } {
                    // Remove route
                    var routes = ~modRoutes[targetKey];
                    if(routes.notNil, {
                        routes.removeAllSuchThat { |r| r.sourceKey == sourceKey };
                        if(routes.size == 0, {
                            ~modRoutes.removeAt(targetKey);
                        });
                    });
                }
                { op == \clear } {
                    // Clear all routes for target (or all if targetKey is nil)
                    if(targetKey.isNil, {
                        ~modRoutes.clear;
                    }, {
                        ~modRoutes.removeAt(targetKey);
                    });
                };
            };

            // === PHASE 3: DRAIN BOID OPS (FIFO) ===
            // Per spec: FIFO order is authoritative
            // - [\enable, true]: ~boidEnabled := true
            // - [\enable, false] (disable): ~boidEnabled := false AND ~boidOffsets := empty
            // - [\setOffsets, snapshot]: ~boidOffsets := snapshot (full replacement)
            drainBoidOps.do { |boidOp|
                var op = boidOp.op;
                case
                { op == \enable } {
                    ~boidEnabled = true;
                }
                { op == \disable } {
                    ~boidEnabled = false;
                    ~boidOffsets = Dictionary.new;  // Clear offsets on disable (Invariant 4)
                }
                { op == \setOffsets } {
                    // Replace entire offsets dict (Invariant 5: snapshot replacement)
                    ~boidOffsets = boidOp.offsets ?? Dictionary.new;
                };
            };

            // === PHASE 4: SNAPSHOT MOD SOURCES ===
            // Read current values from mod source buses
            ~modSourceState.clear;
            ~modSourceKeysOrdered.do { |sourceKey|
                var bus = ~getModSourceBus.(sourceKey);
                if(bus.notNil, {
                    ~modSourceState[sourceKey] = bus.getSynchronous;
                });
            };

            // Also snapshot from existing ~modBuses for backward compat
            if(~modBuses.notNil, {
                ~modBuses.size.do { |i|
                    var key = ("modBus_%").format(i).asSymbol;
                    if(~modSourceKeysOrdered.includes(key).not, {
                        try {
                            ~modSourceState[key] = ~modBuses[i].getSynchronous;
                        };
                    });
                };
            });

            // === PHASE 5: COMPUTE & WRITE TARGETS ===
            // Iterate in deterministic bus index order
            ~targetKeysOrderedByBusIndex.do { |targetKey|
                var state = ~modTargetState[targetKey];
                var meta = ~targetMeta[targetKey];
                var routes = ~modRoutes[targetKey];
                var modSum = 0.0;
                var boidOffset = 0.0;
                var effective;

                if(state.notNil && meta.notNil, {
                    // Compute modulation sum from routes
                    if(routes.notNil && routes.size > 0, {
                        routes.do { |route|
                            var sourceVal = ~modSourceState[route.sourceKey] ? 0.0;
                            var delta;

                            // Apply invert
                            if(route.invert == 1, {
                                sourceVal = sourceVal.neg;
                            });

                            // Apply polarity transformation
                            case
                            { route.polarity == 0 } {
                                // Bipolar: sourceVal already -1..+1
                                delta = sourceVal;
                            }
                            { route.polarity == 1 } {
                                // Uni+: 0..+1
                                delta = (sourceVal + 1) * 0.5;
                            }
                            { route.polarity == 2 } {
                                // Uni-: -1..0
                                delta = ((sourceVal + 1) * 0.5).neg;
                            };

                            // Scale by depth * amount, add offset
                            delta = (delta * route.depth * route.amount) + route.offset;
                            modSum = modSum + delta;
                        };
                    });

                    // Get boid offset if enabled (lookup by busIndex per spec v4)
                    if(~boidEnabled, {
                        boidOffset = ~boidOffsets[meta.busIndex] ? 0.0;
                    });

                    // Compute effective value
                    // For 0-1 params, modSum scales the range; for pan (-1 to 1), it's additive
                    effective = state.baseValue + (modSum * (meta.max - meta.min)) + boidOffset;
                    effective = effective.clip(meta.min, meta.max);

                    // Write to bus
                    state.bus.set(effective);
                    state.lastModSum = modSum;
                });
            };

            // Wait for next tick (500Hz = 2ms)
            0.002.wait;
        };
    }).play(SystemClock);

    "  [x] Apply tick started (500Hz)".postln;
};

~stopApplyTick = {
    if(~applyTickRoutine.notNil, {
        ~applyTickRoutine.stop;
        ~applyTickRoutine = nil;
    });
    "  Apply tick stopped".postln;
};

// === MOD SOURCE REGISTRATION ===
// Register a mod source (from mod_slots, crossmod, etc.)

~registerModSource = { |sourceKey, bus|
    if(~modSourceKeysOrdered.includes(sourceKey).not, {
        ~modSourceKeysOrdered = ~modSourceKeysOrdered.add(sourceKey);
        // Sort by ASCII codepoint for determinism
        ~modSourceKeysOrdered = ~modSourceKeysOrdered.sort { |a, b|
            a.asString < b.asString
        };
    });
};

// Get mod source bus (for backward compat with existing ~modBuses)
// This wraps ~getModSourceBus from crossmod_buses.scd if available
~getUnifiedModSourceBus = { |sourceIdOrKey|
    var result = nil;
    case
    { sourceIdOrKey.isInteger } {
        // Numeric: use old modBus index
        if(~modBuses.notNil && sourceIdOrKey >= 0 && sourceIdOrKey < ~modBuses.size, {
            result = ~modBuses[sourceIdOrKey];
        });
    }
    { sourceIdOrKey.isString || sourceIdOrKey.isSymbol } {
        // String key: look up in registry
        var key = sourceIdOrKey.asSymbol;
        if(key.asString.beginsWith("modBus_"), {
            var idx = key.asString[7..].asInteger;
            if(~modBuses.notNil && idx >= 0 && idx < ~modBuses.size, {
                result = ~modBuses[idx];
            });
        });
    };
    result;
};

"bus_unification.scd loaded (Phase 1: Infrastructure, Phase 2: Apply Loop)".postln;
