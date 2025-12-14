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
    
    SynthDef(\channelStrip, { |inBus, outBus, vol=0.8, mute=0, solo=0, gain=1.0, pan=0, genTrim=0, soloActiveBus, slotID=1|
        var sig, soloActive, soloGate, ampL, ampR;
        
        // Read stereo from per-generator bus (dual mono or true stereo)
        sig = In.ar(inBus, 2);
        
        // Generator trim (loudness normalization from JSON config)
        // Applied first, before any other processing
        // genTrim is in dB (0 = unity, -6 = half amplitude)
        sig = sig * genTrim.dbamp;
        
        // Read global solo state
        soloActive = In.kr(soloActiveBus);
        
        // Mute: silence this channel (applied first)
        sig = sig * (1 - mute);
        
        // Solo-in-place logic:
        // If no solos active (soloActive=0): all unmuted channels pass
        // If any solo active (soloActive=1): only soloed channels pass
        soloGate = Select.kr(soloActive, [1, solo]);
        sig = sig * soloGate;
        
        // Gain stage (0dB=1.0, +6dB=2.0, +12dB=4.0)
        sig = sig * gain;
        
        // Pan using Balance2 (-1=L, 0=center, 1=R)
        // For dual mono: behaves like Pan2
        // For true stereo: shifts balance while preserving stereo image
        sig = Balance2.ar(sig[0], sig[1], pan);
        
        // Volume (applied last)
        sig = sig * vol;
        
        // Per-channel metering (post-fader, 24fps)
        ampL = Amplitude.kr(sig[0], 0.01, 0.1);
        ampR = Amplitude.kr(sig[1], 0.01, 0.1);
        SendReply.kr(Impulse.kr(24), '/noise/gen/levels', [slotID, ampL, ampR]);
        
        Out.ar(outBus, sig);
    }).add;
    
    // Mute state tracking (parallel to solo tracking)
    ~stripMuteState = Array.fill(8, { 0 });
    
    // Gain state tracking (linear multiplier: 1.0, 2.0, or 4.0)
    ~stripGainState = Array.fill(8, { 1.0 });
    
    // Pan state tracking (-1 to 1, 0=center)
    ~stripPanState = Array.fill(8, { 0 });
    
    // Trim state tracking (dB, from generator JSON config)
    ~stripTrimState = Array.fill(8, { 0.0 });
    
    "  ✓ Channel strip SynthDef ready (with metering + trim)".postln;
};

// Start a channel strip for a slot (called when generator starts)
~startChannelStrip = { |slotID|
    var idx = slotID - 1;  // 0-indexed
    var currentMute, currentSolo, currentGain, currentPan, currentTrim;
    
    // Store current state before freeing (if strip exists)
    currentMute = ~stripMuteState[idx] ? 0;
    currentSolo = ~stripSoloState[idx] ? 0;
    currentGain = ~stripGainState[idx] ? 1.0;
    currentPan = ~stripPanState[idx] ? 0;
    currentTrim = ~stripTrimState[idx] ? 0.0;
    
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
        \gain, currentGain,
        \pan, currentPan,
        \genTrim, currentTrim,
        \soloActiveBus, ~soloActive.index,
        \slotID, slotID  // Pass slot ID for metering
    ], ~stripGroup, \addToTail);
    
    "  Started channel strip for slot % (mute:%, solo:%, gain:%, pan:%, trim:%dB)".format(slotID, currentMute, currentSolo, currentGain, currentPan, currentTrim).postln;
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

// Forward channel meter replies to Python (must be called after ~pythonAddr is set)
~setupChannelMeterForward = {
    OSCdef(\channelMeterForward, { |msg|
        // msg format: ['/noise/gen/levels', node_id, reply_id, slotID, ampL, ampR]
        ~pythonAddr.sendMsg('/noise/gen/levels', msg[3].asInteger, msg[4], msg[5]);
    }, '/noise/gen/levels');
    "  ✓ Channel meter forwarding ready".postln;
};
