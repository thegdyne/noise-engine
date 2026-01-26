/*
Channel Strips
Per-generator volume, mute, solo, and EQ processing

Signal flow: ~genBus[n] -> channelStrip -> ~masterBus

Each generator slot gets its own channel strip synth that runs
after the generator but before master effects.

Solo logic:
- soloActive = 1 if ANY channel is soloed
- When soloActive=1, only channels with solo=1 pass audio
- Mute is applied first, then solo check

EQ: 3-band DJ isolator
- Crossover freqs: ~eqLoXover (250Hz), ~eqHiXover (2500Hz)
- Uses remainder-mid for perfect reconstruction at unity
- 24dB/oct cascaded Butterworth (NOT Linkwitz-Riley, but doesn't matter)
*/

~setupChannelStrips = {
    "Setting up channel strips...".postln;
    
    // === SSOT: EQ Crossover Frequencies ===
    // Change here to change everywhere (strip + master EQ should share these)
    ~eqLoXover = 250;   // Hz - below this is LO band
    ~eqHiXover = 2500;  // Hz - above this is HI band
    ~eqSmoothTime = 0.02;  // Seconds - lag time for zipper-free knobs
    
    // === SSOT: DJ Isolator Helper ===
    // 3-band split with remainder-mid for perfect reconstruction at unity
    // loGain/midGain/hiGain: 0=kill, 1=unity, 2=+6dB (linear amplitude)
    ~djIsolator = { |sig, loGain=1, midGain=1, hiGain=1|
        var lo, hi, mid;
        var loG, midG, hiG;
        
        // Smooth gains to prevent clicks/zipper noise
        loG = Lag.kr(loGain, ~eqSmoothTime);
        midG = Lag.kr(midGain, ~eqSmoothTime);
        hiG = Lag.kr(hiGain, ~eqSmoothTime);
        
        // Split bands (24dB/oct cascaded Butterworth)
        lo = LPF.ar(LPF.ar(sig, ~eqLoXover), ~eqLoXover);
        hi = HPF.ar(HPF.ar(sig, ~eqHiXover), ~eqHiXover);
        mid = sig - lo - hi;  // Remainder = perfect mid, no phase issues
        
        // Apply gains and recombine
        (lo * loG) + (mid * midG) + (hi * hiG)
    };
    
    // === SSOT: Bounds-checked slot helper ===
    // Use this in all OSC handlers for consistent validation
    ~withValidSlot = { |slot, action|
        var idx = slot - 1;
        if(idx >= 0 && idx < 8, {
            action.(idx);
        }, {
            "WARNING: Invalid slot % in OSC message".format(slot).postln;
        });
    };
    
    SynthDef(\channelStrip, { |inBus, outBus, vol=0.8, mute=0, solo=0, gain=1.0, pan=0,
                              genTrim=0, soloActiveBus, slotID=1,
                              eqLo=1, eqMid=1, eqHi=1,
                              fx1Send=0, fx2Send=0, fx3Send=0, fx4Send=0,
                              fx1SendBus, fx2SendBus, fx3SendBus, fx4SendBus,
                              fx1SendModBus=(-1), fx2SendModBus=(-1), fx3SendModBus=(-1), fx4SendModBus=(-1),
                              panModBus=(-1)|
        var sig, soloActive, soloGate, ampL, ampR;
        var fx1SendEff, fx2SendEff, fx3SendEff, fx4SendEff, panEff;

        // Bus unification: read from bus if valid index, otherwise use direct arg
        fx1SendEff = Select.kr(fx1SendModBus >= 0, [fx1Send, In.kr(fx1SendModBus)]);
        fx2SendEff = Select.kr(fx2SendModBus >= 0, [fx2Send, In.kr(fx2SendModBus)]);
        fx3SendEff = Select.kr(fx3SendModBus >= 0, [fx3Send, In.kr(fx3SendModBus)]);
        fx4SendEff = Select.kr(fx4SendModBus >= 0, [fx4Send, In.kr(fx4SendModBus)]);
        panEff = Select.kr(panModBus >= 0, [pan, In.kr(panModBus)]);

        // Read stereo from per-generator bus (dual mono or true stereo)
        sig = In.ar(inBus, 2);
        
        // Generator trim (loudness normalization from JSON config)
        // Applied first, with smoothing for large dB jumps
        sig = sig * Lag.kr(genTrim, 0.05).dbamp;
        
        // 3-band EQ using shared isolator helper
        sig = ~djIsolator.(sig, eqLo, eqMid, eqHi);
        
        // Read global solo state
        soloActive = In.kr(soloActiveBus);
        
        // Mute: silence this channel (applied first)
        sig = sig * (1 - mute);
        
        // Solo-in-place logic:
        // If no solos active (soloActive=0): all unmuted channels pass
        // If any solo active (soloActive=1): only soloed channels pass
        soloGate = Select.kr(soloActive, [1, solo]);
        sig = sig * soloGate;
        
        // Gain stage with smoothing (0dB=1.0, +6dB=2.0, +12dB=4.0)
        sig = sig * Lag.kr(gain, ~eqSmoothTime);
        
        // Pan using Balance2 (-1=L, 0=center, 1=R) with smoothing
        sig = Balance2.ar(sig[0], sig[1], Lag.kr(panEff, ~eqSmoothTime));
        
        // Volume with smoothing (applied last)
        sig = sig * Lag.kr(vol, ~eqSmoothTime);
        
        // Per-channel metering (post-fader, 24fps)
        ampL = Amplitude.kr(sig[0], 0.01, 0.1);
        ampR = Amplitude.kr(sig[1], 0.01, 0.1);
        SendReply.kr(Impulse.kr(24), '/noise/gen/levels', [slotID, ampL, ampR]);
        
        // FX Sends (post-fader) - 4 send buses
        Out.ar(fx1SendBus, sig * Lag.kr(fx1SendEff, 0.02));
        Out.ar(fx2SendBus, sig * Lag.kr(fx2SendEff, 0.02));
        Out.ar(fx3SendBus, sig * Lag.kr(fx3SendEff, 0.02));
        Out.ar(fx4SendBus, sig * Lag.kr(fx4SendEff, 0.02));
        
        // Main output
        Out.ar(outBus, sig);
    }).add;
    
    // === State Tracking Arrays ===
    // All state persists across generator changes / strip rebuilds
    ~stripVolState = Array.fill(8, { 0.8 });   // Volume (0-1)
    ~stripMuteState = Array.fill(8, { 0 });    // Mute (0/1)
    ~stripSoloState = ~stripSoloState ? Array.fill(8, { 0 });  // Solo (0/1) - keep if exists
    ~stripGainState = Array.fill(8, { 1.0 });  // Gain multiplier (1.0/2.0/4.0)
    ~stripPanState = Array.fill(8, { 0 });     // Pan (-1 to 1)
    ~stripTrimState = Array.fill(8, { 0.0 });  // Trim dB (from generator JSON)
    ~stripEqLoState = Array.fill(8, { 1.0 });  // EQ LO (0-2 linear)
    ~stripEqMidState = Array.fill(8, { 1.0 }); // EQ MID
    ~stripEqHiState = Array.fill(8, { 1.0 });  // EQ HI
    ~stripFx1SendState = Array.fill(8, { 0.0 }); // FX1 send (0-1) - was Echo
    ~stripFx2SendState = Array.fill(8, { 0.0 }); // FX2 send (0-1) - was Verb
    ~stripFx3SendState = Array.fill(8, { 0.0 }); // FX3 send (0-1)
    ~stripFx4SendState = Array.fill(8, { 0.0 }); // FX4 send (0-1)
    // Legacy aliases for backward compatibility
    ~stripEchoSendState = ~stripFx1SendState;
    ~stripVerbSendState = ~stripFx2SendState;
    
    "  [x] Channel strip SynthDef ready (EQ: %Hz / %Hz, smooth: %ms)".format(
        ~eqLoXover, ~eqHiXover, (~eqSmoothTime * 1000).asInteger
    ).postln;
};

