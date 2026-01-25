/*
Bus Unification - Unified Parameter Control Architecture (v2 - 149 targets)
Expands to include generator parameters alongside mod slots, channels, and FX.

Problem solved:
- ext_mod cached base values at route creation, causing user knob changes to be overwritten
- Now: UI writes to base, modulation adds to base, synths read combined value from bus

Architecture:
- 149 control buses allocated contiguously
- Single-writer: only apply tick writes to target buses
- Canonical base: one baseValue per target in ~modTargetState
- Bus-only read: SynthDefs read covered params from In.kr(bus) only

Bus Layout (149 total):
| Index     | Count | Category      | Parameters                                      |
|-----------|-------|---------------|------------------------------------------------|
| 0-39      | 40    | Gen Core      | 8 slots x 5 params (freq, cutoff, res, atk, dec)|
| 40-79     | 40    | Gen Custom    | 8 slots x 5 custom params (custom0-4)          |
| 80-107    | 28    | Mod Slots     | 4 slots x 7 params (P0-P6)                     |
| 108-131   | 24    | Channels      | 8 slots x 3 params (echo, verb, pan)           |
| 132       | 1     | FX: Heat      | drive (mix excluded - manual only)             |
| 133-138   | 6     | FX: Echo      | time, feedback, tone, wow, spring, verbSend    |
| 139-141   | 3     | FX: Reverb    | size, decay, tone                              |
| 142-148   | 7     | FX: DualFilter| drive, freq1, freq2, reso1, reso2, syncAmt, harmonics (mix excluded) |

Mix controls (fx_heat_mix, fx_dualFilter_mix) are NOT unified targets.
They remain manual-only via dedicated OSC endpoints.
*/

