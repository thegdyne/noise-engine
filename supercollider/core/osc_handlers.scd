/*
OSC Handlers
All OSC message routing
*/

~setupOSC = {
    "Setting up OSC handlers...".postln;
    
    // === CONNECTION MANAGEMENT ===
    // Ping/pong for connection verification
    // Python sends /noise/ping, SC responds with /noise/pong
    // Send to fixed port 57121 where Python listens
    ~pythonAddr = NetAddr("127.0.0.1", 57121);
    
    OSCdef(\ping, { |msg, time, addr|
        ~pythonAddr.sendMsg('/noise/pong', 1);
    }, '/noise/ping');
    
    // Heartbeat - Python sends periodically, SC responds
    // If Python misses responses, it knows connection is dead
    OSCdef(\heartbeat, { |msg, time, addr|
        ~pythonAddr.sendMsg('/noise/heartbeat_ack', 1);
    }, '/noise/heartbeat');
    
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
    
    // Envelope source: 0=OFF, 1=CLK, 2=MIDI
    OSCdef(\genEnvSource, { |msg|
        var slot = msg[1].asInteger;
        var source = msg[2].asInteger;
        ~genParams[slot][\envSource].set(source);
        ("Gen " ++ slot ++ " env source: " ++ ["OFF", "CLK", "MIDI"][source]).postln;
    }, '/noise/gen/envSource');
    
    OSCdef(\genClockRate, { |msg|
        // Rate index: 0=/32 ... 6=CLK ... 12=x32
        ~genParams[msg[1].asInteger][\clockRate].set(msg[2].asInteger);
    }, '/noise/gen/clockRate');
    
    // Per-generator custom parameters
    // Path format: /noise/gen/custom/{slot}/{param_index}
    8.do { |i|
        var slot = i + 1;
        5.do { |p|
            OSCdef(("genCustom" ++ slot ++ "_" ++ p).asSymbol, { |msg|
                ~genParams[slot][\custom][p].set(msg[1].asFloat);
            }, "/noise/gen/custom/" ++ slot ++ "/" ++ p);
        };
    };
    
    // Generator control
    OSCdef(\startGenerator, { |msg|
        ~startGenerator.(msg[1].asInteger, msg[2].asSymbol);
    }, '/noise/start_generator');
    
    OSCdef(\stopGenerator, { |msg|
        ~stopGenerator.(msg[1].asInteger);
    }, '/noise/stop_generator');
    
    "  ✓ OSC handlers ready".postln;
};
