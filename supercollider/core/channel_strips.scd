/*
Channel Strips
Per-generator volume, mute, and solo processing

Signal flow: ~genBus[n] → channelStrip → ~masterBus

Each generator slot gets its own channel strip synth that runs
after the generator but before master effects.
*/

~setupChannelStrips = {
    "Setting up channel strips...".postln;
    
    SynthDef(\channelStrip, { |inBus, outBus, vol=0.8, mute=0, solo=0, soloActiveBus|
        var sig, soloActive;
        
        // Read from per-generator bus
        sig = In.ar(inBus, 2);
        
        // Read global solo state
        soloActive = In.kr(soloActiveBus);
        
        // Mute: silence this channel
        sig = sig * (1 - mute);
        
        // Solo-in-place: when any channel is soloed, only soloed channels pass
        // If soloActive=0: pass all (multiply by 1)
        // If soloActive=1: pass only if solo=1 (multiply by solo)
        sig = sig * Select.kr(soloActive, [1, solo]);
        
        // Volume
        sig = sig * vol;
        
        Out.ar(outBus, sig);
    }).add;
    
    "  ✓ Channel strip SynthDef ready".postln;
};

// Start a channel strip for a slot (called when generator starts)
~startChannelStrip = { |slotID|
    var idx = slotID - 1;  // 0-indexed
    
    if(~channelStrips[idx].isNil, {
        ~channelStrips[idx] = Synth(\channelStrip, [
            \inBus, ~genBus[idx],
            \outBus, ~masterBus,
            \vol, 0.8,
            \mute, 0,
            \solo, 0,
            \soloActiveBus, ~soloActive.index
        ], ~stripGroup, \addToTail);
        
        "  Started channel strip for slot %".format(slotID).postln;
    });
};

// Stop a channel strip for a slot (called when generator stops)
~stopChannelStrip = { |slotID|
    var idx = slotID - 1;
    
    if(~channelStrips[idx].notNil, {
        // If this strip was soloed, decrement solo count
        if(~stripSoloState[idx] == 1, {
            ~soloCount = ~soloCount - 1;
            ~stripSoloState[idx] = 0;
            ~soloActive.set(if(~soloCount > 0, 1, 0));
        });
        
        ~channelStrips[idx].free;
        ~channelStrips[idx] = nil;
        
        "  Stopped channel strip for slot %".format(slotID).postln;
    });
};
