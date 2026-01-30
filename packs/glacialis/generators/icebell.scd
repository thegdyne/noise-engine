// glacialis/icebell — Lightweight end-stage generator
// ICEBELL - Crystalline struck ice
// Modal resonator with inharmonic ice ratios

SynthDef(\forge_glacialis_icebell, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var crystal, ring, strike, frost, size;
    var exciter, modes, ratios, decays, shimmer;

    crystal = p[0];  // Inharmonicity
    ring = p[1];  // Ring time
    strike = p[2];  // Strike brightness
    frost = p[3];  // High shimmer
    size = p[4];  // Modal spread

    freq = In.kr(freqBus);

    // Ice-like modal ratios (between harmonic and bar modes)
    ratios = [1, 2.32, 3.86, 5.17, 6.71, 8.23];
    ratios = ratios + (crystal * [0, 0.24, 0.41, 0.52, 0.38, 0.27]);
    ratios = ratios * (1 + (size * 0.3 * [0, 0.1, -0.05, 0.15, -0.1, 0.08]));

    // Per-mode decay times
    decays = ring.linexp(0, 1, 0.3, 4.0) * [1, 0.8, 0.6, 0.5, 0.4, 0.35];

    // Bright noise exciter
    exciter = WhiteNoise.ar(1) * Env.perc(0.001, 0.01 + (strike * 0.03)).ar(0);
    exciter = HPF.ar(exciter, strike.linexp(0, 1, 500, 3000));

    // Modal resonators
    modes = Mix.fill(6, { |i|
        Ringz.ar(exciter, (freq * ratios[i]).clip(20, 18000), decays[i]) * (i + 1).reciprocal
    });

    sig = modes * 0.15;

    // High frequency frost shimmer
    shimmer = Ringz.ar(exciter * frost,
        freq * [9.7, 12.3, 15.1],
        ring.linexp(0, 1, 0.1, 0.5) * 0.3
    ).sum * 0.1 * frost;

    sig = sig + shimmer;

    // Subtle stereo from size
    sig = [sig, DelayC.ar(sig, 0.01, size * 0.005)];

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_glacialis_icebell loaded".postln;
