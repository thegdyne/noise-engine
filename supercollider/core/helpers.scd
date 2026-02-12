/*
Helper Functions
Reusable functions for generator management
*/

~setupHelpers = {
    "Setting up helpers...".postln;
    
    // =========================================================
    // SIGNAL PROCESSING HELPERS (used inside SynthDefs)
    // =========================================================
    
    // Shared multimode filter with BPF gain compensation
    // filterType: 0=LP, 1=HP, 2=BP, 3=NOT (notch), 4=LP2 (12dB), 5=OFF (bypass)
    // At low rq (high res), resonant filters will self-oscillate
    ~multiFilter = { |sig, filterType, filterFreq, rq|
        Select.ar(filterType, [
            RLPF.ar(sig, filterFreq, rq),                              // 0: LP (24dB resonant)
            RHPF.ar(sig, filterFreq, rq),                              // 1: HP (24dB resonant)
            BPF.ar(sig, filterFreq, rq, mul: rq.sqrt.reciprocal.min(15)), // 2: BP (with gain comp)
            BRF.ar(sig, filterFreq, rq),                               // 3: NOT (band-reject/notch)
            LPF.ar(sig, filterFreq),                                   // 4: LP2 (12dB, no resonance)
            sig                                                         // 5: OFF (bypass)
        ])
    };
    
    // SSOT trigger selector — shared by envVCA (amp gate) and any generator
    // that needs a rhythmic edge (e.g. MOLTI Phasor reset).
    // envSource: 0=OFF, 1=CLK, 2=MIDI
    // NOTE: 13 clock rates and 8 MIDI channels must match buses.scd
    ~trigSelect = { |envSource, clockRateIdx, clockTrigBus, midiTrigBus, slotIndex|
        var allTrigs, clockTrig, allMidiTrigs, midiTrig, clkOn, clkIdx;
        allTrigs = In.ar(clockTrigBus, 13);
        clkOn = (clockRateIdx >= 0);
        clkIdx = clockRateIdx.clip(0, 12);
        clockTrig = Select.ar(clkIdx, allTrigs) * clkOn;
        allMidiTrigs = In.ar(midiTrigBus, 8);
        midiTrig = Select.ar(slotIndex.clip(0, 7), allMidiTrigs);
        Select.ar(envSource.clip(0, 2), [DC.ar(0), clockTrig, midiTrig]);
    };

    // Envelope VCA - applies envelope based on envSource (OFF/CLK/MIDI)
    // Uses ~trigSelect (SSOT for trigger routing)
    ~envVCA = { |sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex|
        var trig, env;
        trig = ~trigSelect.(envSource, clockRate, clockTrigBus, midiTrigBus, slotIndex);
        env = EnvGen.ar(Env.perc(attack, decay), trig);
        sig * Select.kr(envSource > 0, [1.0, env]) * amp
    };
    
    // Stereo spread - subtle random panning for width
    // rate: LFO speed (lower = slower movement)
    // width: pan range (0-1, where 1 = full L-R)
    ~stereoSpread = { |sig, rate=0.2, width=0.3|
        Pan2.ar(sig, LFNoise1.kr(rate).range(width.neg, width))
    };


    // Ensure generator output is exactly 2 channels (SSOT for per-slot buses)
    // - mono -> dual-mono
    // - 2ch  -> passthrough
    // - >2ch -> mixdown to mono then dual-mono (safety to prevent bus spill into adjacent slots)
    ~ensure2ch = { |sig|
        var a = sig.asArray;
        if(a.size <= 1) {
            a = a[0] ! 2;
        } {
            if(a.size > 2) {
                a = Mix(a) ! 2;
            };
        };
        a
    };
    
    // =========================================================
    // GENERATOR MANAGEMENT (called from OSC handlers)
    // =========================================================
    
    // All 8 slots now use unified bus system (Phase 5: expanded from slot 1)
    ~genUnifiedSlots = Set[1, 2, 3, 4, 5, 6, 7, 8];

    ~startGenerator = { |slotID, genType|
        var params = ~genParams[slotID];
        var customBuses = params[\custom];
        var idx = slotID - 1;  // 0-indexed for arrays
        var useUnified = ~genUnifiedSlots.includes(slotID);
        var freqBusIdx, cutoffBusIdx, resBusIdx, attackBusIdx, decayBusIdx;
        var custom0Idx, custom1Idx, custom2Idx, custom3Idx, custom4Idx;

        if(~generators[slotID].notNil, {
            ~generators[slotID].free;
            ~generators[slotID] = nil;
        });

        // Determine which buses to use based on unified slot membership
        if(useUnified, {
            // Unified bus system (149-bus architecture)
            var slotKey = slotID.asString;
            freqBusIdx = ~busRegistry[("gen_" ++ slotKey ++ "_freq").asSymbol].index;
            cutoffBusIdx = ~busRegistry[("gen_" ++ slotKey ++ "_cutoff").asSymbol].index;
            resBusIdx = ~busRegistry[("gen_" ++ slotKey ++ "_res").asSymbol].index;
            attackBusIdx = ~busRegistry[("gen_" ++ slotKey ++ "_attack").asSymbol].index;
            decayBusIdx = ~busRegistry[("gen_" ++ slotKey ++ "_decay").asSymbol].index;
            custom0Idx = ~busRegistry[("gen_" ++ slotKey ++ "_custom0").asSymbol].index;
            custom1Idx = ~busRegistry[("gen_" ++ slotKey ++ "_custom1").asSymbol].index;
            custom2Idx = ~busRegistry[("gen_" ++ slotKey ++ "_custom2").asSymbol].index;
            custom3Idx = ~busRegistry[("gen_" ++ slotKey ++ "_custom3").asSymbol].index;
            custom4Idx = ~busRegistry[("gen_" ++ slotKey ++ "_custom4").asSymbol].index;
            "Slot % using UNIFIED buses".format(slotID).postln;
        }, {
            // Legacy bus system (~genParams)
            freqBusIdx = params[\frequency].index;
            cutoffBusIdx = params[\cutoff].index;
            resBusIdx = params[\resonance].index;
            attackBusIdx = params[\attack].index;
            decayBusIdx = params[\decay].index;
            custom0Idx = customBuses[0].index;
            custom1Idx = customBuses[1].index;
            custom2Idx = customBuses[2].index;
            custom3Idx = customBuses[3].index;
            custom4Idx = customBuses[4].index;
        });

        if(~genGroup.notNil, {
            var synthArgs;

            // Start channel strip FIRST (must exist before generator writes to bus)
            ~startChannelStrip.(slotID);

            // Build args for all generators
            // bufBus always passed (SC ignores unknown args;
            // any MOLTI-SAMP variant SynthDef will pick it up)
            synthArgs = [
                \out, ~genBus[idx],  // Per-slot bus
                \freqBus, freqBusIdx,
                \cutoffBus, cutoffBusIdx,
                \resBus, resBusIdx,
                \attackBus, attackBusIdx,
                \decayBus, decayBusIdx,
                \filterTypeBus, params[\filterType].index,
                \envEnabledBus, params[\envEnabled].index,
                \envSourceBus, params[\envSource].index,
                \clockRateBus, params[\clockRate].index,
                \clockTrigBus, ~clockTrigBus.index,
                \midiTrigBus, if(~midiTrigBus.notNil, { ~midiTrigBus.index }, { 0 }),
                \noteBus, if(~noteBus.notNil, { ~noteBus.index }, { 0 }),
                \slotIndex, idx,  // 0-indexed for MIDI trigger bus channel
                \bufBus, ~bufBuses[idx].index,
                // Custom params (5 per generator)
                \customBus0, custom0Idx,
                \customBus1, custom1Idx,
                \customBus2, custom2Idx,
                \customBus3, custom3Idx,
                \customBus4, custom4Idx,
                \portamentoBus, params[\portamento].index
            ];

            // Start generator - routes to per-slot bus (not master)
            ~generators[slotID] = Synth(genType, synthArgs, ~genGroup, \addToHead);

            // Start cross-mod follower (after generator, for envelope tracking)
            if(~startCrossModFollower.notNil, {
                ~startCrossModFollower.(slotID);
            });
        }, {
            "ERROR: genGroup is nil!".postln;
        });

        "Started % in slot %".format(genType, slotID).postln;
    };
    
    ~stopGenerator = { |slotID|
        if(~generators[slotID].notNil, {
            ~generators[slotID].free;
            ~generators[slotID] = nil;
            "Stopped generator in slot %".format(slotID).postln;
        });
        
        // Stop cross-mod follower
        if(~stopCrossModFollower.notNil, {
            ~stopCrossModFollower.(slotID);
        });
        
        // Stop channel strip when generator stops
        ~stopChannelStrip.(slotID);
    };
    
    // === END-STAGE AWARE DISPATCH ===
    // When end-stage infrastructure is booted (~endstageNodes not nil),
    // route start/stop through endstage-aware functions.
    // Otherwise fall through to legacy monolithic path above.
    // This allows gradual migration: unconverted generators use legacy,
    // converted generators use end-stage.

    ~startGeneratorDispatch = { |slotID, genType|
        if(~endstageNodes.notNil && ~endstageNodes.isArray, {
            // End-stage infrastructure is active — use new path
            ~startGeneratorEndstage.(slotID, genType);
        }, {
            // Legacy path (monolithic generators)
            ~startGenerator.(slotID, genType);
        });
    };

    ~stopGeneratorDispatch = { |slotID|
        if(~endstageNodes.notNil && ~endstageNodes.isArray, {
            ~stopGeneratorEndstage.(slotID);
        }, {
            ~stopGenerator.(slotID);
        });
    };

    "  [x] Helpers ready".postln;
};
