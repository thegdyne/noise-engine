SynthDef(\forge_kaiju_beats_cosmic, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var partials, drift, shimmer, depth, warp;
    var harmonics, driftMod;

    // Theme params
    partials = In.kr(customBus0);     // P1: Number of partials
    drift = In.kr(customBus1);        // P2: Frequency drift amount
    shimmer = In.kr(customBus2);      // P3: Amplitude shimmer
    depth = In.kr(customBus3);        // P4: Space depth - reverb-like
    warp = In.kr(customBus4);         // P5: Harmonic warp - inharmonicity

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
    ampVal = 0.2;

    // Drift modulation - slow random movement
    driftMod = LFNoise1.kr(0.1 + (drift * 0.5)) * drift * 0.02;

    // Additive synthesis - 12 partials
    harmonics = Mix.fill(12, { |i|
        var partialNum, partialFreq, partialAmp, driftAmt, shimmerAmt;
        partialNum = i + 1;
        // Warp creates inharmonicity (space weirdness)
        partialFreq = freq * (partialNum + (partialNum * partialNum * warp * 0.01));
        partialFreq = partialFreq * (1 + (LFNoise1.kr(0.2 + (i * 0.1)) * drift * 0.01));
        // Amplitude falloff based on partials param
        partialAmp = (1 / partialNum) * ((partials * 12) > i).asInteger;
        // Shimmer modulation
        shimmerAmt = LFNoise2.kr(1 + (i * 0.5)) * shimmer * 0.5 + (1 - (shimmer * 0.5));
        SinOsc.ar(partialFreq) * partialAmp * shimmerAmt * 0.15;
    });

    sig = harmonics;

    // Depth - comb-based pseudo-reverb
    sig = sig + (CombL.ar(sig, 0.2, 0.08 + (depth * 0.12), depth * 4) * depth * 0.4);
    sig = sig + (CombL.ar(sig, 0.2, 0.11 + (depth * 0.09), depth * 3) * depth * 0.3);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_kaiju_beats_cosmic loaded".postln;
