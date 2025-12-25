SynthDef(\forge_block_walk_snap_clap, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                         filterTypeBus, envEnabledBus, envSourceBus=0,
                                         clockRateBus, clockTrigBus,
                                         midiTrigBus=0, slotIndex=0,
                                         customBus0, customBus1, customBus2, customBus3, customBus4,
                                         portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var snap, clap, ring, crowd, room;
    var noise, snapEnv, clapEnv, clapDelay1, clapDelay2, clapDelay3;
    var toneBody, roomVerb, envTrig, crowdLayer;

    // Standard bus reads
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);

    // Theme params
    snap = In.kr(customBus0);       // Attack tightness
    clap = In.kr(customBus1);       // Hand spread
    ring = In.kr(customBus2);       // Tonal body
    crowd = In.kr(customBus3);      // Layering
    room = In.kr(customBus4);       // Space

    // Envelope trigger
    envTrig = Select.ar(envSource, [
        DC.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);

    // Snap envelope - very tight
    snapEnv = EnvGen.ar(Env.perc(0.001, snap.linexp(0, 1, 0.03, 0.01)), envTrig);

    // Clap envelope - slightly longer
    clapEnv = EnvGen.ar(Env.perc(0.005, 0.08), envTrig);

    // Noise source
    noise = WhiteNoise.ar;

    // Snap - tight bandpassed noise
    sig = BPF.ar(noise, 1800, 0.5) * snapEnv * snap.linlin(0, 1, 0.4, 0.8);

    // Clap - multiple taps with slight delays for hand texture
    clapDelay1 = DelayN.ar(noise * clapEnv, 0.02, clap.linlin(0, 1, 0.005, 0.015));
    clapDelay2 = DelayN.ar(noise * clapEnv, 0.03, clap.linlin(0, 1, 0.012, 0.025));
    clapDelay3 = DelayN.ar(noise * clapEnv, 0.04, clap.linlin(0, 1, 0.018, 0.035));

    sig = sig + BPF.ar(noise * clapEnv + clapDelay1 + clapDelay2 + clapDelay3, 1200, 0.6) * 0.5;

    // Crowd layer - additional offset hits
    crowdLayer = DelayN.ar(sig * 0.4, 0.1, TRand.ar(0.01, 0.05, envTrig));
    crowdLayer = crowdLayer + DelayN.ar(sig * 0.3, 0.1, TRand.ar(0.02, 0.06, envTrig));
    sig = sig + (crowdLayer * crowd.linlin(0, 1, 0, 0.6));

    // Tonal body via comb filter
    toneBody = CombL.ar(sig, 0.02, freq.reciprocal.clip(0.002, 0.02), ring.linlin(0, 1, 0.02, 0.12));
    sig = sig + (toneBody * ring.linlin(0, 1, 0, 0.5));

    // Room via allpass chain
    roomVerb = sig;
    roomVerb = AllpassN.ar(roomVerb, 0.05, 0.035, room.linlin(0, 1, 0.05, 0.25));
    roomVerb = AllpassN.ar(roomVerb, 0.05, 0.022, room.linlin(0, 1, 0.04, 0.2));
    roomVerb = AllpassN.ar(roomVerb, 0.05, 0.015, room.linlin(0, 1, 0.03, 0.15));
    sig = sig + (roomVerb * room.linlin(0, 1, 0.1, 0.5));

    sig = sig.tanh * 0.7;

    // Output chain
    sig = ~stereoSpread.(sig, 0.2, clap.linlin(0, 1, 0.2, 0.5));
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_block_walk_snap_clap loaded".postln;
