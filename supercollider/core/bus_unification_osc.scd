/*
Bus Unification OSC Handlers
New preferred endpoints for bus-based parameter control.

These endpoints enqueue updates to ~pendingBaseUpdates, which are
drained atomically in the apply tick. This ensures user knob changes
are never overwritten by stale modulation values.

Legacy endpoints (in osc_handlers.scd, ext_mod_osc.scd) are updated
to also enqueue through this system for backward compatibility.
*/

~setupBusUnificationOSC = {
    "Setting up Bus Unification OSC handlers...".postln;

    // =========================================================================
    // GENERIC BASE VALUE UPDATE
    // /noise/bus/base [targetKey, normalizedValue]
    // Used by Python for generator params (freq, cutoff, res, attack, decay, custom0-4)
    // =========================================================================

    OSCdef(\busBase).free;
    OSCdef(\busBase, { |msg|
        var targetKey = msg[1].asString.asSymbol;
        var normValue = msg[2].asFloat.clip(0, 1);
        var meta = ~targetMeta[targetKey];

        if(meta.notNil, {
            var realValue;

            // Apply inversion if specified (before denormalization)
            // Used for resonance where UI shows "more resonance" but rq is inverse
            if(meta[\invert] == true, {
                normValue = 1.0 - normValue;
            });

            // Denormalize from 0-1 to actual range using target metadata
            if(meta.curve == \exp, {
                realValue = normValue.linexp(0, 1, meta.min.max(0.001), meta.max);
            }, {
                realValue = normValue.linlin(0, 1, meta.min, meta.max);
            });
            ~queueBaseUpdate.(targetKey, realValue);
        }, {
            "WARNING: /noise/bus/base unknown target: %".format(targetKey).postln;
        });
    }, '/noise/bus/base');

    // =========================================================================
    // MOD SLOT PARAMETERS (P0-P6)
    // /noise/mod/bus/p0 ... /noise/mod/bus/p6 [slot, value]
    // =========================================================================

    7.do { |pIdx|
        var path = ("/noise/mod/bus/p%").format(pIdx);

        OSCdef(("busModP%" ++ pIdx).asSymbol).free;
        OSCdef(("busModP%" ++ pIdx).asSymbol, { |msg|
            var slot = msg[1].asInteger.clip(1, 4);
            var value = msg[2].asFloat.clip(0, 1);
            var targetKey = ("mod_%_p%").format(slot, pIdx).asSymbol;

            ~queueBaseUpdate.(targetKey, value);
        }, path);
    };

    // =========================================================================
    // CHANNEL PARAMETERS
    // /noise/channel/bus/echoSend [channel, value]
    // /noise/channel/bus/verbSend [channel, value]
    // /noise/channel/bus/pan [channel, value]
    // =========================================================================

    OSCdef(\busChannelEcho).free;
    OSCdef(\busChannelEcho, { |msg|
        var channel = msg[1].asInteger.clip(1, 8);
        var value = msg[2].asFloat.clip(0, 1);
        var targetKey = ("chan_%_echo").format(channel).asSymbol;

        ~queueBaseUpdate.(targetKey, value);
    }, '/noise/channel/bus/echoSend');

    OSCdef(\busChannelVerb).free;
    OSCdef(\busChannelVerb, { |msg|
        var channel = msg[1].asInteger.clip(1, 8);
        var value = msg[2].asFloat.clip(0, 1);
        var targetKey = ("chan_%_verb").format(channel).asSymbol;

        ~queueBaseUpdate.(targetKey, value);
    }, '/noise/channel/bus/verbSend');

    OSCdef(\busChannelPan).free;
    OSCdef(\busChannelPan, { |msg|
        var channel = msg[1].asInteger.clip(1, 8);
        var value = msg[2].asFloat.clip(-1, 1);
        var targetKey = ("chan_%_pan").format(channel).asSymbol;

        ~queueBaseUpdate.(targetKey, value);
    }, '/noise/channel/bus/pan');

    // =========================================================================
    // FX: HEAT
    // /noise/fx/bus/heat/drive [value]
    // /noise/fx/bus/heat/mix [value]
    // =========================================================================

    OSCdef(\busHeatDrive).free;
    OSCdef(\busHeatDrive, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_heat_drive, value);
    }, '/noise/fx/bus/heat/drive');

    OSCdef(\busHeatMix).free;
    OSCdef(\busHeatMix, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_heat_mix, value);
    }, '/noise/fx/bus/heat/mix');

    // =========================================================================
    // FX: ECHO
    // /noise/fx/bus/echo/time [value]
    // /noise/fx/bus/echo/feedback [value]
    // /noise/fx/bus/echo/tone [value]
    // /noise/fx/bus/echo/wow [value]
    // /noise/fx/bus/echo/spring [value]
    // /noise/fx/bus/echo/verbSend [value]
    // =========================================================================

    OSCdef(\busEchoTime).free;
    OSCdef(\busEchoTime, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_echo_time, value);
    }, '/noise/fx/bus/echo/time');

    OSCdef(\busEchoFeedback).free;
    OSCdef(\busEchoFeedback, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_echo_feedback, value);
    }, '/noise/fx/bus/echo/feedback');

    OSCdef(\busEchoTone).free;
    OSCdef(\busEchoTone, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_echo_tone, value);
    }, '/noise/fx/bus/echo/tone');

    OSCdef(\busEchoWow).free;
    OSCdef(\busEchoWow, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_echo_wow, value);
    }, '/noise/fx/bus/echo/wow');

    OSCdef(\busEchoSpring).free;
    OSCdef(\busEchoSpring, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_echo_spring, value);
    }, '/noise/fx/bus/echo/spring');

    OSCdef(\busEchoVerbSend).free;
    OSCdef(\busEchoVerbSend, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_echo_verbSend, value);
    }, '/noise/fx/bus/echo/verbSend');

    // =========================================================================
    // FX: REVERB
    // /noise/fx/bus/reverb/size [value]
    // /noise/fx/bus/reverb/decay [value]
    // /noise/fx/bus/reverb/tone [value]
    // =========================================================================

    OSCdef(\busVerbSize).free;
    OSCdef(\busVerbSize, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_verb_size, value);
    }, '/noise/fx/bus/reverb/size');

    OSCdef(\busVerbDecay).free;
    OSCdef(\busVerbDecay, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_verb_decay, value);
    }, '/noise/fx/bus/reverb/decay');

    OSCdef(\busVerbTone).free;
    OSCdef(\busVerbTone, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_verb_tone, value);
    }, '/noise/fx/bus/reverb/tone');

    // =========================================================================
    // FX: DUAL_FILTER
    // /noise/fx/bus/fb/drive [value]
    // /noise/fx/bus/fb/freq1 [value]
    // /noise/fx/bus/fb/freq2 [value]
    // /noise/fx/bus/fb/reso1 [value]
    // /noise/fx/bus/fb/reso2 [value]
    // /noise/fx/bus/fb/syncAmt [value]
    // /noise/fx/bus/fb/harmonics [value]
    // /noise/fx/bus/fb/mix [value]
    // =========================================================================

    OSCdef(\busFbDrive).free;
    OSCdef(\busFbDrive, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_fb_drive, value);
    }, '/noise/fx/bus/fb/drive');

    OSCdef(\busFbFreq1).free;
    OSCdef(\busFbFreq1, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_fb_freq1, value);
    }, '/noise/fx/bus/fb/freq1');

    OSCdef(\busFbFreq2).free;
    OSCdef(\busFbFreq2, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_fb_freq2, value);
    }, '/noise/fx/bus/fb/freq2');

    OSCdef(\busFbReso1).free;
    OSCdef(\busFbReso1, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_fb_reso1, value);
    }, '/noise/fx/bus/fb/reso1');

    OSCdef(\busFbReso2).free;
    OSCdef(\busFbReso2, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_fb_reso2, value);
    }, '/noise/fx/bus/fb/reso2');

    OSCdef(\busFbSyncAmt).free;
    OSCdef(\busFbSyncAmt, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_fb_syncAmt, value);
    }, '/noise/fx/bus/fb/syncAmt');

    OSCdef(\busFbHarmonics).free;
    OSCdef(\busFbHarmonics, { |msg|
        var value = msg[1].asFloat.clip(0, 7);
        ~queueBaseUpdate.(\fx_fb_harmonics, value);
    }, '/noise/fx/bus/fb/harmonics');

    OSCdef(\busFbMix).free;
    OSCdef(\busFbMix, { |msg|
        var value = msg[1].asFloat.clip(0, 1);
        ~queueBaseUpdate.(\fx_fb_mix, value);
    }, '/noise/fx/bus/fb/mix');

    // =========================================================================
    // ROUTE OPERATIONS
    // /noise/bus/route/set [sourceKey, targetKey, depth, amount, offset, polarity, invert]
    // /noise/bus/route/remove [sourceKey, targetKey]
    // /noise/bus/route/clear [targetKey] (or no args for clear all)
    // =========================================================================

    OSCdef(\busRouteSet).free;
    OSCdef(\busRouteSet, { |msg|
        var sourceKey = msg[1].asString.asSymbol;
        var targetKey = msg[2].asString.asSymbol;
        var depth = msg[3].asFloat ? 0.5;
        var amount = msg[4].asFloat ? 1.0;
        var offset = msg[5].asFloat ? 0.0;
        var polarity = msg[6].asInteger ? 0;
        var invert = msg[7].asInteger ? 0;

        ~queueRouteOp.(\set, sourceKey, targetKey, depth, amount, offset, polarity, invert);
    }, '/noise/bus/route/set');

    OSCdef(\busRouteRemove).free;
    OSCdef(\busRouteRemove, { |msg|
        var sourceKey = msg[1].asString.asSymbol;
        var targetKey = msg[2].asString.asSymbol;

        ~queueRouteOp.(\remove, sourceKey, targetKey, 0, 0, 0, 0, 0);
    }, '/noise/bus/route/remove');

    OSCdef(\busRouteClear).free;
    OSCdef(\busRouteClear, { |msg|
        var targetKey = if(msg.size > 1, { msg[1].asString.asSymbol }, { nil });

        ~queueRouteOp.(\clear, nil, targetKey, 0, 0, 0, 0, 0);
    }, '/noise/bus/route/clear');

    // =========================================================================
    // BOID OPERATIONS (per spec v4)
    // /noise/boid/enable [int enabled] - 1=enable, 0=disable (clears offsets)
    // /noise/boid/offsets [busIndex1, offset1, busIndex2, offset2, ...] - complete snapshot
    // /noise/boid/clear - clear all offsets (equivalent to empty offsets message)
    // =========================================================================

    // Validation: target index range (0-148) per spec
    // 149 targets total: gen core (0-39), gen custom (40-79), mod (80-107), chan (108-131), fx (132-148)
    // Python sends target indices directly; SC converts to absolute bus indices internally
    ~isValidTargetIndex = { |targetIndex|
        targetIndex.isInteger && (targetIndex >= 0) && (targetIndex <= 148);
    };

    OSCdef(\boidEnable).free;
    OSCdef(\boidEnable, { |msg|
        var enabled = if(msg.size > 1, { msg[1].asInteger }, { 0 });
        if(enabled == 1, {
            "BOID: Enabled".postln;
            ~queueBoidOp.(\enable, nil);
        }, {
            "BOID: Disabled".postln;
            ~queueBoidOp.(\disable, nil);
        });
    }, '/noise/boid/enable');

    OSCdef(\boidOffsets).free;
    OSCdef(\boidOffsets, { |msg|
        var offsets = Dictionary.new;
        var i = 1;
        var pairCount = 0;
        var maxPairs = 100;
        var receivedIndices = List.new;

        // Parse pairs: [targetIndex1, offset1, targetIndex2, offset2, ...]
        // Python sends target indices 0-148; we convert to absolute bus indices for storage
        while({ (i + 1) < msg.size && (pairCount < maxPairs) }, {
            var targetIndex = msg[i].asInteger;
            var offset = msg[i+1].asFloat;
            receivedIndices.add(targetIndex);

            // Validate target index range (0-148) and non-finite offset
            if(~isValidTargetIndex.(targetIndex), {
                if(offset.isNaN.not && (offset.abs < inf), {
                    // Convert target index to absolute bus index for storage
                    var absIndex = ~unifiedBusBase + targetIndex;
                    // Last occurrence wins for duplicate targetIndex
                    offsets[absIndex] = offset;
                });
            });
            pairCount = pairCount + 1;
            i = i + 2;
        });
        // DEBUG: Print received target indices (every 20 messages to avoid flood)
        if(~boidDebugCounter.isNil, { ~boidDebugCounter = 0 });
        ~boidDebugCounter = ~boidDebugCounter + 1;
        if((~boidDebugCounter % 20) == 1, {
            "BOID DEBUG: received % indices: %".format(receivedIndices.size, receivedIndices.asArray[0..9]).postln;
        });
        ~queueBoidOp.(\setOffsets, offsets);
    }, '/noise/boid/offsets');

    OSCdef(\boidClear).free;
    OSCdef(\boidClear, { |msg|
        // Clear is equivalent to empty offsets snapshot
        ~queueBoidOp.(\setOffsets, Dictionary.new);
    }, '/noise/boid/clear');

    // =========================================================================
    // VALUE STREAM (for UI feedback)
    // Stream current effective values back to Python
    // =========================================================================

    ~busValueStreamAddr = NetAddr("127.0.0.1", 57121);
    ~busValueStreamRate = 20;  // fps
    ~busValueStreamRoutine = nil;

    ~startBusValueStream = {
        if(~busValueStreamRoutine.notNil, {
            ~busValueStreamRoutine.stop;
        });

        ~busValueStreamRoutine = Routine({
            loop {
                var messages = List.new;

                // Collect values for targets with active routes
                ~modRoutes.keysValuesDo { |targetKey, routes|
                    if(routes.notNil && routes.size > 0, {
                        var state = ~modTargetState[targetKey];
                        var meta = ~targetMeta[targetKey];
                        if(state.notNil && meta.notNil, {
                            var currentVal;
                            try {
                                currentVal = state.bus.getSynchronous;
                            } {
                                currentVal = state.baseValue;
                            };
                            // Normalize to 0-1
                            currentVal = (currentVal - meta.min) / (meta.max - meta.min);
                            currentVal = currentVal.clip(0, 1);
                            messages.add([targetKey.asString, currentVal]);
                        });
                    });
                };

                if(messages.size > 0, {
                    var flat = messages.collect({ |m| m }).flatten;
                    ~busValueStreamAddr.sendMsg('/noise/bus/values', *flat);
                });

                (1 / ~busValueStreamRate).wait;
            };
        }).play;

        "  Bus value stream started".postln;
    };

    ~stopBusValueStream = {
        if(~busValueStreamRoutine.notNil, {
            ~busValueStreamRoutine.stop;
            ~busValueStreamRoutine = nil;
        });
        "  Bus value stream stopped".postln;
    };

    "  [x] Bus Unification OSC handlers ready".postln;
};

"bus_unification_osc.scd loaded (Phase 3: OSC Handlers)".postln;