// Start a channel strip for a slot (called when generator starts)
~startChannelStrip = { |slotID|
    var idx = slotID - 1;  // 0-indexed
    var currentVol, currentMute, currentSolo, currentGain, currentPan, currentTrim;
    var currentFx1Send, currentFx2Send, currentFx3Send, currentFx4Send;
    var currentEqLo, currentEqMid, currentEqHi;
    var fx1ModBusIdx, fx2ModBusIdx, fx3ModBusIdx, fx4ModBusIdx, panModBusIdx;

    // Bounds check
    if(idx < 0 || idx >= 8, {
        "ERROR: Invalid slot ID % for channel strip".format(slotID).postln;
    }, {
        // Get bus indices from bus unification (if available)
        fx1ModBusIdx = if(~getBusIndex.notNil, {
            ~getBusIndex.(("chan_%_fx1").format(slotID).asSymbol) ? -1
        }, { -1 });
        fx2ModBusIdx = if(~getBusIndex.notNil, {
            ~getBusIndex.(("chan_%_fx2").format(slotID).asSymbol) ? -1
        }, { -1 });
        fx3ModBusIdx = if(~getBusIndex.notNil, {
            ~getBusIndex.(("chan_%_fx3").format(slotID).asSymbol) ? -1
        }, { -1 });
        fx4ModBusIdx = if(~getBusIndex.notNil, {
            ~getBusIndex.(("chan_%_fx4").format(slotID).asSymbol) ? -1
        }, { -1 });
        panModBusIdx = if(~getBusIndex.notNil, {
            ~getBusIndex.(("chan_%_pan").format(slotID).asSymbol) ? -1
        }, { -1 });

        // Preserve ALL state before freeing
        currentVol = ~stripVolState[idx] ? 0.8;
        currentMute = ~stripMuteState[idx] ? 0;
        currentSolo = ~stripSoloState[idx] ? 0;
        currentGain = ~stripGainState[idx] ? 1.0;
        currentPan = ~stripPanState[idx] ? 0;
        currentTrim = ~stripTrimState[idx] ? 0.0;
        currentEqLo = ~stripEqLoState[idx] ? 1.0;
        currentEqMid = ~stripEqMidState[idx] ? 1.0;
        currentEqHi = ~stripEqHiState[idx] ? 1.0;
        currentFx1Send = ~stripFx1SendState[idx] ? 0.0;
        currentFx2Send = ~stripFx2SendState[idx] ? 0.0;
        currentFx3Send = ~stripFx3SendState[idx] ? 0.0;
        currentFx4Send = ~stripFx4SendState[idx] ? 0.0;

        // Free existing strip if any
        if(~channelStrips[idx].notNil, {
            ~channelStrips[idx].free;
            ~channelStrips[idx] = nil;
        });

        // Create new strip with ALL preserved state
        ~channelStrips[idx] = Synth(\channelStrip, [
            \inBus, ~genBus[idx],
            \outBus, ~drySumBus,
            \vol, currentVol,
            \mute, currentMute,
            \solo, currentSolo,
            \gain, currentGain,
            \pan, currentPan,
            \genTrim, currentTrim,
            \eqLo, currentEqLo,
            \eqMid, currentEqMid,
            \eqHi, currentEqHi,
            \soloActiveBus, ~soloActive.index,
            \slotID, slotID,
            \fx1Send, currentFx1Send,
            \fx2Send, currentFx2Send,
            \fx3Send, currentFx3Send,
            \fx4Send, currentFx4Send,
            \fx1SendBus, ~fx1SendBus,
            \fx2SendBus, ~fx2SendBus,
            \fx3SendBus, ~fx3SendBus,
            \fx4SendBus, ~fx4SendBus,
            \fx1SendModBus, fx1ModBusIdx,
            \fx2SendModBus, fx2ModBusIdx,
            \fx3SendModBus, fx3ModBusIdx,
            \fx4SendModBus, fx4ModBusIdx,
            \panModBus, panModBusIdx
        ], ~stripGroup, \addToTail);

        "  Started strip % (vol:%, eq:[%,%,%])".format(
            slotID, currentVol.round(0.01),
            currentEqLo.round(0.01), currentEqMid.round(0.01), currentEqHi.round(0.01)
        ).postln;
    });
};

