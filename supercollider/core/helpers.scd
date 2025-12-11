/*
Helper Functions
Reusable functions for generator management
*/

~setupHelpers = {
    "Setting up helpers...".postln;
    
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
                \clockRateBus, params[\clockRate].index,
                \clockTrigBus, ~clockTrigBus.index,
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
