// Horizon Glow - Golden light catching the cliff edge
// Bright FM synthesis with warmth and breakthrough moments

SynthDef(\forge_drangarnir_horizon_glow, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                            portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var glow, warmth, edge, fade, breakthrough;
    var carrier, modulator, fmSig, shimmer, breakFlash;
    var modIndex, modRatio;

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
    glow = In.kr(customBus0);
    warmth = In.kr(customBus1);
    edge = In.kr(customBus2);
    fade = In.kr(customBus3);
    breakthrough = In.kr(customBus4);

    // FM parameters - warmth affects ratio and index
    modRatio = warmth.linlin(0, 1, 2, 1); // warmer = more fundamental
    modIndex = glow.linlin(0, 1, 1, 5) * (1 - (edge * 0.3));

    // FM synthesis - golden tone
    modulator = SinOsc.ar(freq * modRatio, 0, freq * modIndex);
    carrier = SinOsc.ar(freq + modulator, 0, glow * 0.5);

    // Add harmonics based on warmth
    fmSig = carrier;
    fmSig = fmSig + SinOsc.ar(freq * 2, 0, warmth * 0.2);
    fmSig = fmSig + SinOsc.ar(freq * 3, 0, warmth * 0.1 * (1 - edge));

    // Edge sharpness - affects harmonic content
    fmSig = fmSig + (SinOsc.ar(freq * 4 + (SinOsc.ar(freq * 2) * edge * freq)) * edge * 0.1);

    // High shimmer for light quality
    shimmer = Mix.fill(3, { |i|
        var shimFreq = freq * (5 + i) * LFNoise2.kr(1).range(0.99, 1.01);
        SinOsc.ar(shimFreq, 0, glow * 0.03 / (i + 1));
    });

    // Fade distance - affects sustain character
    fmSig = fmSig * LFNoise2.kr(fade.linexp(0, 1, 0.1, 1)).range(0.8, 1);

    // Breakthrough moments - sudden brightness
    breakFlash = SinOsc.ar(freq * 2, 0, 0.3) * 
        EnvGen.ar(
            Env.perc(0.01, 0.2),
            Dust.kr(breakthrough.linlin(0, 1, 0.2, 2))
        ) * breakthrough;

    // Combine
    sig = fmSig + shimmer + breakFlash;

    // Warm saturation
    sig = (sig * (1 + (warmth * 0.3))).tanh;

    // Stereo with subtle movement
    sig = ~stereoSpread.(sig, 0.2, 0.4);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_drangarnir_horizon_glow loaded".postln;