~setupBusUnification = {
    "Setting up Bus Unification (149 targets)...".postln;

    // === BUS ALLOCATION ===
    ~unifiedBusBase = 1000;
    ~unifiedBusCount = 149;

    // Pre-allocate control buses
    ~unifiedBuses = Bus.alloc(\control, s, ~unifiedBusCount);

    // If allocation didn't give us index 1000, log warning but continue
    if(~unifiedBuses.index != ~unifiedBusBase, {
        "WARNING: Bus allocation at % (wanted %)".format(~unifiedBuses.index, ~unifiedBusBase).postln;
        ~unifiedBusBase = ~unifiedBuses.index;
    });

    // === TARGET KEY DEFINITIONS ===
    ~targetMeta = Dictionary.new;
    ~busRegistry = Dictionary.new;

    // === GENERATOR CORE PARAMS (40 total: 8 slots x 5 params) ===
    // Indices 0-39
    // Order: freq, cutoff, res, attack, decay per slot
    8.do { |slotIdx|
        var slot = slotIdx + 1;  // 1-indexed
        var baseIdx = slotIdx * 5;

        // freq (index 0, 5, 10, ...)
        ~targetMeta[("gen_%_freq").format(slot).asSymbol] = (
            busIndex: ~unifiedBusBase + baseIdx + 0,
            min: 20.0,
            max: 8000.0,
            default: 400.0,
            curve: \exp
        );
        // cutoff (index 1, 6, 11, ...)
        ~targetMeta[("gen_%_cutoff").format(slot).asSymbol] = (
            busIndex: ~unifiedBusBase + baseIdx + 1,
            min: 20.0,
            max: 16000.0,
            default: 16000.0,
            curve: \exp
        );
        // res (index 2, 7, 12, ...)
        // invert: true because UI shows "resonance" (high=more) but rq is inverse (low=more)
        ~targetMeta[("gen_%_res").format(slot).asSymbol] = (
            busIndex: ~unifiedBusBase + baseIdx + 2,
            min: 0.1,
            max: 1.0,
            default: 1.0,
            curve: \lin,
            invert: true
        );
        // attack (index 3, 8, 13, ...)
        ~targetMeta[("gen_%_attack").format(slot).asSymbol] = (
            busIndex: ~unifiedBusBase + baseIdx + 3,
            min: 0.0001,
            max: 2.0,
            default: 0.0001,
            curve: \exp
        );
        // decay (index 4, 9, 14, ...)
        ~targetMeta[("gen_%_decay").format(slot).asSymbol] = (
            busIndex: ~unifiedBusBase + baseIdx + 4,
            min: 0.01,
            max: 10.0,
            default: 1.0,
            curve: \exp
        );
    };

    // === GENERATOR CUSTOM PARAMS (40 total: 8 slots x 5 custom) ===
    // Indices 40-79
    8.do { |slotIdx|
        var slot = slotIdx + 1;
        var baseIdx = 40 + (slotIdx * 5);

        5.do { |k|
            ~targetMeta[("gen_%_custom%").format(slot, k).asSymbol] = (
                busIndex: ~unifiedBusBase + baseIdx + k,
                min: 0.0,
                max: 1.0,
                default: 0.5,
                curve: \lin
            );
        };
    };

    // === MOD SLOT PARAMS (28 total: 4 slots x 7 params) ===
    // Indices 80-107
    4.do { |slotIdx|
        var slot = slotIdx + 1;
        7.do { |pIdx|
            var key = ("mod_%_p%").format(slot, pIdx).asSymbol;
            var busIdx = ~unifiedBusBase + 80 + (slotIdx * 7) + pIdx;
            ~targetMeta[key] = (
                busIndex: busIdx,
                min: 0.0,
                max: 1.0,
                default: 0.5,
                curve: \lin
            );
        };
    };

    // === CHANNEL PARAMS (24 total: 8 channels x 3 params) ===
    // Indices 108-131
    8.do { |chanIdx|
        var chan = chanIdx + 1;
        var baseIdx = ~unifiedBusBase + 108 + (chanIdx * 3);

        // echo
        ~targetMeta[("chan_%_echo").format(chan).asSymbol] = (
            busIndex: baseIdx,
            min: 0.0,
            max: 1.0,
            default: 0.0,
            curve: \lin
        );
        // verb
        ~targetMeta[("chan_%_verb").format(chan).asSymbol] = (
            busIndex: baseIdx + 1,
            min: 0.0,
            max: 1.0,
            default: 0.0,
            curve: \lin
        );
        // pan
        ~targetMeta[("chan_%_pan").format(chan).asSymbol] = (
            busIndex: baseIdx + 2,
            min: -1.0,
            max: 1.0,
            default: 0.0,
            curve: \lin
        );
    };

    // === FX: HEAT (1 bus - mix excluded) ===
    // Index 132
    ~targetMeta[\fx_heat_drive] = (busIndex: ~unifiedBusBase + 132, min: 0.0, max: 1.0, default: 0.0, curve: \lin);
    // fx_heat_mix is NOT a unified target - manual only

    // === FX: ECHO (6 buses) ===
    // Indices 133-138
    ~targetMeta[\fx_echo_time] = (busIndex: ~unifiedBusBase + 133, min: 0.0, max: 1.0, default: 0.3, curve: \lin);
    ~targetMeta[\fx_echo_feedback] = (busIndex: ~unifiedBusBase + 134, min: 0.0, max: 1.0, default: 0.3, curve: \lin);
    ~targetMeta[\fx_echo_tone] = (busIndex: ~unifiedBusBase + 135, min: 0.0, max: 1.0, default: 0.7, curve: \lin);
    ~targetMeta[\fx_echo_wow] = (busIndex: ~unifiedBusBase + 136, min: 0.0, max: 1.0, default: 0.1, curve: \lin);
    ~targetMeta[\fx_echo_spring] = (busIndex: ~unifiedBusBase + 137, min: 0.0, max: 1.0, default: 0.0, curve: \lin);
    ~targetMeta[\fx_echo_verbSend] = (busIndex: ~unifiedBusBase + 138, min: 0.0, max: 1.0, default: 0.0, curve: \lin);

    // === FX: REVERB (3 buses) ===
    // Indices 139-141
    ~targetMeta[\fx_reverb_size] = (busIndex: ~unifiedBusBase + 139, min: 0.0, max: 1.0, default: 0.75, curve: \lin);
    ~targetMeta[\fx_reverb_decay] = (busIndex: ~unifiedBusBase + 140, min: 0.0, max: 1.0, default: 0.65, curve: \lin);
    ~targetMeta[\fx_reverb_tone] = (busIndex: ~unifiedBusBase + 141, min: 0.0, max: 1.0, default: 0.7, curve: \lin);

    // === FX: DUAL_FILTER (7 buses - mix excluded) ===
    // Indices 142-148
    ~targetMeta[\fx_dualFilter_drive] = (busIndex: ~unifiedBusBase + 142, min: 0.0, max: 1.0, default: 0.0, curve: \lin);
    ~targetMeta[\fx_dualFilter_freq1] = (busIndex: ~unifiedBusBase + 143, min: 0.0, max: 1.0, default: 0.6, curve: \lin);
    ~targetMeta[\fx_dualFilter_freq2] = (busIndex: ~unifiedBusBase + 144, min: 0.0, max: 1.0, default: 0.6, curve: \lin);
    ~targetMeta[\fx_dualFilter_reso1] = (busIndex: ~unifiedBusBase + 145, min: 0.0, max: 1.0, default: 0.3, curve: \lin);
    ~targetMeta[\fx_dualFilter_reso2] = (busIndex: ~unifiedBusBase + 146, min: 0.0, max: 1.0, default: 0.3, curve: \lin);
    ~targetMeta[\fx_dualFilter_syncAmt] = (busIndex: ~unifiedBusBase + 147, min: 0.0, max: 1.0, default: 0.0, curve: \lin);
    ~targetMeta[\fx_dualFilter_harmonics] = (busIndex: ~unifiedBusBase + 148, min: 0.0, max: 7.0, default: 0.0, curve: \lin);
    // fx_dualFilter_mix is NOT a unified target - manual only

    // === BUILD BUS REGISTRY ===
    ~targetMeta.keysValuesDo { |key, meta|
        var bus = Bus(\control, meta.busIndex, 1, s);
        ~busRegistry[key] = bus;
        bus.set(meta.default);
    };

    // === BUILD ORDERED KEY ARRAYS ===
    ~targetKeysOrderedByBusIndex = ~targetMeta.keys.asArray.sort { |a, b|
        ~targetMeta[a].busIndex < ~targetMeta[b].busIndex
    };

    // === MOD TARGET STATE ===
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
    ~pendingBaseUpdates = Dictionary.new;
    ~pendingRouteOps = List.new;
    ~pendingBoidOps = List.new;

    // === MOD SOURCE STATE ===
    ~modSourceState = Dictionary.new;
    ~modSourceKeysOrdered = Array.new;

    // === ROUTE STORAGE ===
    ~modRoutes = Dictionary.new;

    // === BOID STATE ===
    // NOTE: Scaling is now handled Python-side via config/boid_target_scales.json
    // SC receives pre-scaled offsets and applies them directly (offset * range)
    ~boidEnabled = false;
    ~boidOffsets = Array.fill(149, { 0.0 });
    ~activeBoidIndices = Set.new;  // Track which indices have non-zero offsets (for lazy computation)

    // === VERIFY BUS ALLOCATION ===
    "  Bus Unification allocated % buses at indices %-%.".format(
        ~unifiedBusCount,
        ~unifiedBusBase,
        ~unifiedBusBase + ~unifiedBusCount - 1
    ).postln;

    // Post sample of targets for verification
    "  Sample targets:".postln;
    [\gen_1_freq, \gen_1_cutoff, \gen_1_custom0, \mod_1_p0, \chan_1_echo, \fx_heat_drive, \fx_reverb_size, \fx_dualFilter_freq1].do { |key|
        var meta = ~targetMeta[key];
        if(meta.notNil, {
            "    %: bus=%, default=%, curve=%".format(key, meta.busIndex, meta.default, meta.curve).postln;
        });
    };

    "  [x] Bus Unification infrastructure ready (% targets)".format(~targetMeta.size).postln;
};

