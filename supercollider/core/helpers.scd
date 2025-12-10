/*
Helper Functions
Reusable functions for generator management
*/

~setupHelpers = {
    "Setting up helpers...".postln;
    
    // Start any generator with standard params
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
            \clockDivBus, params[\clockDiv].index,
            \clockTrigBus, ~clockTrigBus.index
        ], addAction: \addToHead);
        
        "Started % in slot %".format(genType, slotID).postln;
    };
    
    // Stop generator
    ~stopGenerator = { |slotID|
        if(~generators[slotID].notNil, {
            ~generators[slotID].free;
            ~generators[slotID] = nil;
            "Stopped generator in slot %".format(slotID).postln;
        });
    };
    
    "  ✓ Helpers ready".postln;
};
