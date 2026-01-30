// overgrown/spore_drift — Lightweight end-stage generator
SynthDef(\forge_overgrown_spore_drift, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var density, scatter, glow, drift, grainSize;
    var grains, shimmer, dust1, dust2, mod1, mod2;

    density = p[0];
    scatter = p[1];
    glow = p[2];
    drift = p[3];
    grainSize = p[4];

    freq = In.kr(freqBus);

    // Slow drift modulation
    mod1 = SinOsc.kr(drift.linexp(0, 1, 0.02, 0.5)).range(0.98, 1.02);
    mod2 = SinOsc.kr(drift.linexp(0, 1, 0.03, 0.7), pi/2).range(0.97, 1.03);

    // Grain triggers - continuous dust for drone mode
    dust1 = Dust.ar(density.linexp(0, 1, 2, 40));
    dust2 = Dust.ar(density.linexp(0, 1, 3, 50));

    // Granular sine particles
    grains = SinOsc.ar(freq * mod1 * [1, 1.002]) * Decay2.ar(dust1, 0.001, grainSize.linexp(0, 1, 0.02, 0.3));
    grains = grains + (SinOsc.ar(freq * 2 * mod2 * [1.001, 1]) * Decay2.ar(dust2, 0.001, grainSize.linexp(0, 1, 0.015, 0.2)) * 0.5);
    grains = grains + (SinOsc.ar(freq * 3 * mod1 * [1, 1.003]) * Decay2.ar(Dust.ar(density.linexp(0, 1, 1, 20)), 0.001, grainSize.linexp(0, 1, 0.01, 0.15)) * 0.25);

    // Harmonic shimmer layer
    shimmer = SinOsc.ar(freq * [4.01, 3.99]) * LFNoise1.kr(0.5).range(0, 1) * glow * 0.15;
    shimmer = shimmer + (SinOsc.ar(freq * [5.02, 4.98]) * LFNoise1.kr(0.7).range(0, 1) * glow * 0.08);

    // Soft noise bed for continuous drone
    sig = grains + shimmer + (PinkNoise.ar(0.02 * density) * [1, 1]);

    // Scatter - stereo width
    sig = Balance2.ar(sig[0], sig[1], LFNoise1.kr(scatter.linexp(0, 1, 0.1, 2)).range(scatter.neg, scatter));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_overgrown_spore_drift loaded".postln;