// === HELPER FUNCTIONS ===

~getBusIndex = { |targetKey|
    var meta = ~targetMeta[targetKey.asSymbol];
    if(meta.notNil, { meta.busIndex }, { nil });
};

~getBus = { |targetKey|
    ~busRegistry[targetKey.asSymbol];
};

~getTargetMeta = { |targetKey|
    ~targetMeta[targetKey.asSymbol];
};

~queueBaseUpdate = { |targetKey, value|
    ~pendingBaseUpdates[targetKey.asSymbol] = value;
};

~queueRouteOp = { |op, sourceKey, targetKey, depth, amount, offset, polarity, invert|
    ~pendingRouteOps.add((
        op: op,
        sourceKey: sourceKey,
        targetKey: targetKey,
        depth: depth,
        amount: amount,
        offset: offset,
        polarity: polarity,
        invert: invert
    ));
};

~queueBoidOp = { |op, offsets|
    ~pendingBoidOps.add((
        op: op,
        offsets: offsets
    ));
};

// =============================================================================
// APPLY LOOP (500Hz Atomic Tick)
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
~applyTickRate = 200;  // Reduced from 500Hz to prevent thread starvation

~startApplyTick = {
    if(~applyTickRoutine.notNil, {
        ~applyTickRoutine.stop;
    });

    ~applyTickRoutine = Routine({
        inf.do {
            // === SWAP-AT-DRAIN-START (deterministic cutoff) ===
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
                    var routes = ~modRoutes[targetKey];
                    var existing;
                    if(routes.isNil, {
                        routes = List.new;
                        ~modRoutes[targetKey] = routes;
                    });
                    existing = routes.detect { |r| r.sourceKey == sourceKey };
                    if(existing.notNil, {
                        existing.depth = routeOp.depth;
                        existing.amount = routeOp.amount;
                        existing.offset = routeOp.offset;
                        existing.polarity = routeOp.polarity;
                        existing.invert = routeOp.invert;
                    }, {
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
                    var routes = ~modRoutes[targetKey];
                    if(routes.notNil, {
                        routes.removeAllSuchThat { |r| r.sourceKey == sourceKey };
                        if(routes.size == 0, {
                            ~modRoutes.removeAt(targetKey);
                        });
                    });
                }
                { op == \clear } {
                    if(targetKey.isNil, {
                        ~modRoutes.clear;
                    }, {
                        ~modRoutes.removeAt(targetKey);
                    });
                };
            };

            // === PHASE 3: DRAIN BOID OPS (FIFO) ===
            drainBoidOps.do { |boidOp|
                var op = boidOp.op;
                case
                { op == \enable } {
                    ~boidEnabled = true;
                }
                { op == \disable } {
                    ~boidEnabled = false;
                    ~boidOffsets = Array.fill(149, { 0.0 });
                    ~activeBoidIndices = Set.new;
                }
                { op == \setOffsets } {
                    var newOffsets = Array.fill(149, { 0.0 });
                    var newActiveIndices = Set.new;
                    if(boidOp.offsets.notNil, {
                        boidOp.offsets.keysValuesDo { |busIndex, offset|
                            var idx = busIndex - ~unifiedBusBase;
                            if((idx >= 0) && (idx < 149), {
                                newOffsets[idx] = offset;
                                newActiveIndices.add(idx);  // Track active index
                            });
                        };
                    });
                    ~boidOffsets = newOffsets;
                    ~activeBoidIndices = newActiveIndices;
                };
            };

            // === PHASE 4: SNAPSHOT MOD SOURCES ===
            ~modSourceState.clear;
            ~modSourceKeysOrdered.do { |sourceKey|
                var bus = ~getModSourceBus.(sourceKey);
                if(bus.notNil, {
                    ~modSourceState[sourceKey] = bus.getSynchronous;
                });
            };

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

            // Read crossmod buses (envelope followers on generator audio)
            if(~crossModBus.notNil, {
                ~crossModBus.size.do { |i|
                    var key = ("crossModBus_%").format(i).asSymbol;
                    try {
                        ~modSourceState[key] = ~crossModBus[i].getSynchronous;
                    };
                };
            });

            // === PHASE 5: COMPUTE & WRITE TARGETS ===
            ~targetKeysOrderedByBusIndex.do { |targetKey|
                var state = ~modTargetState[targetKey];
                var meta = ~targetMeta[targetKey];
                var routes = ~modRoutes[targetKey];
                var modSum = 0.0;
                var boidOffset = 0.0;
                var effective;

                if(state.notNil && meta.notNil, {
                    // Compute modulation sum from routes
                    if(routes.isKindOf(Collection) && (routes.size > 0), {
                        routes.do { |route|
                            var sourceVal = ~modSourceState[route.sourceKey] ? 0.0;
                            var delta;

                            if(route.invert == 1, {
                                sourceVal = sourceVal.neg;
                            });

                            case
                            { route.polarity == 0 } {
                                delta = sourceVal;
                            }
                            { route.polarity == 1 } {
                                delta = (sourceVal + 1) * 0.5;
                            }
                            { route.polarity == 2 } {
                                delta = ((sourceVal + 1) * 0.5).neg;
                            };

                            delta = (delta * route.depth * route.amount) + route.offset;
                            modSum = modSum + delta;
                        };
                    });

                    // Get boid offset if enabled AND this target has active boid contribution
                    // (lazy computation: only process targets with non-zero boid offsets)
                    // NOTE: Scaling is now applied Python-side, offset arrives pre-scaled
                    if(~boidEnabled, {
                        var idx = meta.busIndex - ~unifiedBusBase;
                        if(~activeBoidIndices.includes(idx), {
                            var rawOffset = ~boidOffsets[idx] ? 0.0;
                            var range = meta.max - meta.min;
                            boidOffset = rawOffset * range;
                        });
                    });

                    // Compute effective value
                    effective = state.baseValue + (modSum * (meta.max - meta.min)) + boidOffset;
                    effective = effective.clip(meta.min, meta.max);

                    // Write to bus
                    state.bus.set(effective);
                    state.lastModSum = modSum;
                });
            };

            // Wait for next tick (200Hz = 5ms)
            // Reduced from 500Hz to prevent thread starvation under boid load
            0.005.wait;
        };
    }).play(SystemClock);

    "  [x] Apply tick started (200Hz)".postln;
};

