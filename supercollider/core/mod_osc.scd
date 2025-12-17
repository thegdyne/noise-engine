/*
Mod OSC Handlers
OSC message handling for modulation sources

Paths:
  /noise/mod/generator/{slot}           - set generator type
  /noise/mod/param/{slot}/{key}         - set parameter value
  /noise/mod/out/wave/{slot}/{output}   - set output waveform (LFO)
  /noise/mod/out/pol/{slot}/{output}    - set output polarity
  /noise/mod/scope/enable/{slot}        - enable scope streaming
*/

~setupModOSC = {
    "Setting up mod OSC handlers...".postln;
    
    // Scope streaming state (which slots to send bus values for)
    ~modScopeEnabled = Array.fill(4, { false });
    
    // Generator selection: /noise/mod/generator/{slot} genName
    OSCdef(\modGenerator, { |msg|
        var slot = msg[1].asInteger;
        var genName = msg[2].asString;
        
        if(slot >= 1 && slot <= 4) {
            ~startModSlot.(slot, genName);
        } {
            ("Mod generator: invalid slot " ++ slot).warn;
        };
    }, '/noise/mod/generator');
    
    // Parameter change: /noise/mod/param/{slot}/{key} value
    OSCdef(\modParam, { |msg|
        var slot = msg[1].asInteger;
        var key = msg[2].asString;
        var value = msg[3].asFloat;
        
        if(slot >= 1 && slot <= 4) {
            ~setModParam.(slot, key, value);
        };
    }, '/noise/mod/param');
    
    // Output waveform: /noise/mod/out/wave/{slot}/{output} waveIndex
    OSCdef(\modOutputWave, { |msg|
        var slot = msg[1].asInteger;
        var output = msg[2].asInteger;  // 0-3 (4 outputs)
        var waveIndex = msg[3].asInteger;
        
        if(slot >= 1 && slot <= 4 && output >= 0 && output <= 3) {
            ~setModOutputWave.(slot, output, waveIndex);
        };
    }, '/noise/mod/out/wave');
    
    // Output polarity: /noise/mod/out/pol/{slot}/{output} polarity
    OSCdef(\modOutputPolarity, { |msg|
        var slot = msg[1].asInteger;
        var output = msg[2].asInteger;  // 0-3 (4 outputs)
        var polarity = msg[3].asInteger;  // 0=UNI, 1=BI
        
        if(slot >= 1 && slot <= 4 && output >= 0 && output <= 3) {
            ~setModOutputPolarity.(slot, output, polarity);
        };
    }, '/noise/mod/out/pol');
    
    // Scope enable: /noise/mod/scope/enable/{slot} enabled
    OSCdef(\modScopeEnable, { |msg|
        var slot = msg[1].asInteger;
        var enabled = msg[2].asInteger == 1;
        
        if(slot >= 1 && slot <= 4) {
            ~modScopeEnabled[slot - 1] = enabled;
            // Auto-start/stop streaming
            if(enabled) {
                ~startModScope.();
            } {
                if(~modScopeEnabled.any({ |x| x }).not) {
                    ~stopModScope.();
                };
            };
        };
    }, '/noise/mod/scope/enable');
    
    // Scope streaming routine (~30fps)
    ~modScopeRoutine = Routine({
        var netAddr = ~pythonAddr;
        
        loop {
            4.do { |idx|
                var slot = idx + 1;
                if(~modScopeEnabled[idx]) {
                    // Send 4 bus values for this slot (quadrature)
                    4.do { |out|
                        var busIdx = ~modBusIndex.(slot, out);
                        var value = ~modBuses[busIdx].getSynchronous;
                        netAddr.sendMsg('/noise/mod/bus/value', busIdx, value);
                    };
                };
            };
            (1/30).wait;  // ~30fps
        };
    });
    
    // Start scope streaming
    ~startModScope = {
        if(~modScopeRoutine.isPlaying.not) {
            ~modScopeRoutine.reset;
            ~modScopeRoutine.play(AppClock);
            "  Mod scope streaming started".postln;
        };
    };
    
    // Stop scope streaming
    ~stopModScope = {
        ~modScopeRoutine.stop;
        "  Mod scope streaming stopped".postln;
    };
    
    "  ✓ Mod OSC handlers ready (4 outputs per slot)".postln;
};
