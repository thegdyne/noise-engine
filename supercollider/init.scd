/*
Noise Engine - SuperCollider Initialization
Loads generators from separate files
*/

s.waitForBoot({
    
    "=== Noise Engine - SuperCollider ===".postln;
    "Initializing...".postln;
    
    // Global parameters
    ~params = Dictionary.new;
    ~params[\gravity] = Bus.control(s, 1).set(0.5);
    ~params[\density] = Bus.control(s, 1).set(0.5);
    ~params[\filter_cutoff] = Bus.control(s, 1).set(0.7);
    ~params[\amplitude] = Bus.control(s, 1).set(0.5);
    
    // Per-generator parameters (8 slots)
    ~genParams = Dictionary.new;
    8.do { |i|
        var slot = i + 1;
        ~genParams[slot] = Dictionary.new;
        ~genParams[slot][\frequency] = Bus.control(s, 1).set(0.5);
        ~genParams[slot][\cutoff] = Bus.control(s, 1).set(0.5);
        ~genParams[slot][\resonance] = Bus.control(s, 1).set(0.5);
        ~genParams[slot][\attack] = Bus.control(s, 1).set(0.5);
        ~genParams[slot][\decay] = Bus.control(s, 1).set(0.5);
        ~genParams[slot][\filterType] = Bus.control(s, 1).set(0);
        ~genParams[slot][\envEnabled] = Bus.control(s, 1).set(0);
        ~genParams[slot][\clockDiv] = Bus.control(s, 1).set(1);
    };
    
    // Audio buses
    ~masterBus = Bus.audio(s, 2);
    
    // Generator instances
    ~generators = Dictionary.new;
    ~masterEffects = nil;
    
    // Helper function to start any generator with standard params
    ~startGenerator = { |slotID, genType|
        var params = ~genParams[slotID];
        
        if(~generators[slotID].notNil, {
            ~generators[slotID].free;
            ~generators[slotID] = nil;
        });
        
        ~generators[slotID] = Synth(genType, [
            \out, ~masterBus,
            \freqBus, params[\frequency].index,
            \cutoffBus, params[\cutoff].index,
            \resBus, params[\resonance].index,
            \attackBus, params[\attack].index,
            \decayBus, params[\decay].index,
            \filterTypeBus, params[\filterType].index,
            \envEnabledBus, params[\envEnabled].index,
            \clockDivBus, params[\clockDiv].index
        ], addAction: \addToHead);
        
        "Started % in slot %".format(genType, slotID).postln;
    };
    
    // Load generators from files
    "Loading generators...".postln;
    ~generatorsPath = PathName(thisProcess.nowExecutingPath).parentPath +/+ "generators/";
    (~generatorsPath +/+ "test_synth.scd").load;
    (~generatorsPath +/+ "pt2399_grainy.scd").load;
    
    // Master passthrough with fidelity effect
    SynthDef(\masterPassthrough, { |inBus, outBus=0, fidelityAmount=1.0|
        var sig;
        sig = In.ar(inBus, 2);
        sig = sig.round(2.pow(fidelityAmount.linexp(0, 1, 4, 16)).reciprocal * 2) - 1;
        sig = Latch.ar(sig, Impulse.ar(fidelityAmount.linexp(0, 1, 4000, 44100)));
        sig = LPF.ar(sig, fidelityAmount.linexp(0, 1, 2000, 18000));
        Out.ar(outBus, sig);
    }).add;
    
    // ========== OSC HANDLERS ==========
    
    // Global
    OSCdef(\gravity, { |msg| ~params[\gravity].set(msg[1]); }, '/noise/gravity');
    OSCdef(\density, { |msg| ~params[\density].set(msg[1]); }, '/noise/density');
    OSCdef(\filterCutoff, { |msg| ~params[\filter_cutoff].set(msg[1]); }, '/noise/filter_cutoff');
    OSCdef(\amplitude, { |msg| ~params[\amplitude].set(msg[1]); }, '/noise/amplitude');
    OSCdef(\fidelityAmount, { |msg|
        if(~masterEffects.notNil, { ~masterEffects.set(\fidelityAmount, msg[1]); });
    }, '/noise/fidelity_amount');
    
    // Per-generator
    OSCdef(\genFrequency, { |msg|
        ~genParams[msg[1].asInteger][\frequency].set(msg[2].asFloat);
    }, '/noise/gen/frequency');
    
    OSCdef(\genCutoff, { |msg|
        ~genParams[msg[1].asInteger][\cutoff].set(msg[2].asFloat);
    }, '/noise/gen/cutoff');
    
    OSCdef(\genResonance, { |msg|
        ~genParams[msg[1].asInteger][\resonance].set(msg[2].asFloat);
    }, '/noise/gen/resonance');
    
    OSCdef(\genAttack, { |msg|
        ~genParams[msg[1].asInteger][\attack].set(msg[2].asFloat);
    }, '/noise/gen/attack');
    
    OSCdef(\genDecay, { |msg|
        ~genParams[msg[1].asInteger][\decay].set(msg[2].asFloat);
    }, '/noise/gen/decay');
    
    OSCdef(\genFilterType, { |msg|
        ~genParams[msg[1].asInteger][\filterType].set(msg[2].asInteger);
    }, '/noise/gen/filterType');
    
    OSCdef(\genEnvEnabled, { |msg|
        ~genParams[msg[1].asInteger][\envEnabled].set(msg[2].asInteger);
    }, '/noise/gen/envEnabled');
    
    OSCdef(\genClockDiv, { |msg|
        ~genParams[msg[1].asInteger][\clockDiv].set(msg[2].asInteger);
    }, '/noise/gen/clockDiv');
    
    // Generator control
    OSCdef(\startGenerator, { |msg|
        ~startGenerator.(msg[1].asInteger, msg[2].asSymbol);
    }, '/noise/start_generator');
    
    OSCdef(\stopGenerator, { |msg|
        var slotID = msg[1].asInteger;
        if(~generators[slotID].notNil, {
            ~generators[slotID].free;
            ~generators[slotID] = nil;
            "Stopped generator in slot %".format(slotID).postln;
        });
    }, '/noise/stop_generator');
    
    s.sync;
    
    ~masterEffects = Synth(\masterPassthrough, [
        \inBus, ~masterBus,
        \outBus, 0,
        \fidelityAmount, 1.0
    ], addAction: \addToTail);
    
    "".postln;
    "✓ Noise Engine ready!".postln;
    "✓ ENV OFF = drone, ENV ON = triggered".postln;
    "".postln;
    "Listening for OSC on port 57120".postln;
});