~stopApplyTick = {
    if(~applyTickRoutine.notNil, {
        ~applyTickRoutine.stop;
        ~applyTickRoutine = nil;
    });
    "  Apply tick stopped".postln;
};

// === MOD SOURCE REGISTRATION ===

~registerModSource = { |sourceKey, bus|
    if(~modSourceKeysOrdered.includes(sourceKey).not, {
        ~modSourceKeysOrdered = ~modSourceKeysOrdered.add(sourceKey);
        ~modSourceKeysOrdered = ~modSourceKeysOrdered.sort { |a, b|
            a.asString < b.asString
        };
    });
};

~getUnifiedModSourceBus = { |sourceIdOrKey|
    var result = nil;
    case
    { sourceIdOrKey.isInteger } {
        if(~modBuses.notNil && sourceIdOrKey >= 0 && sourceIdOrKey < ~modBuses.size, {
            result = ~modBuses[sourceIdOrKey];
        });
    }
    { sourceIdOrKey.isString || sourceIdOrKey.isSymbol } {
        var key = sourceIdOrKey.asSymbol;
        var keyStr = key.asString;
        if(keyStr.beginsWith("modBus_"), {
            // Standard mod buses 0-15 (LFO/Sloth/ARSeq/SauceOfGrav outputs)
            var idx = keyStr[7..].asInteger;
            if(~modBuses.notNil && idx >= 0 && idx < ~modBuses.size, {
                result = ~modBuses[idx];
            });
        });
        if(result.isNil && keyStr.beginsWith("crossModBus_"), {
            // Cross-mod buses 0-7 (envelope followers on generator audio)
            var idx = keyStr[12..].asInteger;
            if(~crossModBus.notNil && idx >= 0 && idx < ~crossModBus.size, {
                result = ~crossModBus[idx];
            });
        });
    };
    result;
};

"bus_unification.scd loaded (149 targets: 80 gen + 28 mod + 24 chan + 17 fx)".postln;
