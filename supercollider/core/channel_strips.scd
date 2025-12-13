/*
Channel Strips
Per-generator volume, mute, and solo processing

Signal flow: ~genBus[n] → channelStrip → ~masterBus

Each generator slot gets its own channel strip synth that runs
after the generator but before master effects.

Solo logic:
- soloActive = 1 if ANY channel is soloed
- When soloActive=1, only channels with solo=1 pass audio
- Mute is applied first, then solo check
*/

~setupChannelStrips = {
    "Setting up channel strips...".postln;
    
    SynthDef(\channelStrip, { |inBus, outBus, vol=0.8, mute=0, solo=0, soloActiveBus|
        var sig, soloActive, soloGate;
        
        // Read from per-generator bus
        sig = In.ar(inBus, 2);
        
        // Read global solo state
        soloActive = In.kr(soloActiveBus);
        
        // Mute: silence this channel (applied first)
        sig = sig * (1 - mute);
        
        // Solo-in-place logic:
        // If no solos active (soloActive=0): all unmuted channels pass
        // If any solo active (soloActive=1): only soloed channels pass
        soloGate = Select.kr(soloActive, [1, solo]);
        sig = sig * soloGate;
        
        // Volume (applied last)
        sig = sig * vol;
        
        Out.ar(outBus, sig);
    }).add;
    
    // Mute state tracking (parallel to solo tracking)
    ~stripMuteState = Array.fill(8, { 0 });
    
    "  ✓ Channel strip SynthDef ready".postln;
};

// Start a channel strip for a slot (called when generator starts)
~startChannelStrip = { |slotID|
    var idx = slotID - 1;  // 0-indexed
    var currentMute, currentSolo;
    
    // Store current state before freeing (if strip exists)
    currentMute = ~stripMuteState[idx] ? 0;
    currentSolo = ~stripSoloState[idx] ? 0;
    
    // Free existing strip if any
    if(~channelStrips[idx].notNil, {
        ~channelStrips[idx].free;
        ~channelStrips[idx] = nil;
    });
    
    // Create new strip with preserved state
    ~channelStrips[idx] = Synth(\channelStrip, [
        \inBus, ~genBus[idx],
        \outBus, ~masterBus,
        \vol, 0.8,
        \mute, currentMute,
        \solo, currentSolo,
        \soloActiveBus, ~soloActive.index
    ], ~stripGroup, \addToTail);
    
    "  Started channel strip for slot % (mute:%, solo:%)".format(slotID, currentMute, currentSolo).postln;
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
            ("  Cleared solo for slot % (soloCount now %)".format(slotID, ~soloCount)).postln;
        });
        
        ~channelStrips[idx].free;
        ~channelStrips[idx] = nil;
        
        "  Stopped channel strip for slot %".format(slotID).postln;
    });
};

// Debug helper - call from SC to check state
~debugSoloState = {
    "=== Solo State ===".postln;
    ("soloCount: " ++ ~soloCount).postln;
    ("soloActive bus: " ++ ~soloActive.getSynchronous).postln;
    8.do { |i|
        var state = ~stripSoloState[i];
        var strip = ~channelStrips[i];
        ("  Slot %: solo=%, strip=%".format(i+1, state, if(strip.notNil, "active", "nil"))).postln;
    };
};
