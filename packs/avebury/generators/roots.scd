SynthDef(\forge_avebury_roots, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                   filterTypeBus, envEnabledBus, envSourceBus=0,
                                   clockRateBus, clockTrigBus,
                                   midiTrigBus=0, slotIndex=0,
                                   customBus0, customBus1, customBus2, customBus3, customBus4,
                                   portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var spread, depth, earth, pulse, tangle;
    var exciter, comb1, comb2, comb3, comb4, delayTime, feedback, pulseMod;

    // Theme params
    spread = In.kr(customBus0);
    depth = In.kr(customBus1);
    earth = In.kr(customBus2);
    pulse = In.kr(customBus3);
    tangle = In.kr(customBus4);

    // Standard reads
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

    // Slow organic pulse modulation
    pulseMod = LFTri.kr(pulse.linexp(0, 1, 0.05, 0.5)).range(0.7, 1.0);

    // Exciter - earth rumble + organic texture
    exciter = BrownNoise.ar(0.3) + LPF.ar(PinkNoise.ar(0.2), 400);
    exciter = exciter * pulseMod;

    // Base delay time from frequency
    delayTime = freq.reciprocal;
    feedback = earth.linlin(0, 1, 0.7, 0.4);

    // Root network - multiple comb delays with tangle detuning
    comb1 = CombL.ar(exciter, 0.2, delayTime.clip(0.002, 0.2), 0.8 + (spread * 1.5), 0.4);
    comb2 = CombL.ar(exciter, 0.2, (delayTime * (1 + (tangle * 0.05))).clip(0.002, 0.2), 0.6 + spread, 0.3);
    comb3 = CombL.ar(exciter, 0.2, (delayTime * 2 * (1 - (tangle * 0.03))).clip(0.002, 0.2), 0.5 + (spread * 0.5), 0.25);
    comb4 = CombL.ar(exciter, 0.2, (delayTime * 0.5).clip(0.002, 0.2), 0.7 + spread, 0.35 * depth);

    sig = (comb1 + comb2 + comb3 + comb4) * 0.35;

    // Depth emphasis - sub layer
    sig = sig + (SinOsc.ar(freq * 0.5, 0, 0.2 * depth) * pulseMod);
    sig = sig + LPF.ar(BrownNoise.ar(0.15 * depth), 150);

    // Earth filtering - low pass for underground feel
    sig = LPF.ar(sig, depth.linexp(0, 1, 2000, 600));

    // Add allpass for spread
    sig = AllpassC.ar(sig, 0.3, spread.linlin(0, 1, 0.05, 0.2), spread * 2);

    // Continuous bed
    sig = sig + LPF.ar(BrownNoise.ar(0.08), 200);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_avebury_roots loaded".postln;
