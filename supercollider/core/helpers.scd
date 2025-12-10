/*
Helper Functions
Reusable functions for generator management
*/

~setupHelpers = {
    "Setting up helpers...".postln;
    
    ~startGenerator = { |slotID, genType|
        var params = ~genParams[slotID];
        
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
                \clockRateBus, params[\clockRate].index,
                \clockTrigBus, ~clockTrigBus.index
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
