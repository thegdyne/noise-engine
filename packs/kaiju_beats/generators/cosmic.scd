// kaiju_beats/cosmic — Lightweight end-stage generator
SynthDef(\forge_kaiju_beats_cosmic, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var partials, drift, shimmer, depth, warp;
    var harmonics, driftMod;

    partials = p[0];  // P1: Number of partials
    drift = p[1];  // P2: Frequency drift amount
    shimmer = p[2];  // P3: Amplitude shimmer
    depth = p[3];  // P4: Space depth - reverb-like
    warp = p[4];  // P5: Harmonic warp - inharmonicity

    freq = In.kr(freqBus);
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

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_kaiju_beats_cosmic loaded".postln;