// Stop a channel strip for a slot (called when generator stops)
~stopChannelStrip = { |slotID|
    var idx = slotID - 1;
    
    // Bounds check
    if(idx < 0 || idx >= 8, {
        "ERROR: Invalid slot ID % for channel strip stop".format(slotID).postln;
    }, {
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
    });
};

// Debug helper - call from SC to check all state
~debugStripState = {
    "=== Channel Strip State ===".postln;
    "EQ Crossovers: LO < %Hz < MID < %Hz < HI".format(~eqLoXover, ~eqHiXover).postln;
    ("soloCount: " ++ ~soloCount).postln;
    ("soloActive bus: " ++ ~soloActive.getSynchronous).postln;
    8.do { |i|
        var strip = ~channelStrips[i];
        if(strip.notNil, {
            "  Slot %: vol=%, mute=%, solo=%, gain=%, pan=%, eq=[%,%,%]".format(
                i+1,
                ~stripVolState[i].round(0.01),
                ~stripMuteState[i], 
                ~stripSoloState[i], 
                ~stripGainState[i].round(0.01),
                ~stripPanState[i].round(0.01),
                ~stripEqLoState[i].round(0.01),
                ~stripEqMidState[i].round(0.01),
                ~stripEqHiState[i].round(0.01)
            ).postln;
        });
    };
};

// Forward channel meter replies to Python (must be called after ~pythonAddr is set)
~setupChannelMeterForward = {
    OSCdef(\channelMeterForward, { |msg|
        // msg format: ['/noise/gen/levels', node_id, reply_id, slotID, ampL, ampR]
        if(~pythonAddr.notNil) { ~pythonAddr.sendMsg('/noise/gen/levels', msg[3].asInteger, msg[4], msg[5]); };
    }, '/noise/gen/levels');
    "  [x] Channel meter forwarding ready".postln;
};
