/*
FX Mixer
Sums dry signal + FX returns into masterBus
Part of FX System Phase 1 (UI Refresh expansion to 4 slots)

Signal flow:
  ~drySumBus (channel strips) ──┐
  ~fx1ReturnBus x fx1Return ────┼──► ~masterBus
  ~fx2ReturnBus x fx2Return ────┤
  ~fx3ReturnBus x fx3Return ────┤
  ~fx4ReturnBus x fx4Return ────┘
*/

~setupFxMixer = {
    "Setting up FX mixer...".postln;

    // Return level defaults (4 slots)
    ~fx1ReturnLevel = 0.5;
    ~fx2ReturnLevel = 0.3;
    ~fx3ReturnLevel = 0.3;
    ~fx4ReturnLevel = 0.3;

    // Legacy aliases for backward compat
    ~echoReturnLevel = ~fx1ReturnLevel;
    ~verbReturnLevel = ~fx2ReturnLevel;

    SynthDef(\preMasterMixer, { |drySumBus,
                                  fx1ReturnBus, fx2ReturnBus, fx3ReturnBus, fx4ReturnBus,
                                  outBus,
                                  fx1Return=0.5, fx2Return=0.3, fx3Return=0.3, fx4Return=0.3|
        var dry, fx1Rtn, fx2Rtn, fx3Rtn, fx4Rtn, mixed;

        // Read inputs
        dry = In.ar(drySumBus, 2);
        fx1Rtn = In.ar(fx1ReturnBus, 2) * Lag.kr(fx1Return, 0.02);
        fx2Rtn = In.ar(fx2ReturnBus, 2) * Lag.kr(fx2Return, 0.02);
        fx3Rtn = In.ar(fx3ReturnBus, 2) * Lag.kr(fx3Return, 0.02);
        fx4Rtn = In.ar(fx4ReturnBus, 2) * Lag.kr(fx4Return, 0.02);

        // Sum all
        mixed = dry + fx1Rtn + fx2Rtn + fx3Rtn + fx4Rtn;

        // Write to master bus
        ReplaceOut.ar(outBus, mixed);
    }).add;

    "  [x] FX mixer SynthDef ready (4 returns)".postln;
};

~startFxMixer = {
    ~fxMixer = Synth(\preMasterMixer, [
        \drySumBus, ~drySumBus,
        \fx1ReturnBus, ~fx1ReturnBus,
        \fx2ReturnBus, ~fx2ReturnBus,
        \fx3ReturnBus, ~fx3ReturnBus,
        \fx4ReturnBus, ~fx4ReturnBus,
        \outBus, ~masterBus,
        \fx1Return, ~fx1ReturnLevel,
        \fx2Return, ~fx2ReturnLevel,
        \fx3Return, ~fx3ReturnLevel,
        \fx4Return, ~fx4ReturnLevel
    ], ~mixerGroup, \addToTail);

    "  [x] FX mixer running".postln;
};

// OSC handlers for return levels
~setupFxMixerOSC = {
    // Generic slot return handlers
    4.do { |i|
        var slotNum = i + 1;
        OSCdef(("fxReturn" ++ slotNum).asSymbol, { |msg|
            var level = msg[1].clip(0, 1);
            switch(i,
                0, { ~fx1ReturnLevel = level; ~fxMixer.set(\fx1Return, level) },
                1, { ~fx2ReturnLevel = level; ~fxMixer.set(\fx2Return, level) },
                2, { ~fx3ReturnLevel = level; ~fxMixer.set(\fx3Return, level) },
                3, { ~fx4ReturnLevel = level; ~fxMixer.set(\fx4Return, level) }
            );
        }, '/noise/fx/slot/' ++ slotNum ++ '/return_level');
    };

    // Legacy echo/verb return handlers (backward compat)
    OSCdef(\echoReturn, { |msg|
        var level = msg[1].clip(0, 1);
        ~fx1ReturnLevel = level;
        ~echoReturnLevel = level;
        if(~fxMixer.notNil) {
            ~fxMixer.set(\fx1Return, level);
        };
    }, '/noise/master/echo/return');

    OSCdef(\verbReturn, { |msg|
        var level = msg[1].clip(0, 1);
        ~fx2ReturnLevel = level;
        ~verbReturnLevel = level;
        if(~fxMixer.notNil) {
            ~fxMixer.set(\fx2Return, level);
        };
    }, '/noise/master/verb/return');

    "  [x] FX mixer OSC handlers ready".postln;
};
