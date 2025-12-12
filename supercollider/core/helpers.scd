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
    // filterType: 0=LP, 1=HP, 2=BP
    // At low rq (high res), filters will self-oscillate
    ~multiFilter = { |sig, filterType, filterFreq, rq|
        Select.ar(filterType, [
            RLPF.ar(sig, filterFreq, rq),
            RHPF.ar(sig, filterFreq, rq),
            BPF.ar(sig, filterFreq, rq, mul: rq.sqrt.reciprocal.min(15))
        ])
    };
    
    // Envelope VCA - applies envelope based on envSource (OFF/CLK/MIDI)
    // This is the SINGLE SOURCE OF TRUTH for envelope triggering
    // envSource: 0=OFF (drone), 1=CLK (clock), 2=MIDI (midi trigger)
    ~envVCA = { |sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex|
        var allTrigs, clockTrig, allMidiTrigs, midiTrig, trig, env;
        
        // Clock trigger - select from clock rate bus
        allTrigs = In.ar(clockTrigBus, ~clockRates.size);
        clockTrig = Select.ar(clockRate, allTrigs);
        
        // MIDI trigger - read all 8 channels and select by slotIndex
        allMidiTrigs = In.ar(midiTrigBus, 8);
        midiTrig = Select.ar(slotIndex, allMidiTrigs);
        
        // Select trigger based on envSource: 0=none, 1=clock, 2=midi
        trig = Select.ar(envSource, [
            DC.ar(0),      // 0: OFF - no triggers (drone)
            clockTrig,     // 1: CLK - clock triggers only
            midiTrig       // 2: MIDI - midi triggers only
        ]);
        
        // Generate envelope
        env = EnvGen.ar(Env.perc(attack, decay), trig);
        
        // Apply envelope only when envSource > 0, otherwise pass through (drone)
        sig * Select.kr(envSource > 0, [1.0, env]) * amp
    };
    
    // Stereo spread - subtle random panning for width
    // rate: LFO speed (lower = slower movement)
    // width: pan range (0-1, where 1 = full L-R)
    ~stereoSpread = { |sig, rate=0.2, width=0.3|
        Pan2.ar(sig, LFNoise1.kr(rate).range(width.neg, width))
    };
    
    // =========================================================
    // GENERATOR MANAGEMENT (called from OSC handlers)
    // =========================================================
    
    ~startGenerator = { |slotID, genType|
        var params = ~genParams[slotID];
        var customBuses = params[\custom];
        
        if(~generators[slotID].notNil, {
            ~generators[slotID].free;
            ~generators[slotID] = nil;
        });
        
        if(~genGroup.notNil, {
            ~generators[slotID] = Synth(genType, [
                \out, ~masterBus,
                \freqBus, params[\frequency].index,
                \cutoffBus, params[\cutoff].index,
                \resBus, params[\resonance].index,
                \attackBus, params[\attack].index,
                \decayBus, params[\decay].index,
                \filterTypeBus, params[\filterType].index,
                \envEnabledBus, params[\envEnabled].index,
                \envSourceBus, params[\envSource].index,
                \clockRateBus, params[\clockRate].index,
                \clockTrigBus, ~clockTrigBus.index,
                \midiTrigBus, if(~midiTrigBus.notNil, { ~midiTrigBus.index }, { 0 }),
                \slotIndex, slotID - 1,  // 0-indexed for MIDI trigger bus channel
                // Custom params (5 per generator)
                \customBus0, customBuses[0].index,
                \customBus1, customBuses[1].index,
                \customBus2, customBuses[2].index,
                \customBus3, customBuses[3].index,
                \customBus4, customBuses[4].index
            ], ~genGroup, \addToHead);
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
    };
    
    "  ✓ Helpers ready".postln;
};
