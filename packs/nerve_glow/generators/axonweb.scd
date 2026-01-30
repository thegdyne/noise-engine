// nerve_glow/axonweb — Lightweight end-stage generator
// AXONWEB -- Axon network granular
// Diffuse cloud of nerve fibers -- cyan shimmer spreading

SynthDef(\forge_nerve_glow_axonweb, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var network, spread, pulse, branch, shimmer;
    var grainDens, grainDur, grains, pitchVar, shimmerSig;

    // Standard bus reads
    freq = In.kr(freqBus);

    network = p[0].linexp(0, 1, 5, 80);  // Grain density
    spread = p[1].linlin(0, 1, 0.0, 1.0);  // Stereo width
    pulse = p[2].linlin(0, 1, 0.0, 0.8);  // Amplitude mod
    branch = p[3].linlin(0, 1, 0.0, 0.5);  // Pitch scatter
    shimmer = p[4].linlin(0, 1, 0.0, 0.6);  // High freq content

    // Grain parameters
    grainDens = network;
    grainDur = network.reciprocal.linlin(5, 80, 0.1, 0.02);

    // Pitch variation for branching
    pitchVar = LFNoise1.kr(branch * 10).range(1 - (branch * 0.5), 1 + (branch * 0.5));

    // Granular synthesis - using GrainSin for clean sine grains
    grains = GrainSin.ar(
        numChannels: 2,
        trigger: Dust.ar(grainDens),
        dur: grainDur,
        freq: freq * pitchVar,
        pan: WhiteNoise.kr(spread),
        mul: 0.3
    );

    // Add layers at different octaves for network complexity
    grains = grains + GrainSin.ar(
        numChannels: 2,
        trigger: Dust.ar(grainDens * 0.5),
        dur: grainDur * 2,
        freq: freq * 2 * LFNoise1.kr(2).range(0.98, 1.02),
        pan: WhiteNoise.kr(spread),
        mul: 0.15
    );

    // Shimmer - high frequency grains
    shimmerSig = GrainSin.ar(
        numChannels: 2,
        trigger: Dust.ar(grainDens * 2),
        dur: grainDur * 0.5,
        freq: freq * 4 * LFNoise1.kr(5).range(0.9, 1.1),
        pan: WhiteNoise.kr(1),
        mul: shimmer * 0.1
    );

    sig = grains + shimmerSig;

    // Amplitude pulse (neural firing rhythm)
    sig = sig * (1 - (pulse * SinOsc.kr(LFNoise1.kr(0.2).range(0.5, 3)).range(0, 0.5)));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_nerve_glow_axonweb loaded".postln;
