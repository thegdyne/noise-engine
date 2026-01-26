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

Return levels support bus unification for boid modulation:
  fx1ReturnModBus = -1 means use direct fx1Return value
  fx1ReturnModBus >= 0 means read from unified bus
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
                                  fx1Return=0.5, fx2Return=0.3, fx3Return=0.3, fx4Return=0.3,
                                  fx1ReturnModBus=(-1), fx2ReturnModBus=(-1),
                                  fx3ReturnModBus=(-1), fx4ReturnModBus=(-1)|
        var dry, fx1Rtn, fx2Rtn, fx3Rtn, fx4Rtn, mixed;
        var fx1ReturnEff, fx2ReturnEff, fx3ReturnEff, fx4ReturnEff;

        // Bus unification for return levels (allows boid modulation)
        fx1ReturnEff = Select.kr(fx1ReturnModBus >= 0, [fx1Return, In.kr(fx1ReturnModBus)]);
        fx2ReturnEff = Select.kr(fx2ReturnModBus >= 0, [fx2Return, In.kr(fx2ReturnModBus)]);
        fx3ReturnEff = Select.kr(fx3ReturnModBus >= 0, [fx3Return, In.kr(fx3ReturnModBus)]);
        fx4ReturnEff = Select.kr(fx4ReturnModBus >= 0, [fx4Return, In.kr(fx4ReturnModBus)]);

        // Read inputs with smoothed return levels
        dry = In.ar(drySumBus, 2);
        fx1Rtn = In.ar(fx1ReturnBus, 2) * Lag.kr(fx1ReturnEff, 0.02);
        fx2Rtn = In.ar(fx2ReturnBus, 2) * Lag.kr(fx2ReturnEff, 0.02);
        fx3Rtn = In.ar(fx3ReturnBus, 2) * Lag.kr(fx3ReturnEff, 0.02);
        fx4Rtn = In.ar(fx4ReturnBus, 2) * Lag.kr(fx4ReturnEff, 0.02);

        // Sum all
        mixed = dry + fx1Rtn + fx2Rtn + fx3Rtn + fx4Rtn;

        // Write to master bus
        ReplaceOut.ar(outBus, mixed);
    }).add;

    "  [x] FX mixer SynthDef ready (4 returns with mod bus support)".postln;
};

~startFxMixer = {
    // Get mod bus indices for return levels from unified bus system
    // These enable boid modulation of FX return levels
    var fx1ReturnModBusIdx = ~getBusIndex.(\fx_slot1_return) ? -1;
    var fx2ReturnModBusIdx = ~getBusIndex.(\fx_slot2_return) ? -1;
    var fx3ReturnModBusIdx = ~getBusIndex.(\fx_slot3_return) ? -1;
    var fx4ReturnModBusIdx = ~getBusIndex.(\fx_slot4_return) ? -1;

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
        \fx4Return, ~fx4ReturnLevel,
        \fx1ReturnModBus, fx1ReturnModBusIdx,
        \fx2ReturnModBus, fx2ReturnModBusIdx,
        \fx3ReturnModBus, fx3ReturnModBusIdx,
        \fx4ReturnModBus, fx4ReturnModBusIdx
    ], ~mixerGroup, \addToTail);

    "  [x] FX mixer running (mod bus wired)".postln;
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
