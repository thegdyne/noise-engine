/*
FX Mixer
Sums dry signal + FX returns into masterBus
Part of FX System Phase 1

Signal flow:
  ~drySumBus (channel strips) ──┐
  ~echoReturnBus × echoReturn ──┼──► ~masterBus
  ~verbReturnBus × verbReturn ──┘
*/

~setupFxMixer = {
    "Setting up FX mixer...".postln;
    
    // Return level defaults
    ~echoReturnLevel = 0.5;
    ~verbReturnLevel = 0.3;
    
    SynthDef(\preMasterMixer, { |drySumBus, echoReturnBus, verbReturnBus, outBus,
                                  echoReturn=0.5, verbReturn=0.3|
        var dry, echoRtn, verbRtn, mixed;
        
        // Read inputs
        dry = In.ar(drySumBus, 2);
        echoRtn = In.ar(echoReturnBus, 2) * Lag.kr(echoReturn, 0.02);
        verbRtn = In.ar(verbReturnBus, 2) * Lag.kr(verbReturn, 0.02);
        
        // Sum
        mixed = dry + echoRtn + verbRtn;
        
        // Write to master bus
        ReplaceOut.ar(outBus, mixed);
    }).add;
    
    "  ✓ FX mixer SynthDef ready".postln;
};

~startFxMixer = {
    ~fxMixer = Synth(\preMasterMixer, [
        \drySumBus, ~drySumBus,
        \echoReturnBus, ~echoReturnBus,
        \verbReturnBus, ~verbReturnBus,
        \outBus, ~masterBus,
        \echoReturn, ~echoReturnLevel,
        \verbReturn, ~verbReturnLevel
    ], ~mixerGroup, \addToTail);
    
    "  ✓ FX mixer running".postln;
};

// OSC handlers for return levels
~setupFxMixerOSC = {
    OSCdef(\echoReturn, { |msg|
        var level = msg[1].clip(0, 1);
        ~echoReturnLevel = level;
        if(~fxMixer.notNil) {
            ~fxMixer.set(\echoReturn, level);
        };
    }, '/noise/master/echo/return');
    
    OSCdef(\verbReturn, { |msg|
        var level = msg[1].clip(0, 1);
        ~verbReturnLevel = level;
        if(~fxMixer.notNil) {
            ~fxMixer.set(\verbReturn, level);
        };
    }, '/noise/master/verb/return');
    
    "  ✓ FX mixer OSC handlers ready".postln;
};
