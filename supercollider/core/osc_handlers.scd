/*
OSC Handlers
All OSC message routing
*/

~setupOSC = {
    "Setting up OSC handlers...".postln;
    
    // Master clock BPM
    OSCdef(\clockBPM, { |msg|
        ~clockBus.set(msg[1]);
    }, '/noise/clock/bpm');
    
    // Global parameters
    OSCdef(\gravity, { |msg| ~params[\gravity].set(msg[1]); }, '/noise/gravity');
    OSCdef(\density, { |msg| ~params[\density].set(msg[1]); }, '/noise/density');
    OSCdef(\filterCutoff, { |msg| ~params[\filter_cutoff].set(msg[1]); }, '/noise/filter_cutoff');
    OSCdef(\amplitude, { |msg| ~params[\amplitude].set(msg[1]); }, '/noise/amplitude');
    OSCdef(\fidelityAmount, { |msg|
        if(~masterEffects.notNil, { ~masterEffects.set(\fidelityAmount, msg[1]); });
    }, '/noise/fidelity_amount');
    
    // Per-generator parameters
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
    
    OSCdef(\genClockRate, { |msg|
        // Rate index: 0=x8, 1=x4, 2=x2, 3=CLK, 4=/2, 5=/4, 6=/8, 7=/16
        ~genParams[msg[1].asInteger][\clockRate].set(msg[2].asInteger);
        "Gen % clock rate index: %".format(msg[1], msg[2]).postln;
    }, '/noise/gen/clockRate');
    
    // Generator control
    OSCdef(\startGenerator, { |msg|
        ~startGenerator.(msg[1].asInteger, msg[2].asSymbol);
    }, '/noise/start_generator');
    
    OSCdef(\stopGenerator, { |msg|
        ~stopGenerator.(msg[1].asInteger);
    }, '/noise/stop_generator');
    
    "  ✓ OSC handlers ready".postln;
};
