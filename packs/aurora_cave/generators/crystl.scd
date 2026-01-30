// aurora_cave/crystl — Lightweight end-stage generator
SynthDef(\forge_aurora_cave_crystl, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var clarity, ring, size, chime, ice;
    var exciter, modes, ratios, decays, amps;

    freq = In.kr(freqBus);

    clarity = p[0];
    ring = p[1];
    size = p[2];
    chime = p[3];
    ice = p[4];

    // Crystal exciter - sparse bright impulses
    exciter = Dust.ar(chime.linexp(0, 1, 1, 20)) * 0.8;
    exciter = exciter + (Impulse.ar(0) * 0.5); // Initial strike
    exciter = HPF.ar(exciter, 2000); // Bright excitation

    // Modal ratios - crystalline inharmonic series
    ratios = [1, 2.76, 5.41, 8.93, 13.34, 18.64] * size.linlin(0, 1, 0.7, 1.3);

    // Ring times based on modal frequency
    decays = ring.linlin(0, 1, 0.3, 3) * [1, 0.8, 0.6, 0.5, 0.4, 0.3];

    // Amplitude rolloff (higher modes quieter)
    amps = [1, 0.7, 0.5, 0.35, 0.25, 0.15] * clarity.linlin(0, 1, 0.5, 1);

    // Build modal resonator
    modes = Array.fill(6, { |i|
        Ringz.ar(exciter, freq * ratios[i], decays[i]) * amps[i]
    }).sum;

    // Add icy high shimmer
    modes = modes + (
        Ringz.ar(exciter * ice, freq * 21.7, 0.1) * ice * 0.1
    );
    modes = modes + (
        Ringz.ar(exciter * ice, freq * 34.2, 0.08) * ice * 0.05
    );

    sig = modes * 0.15;

    // Slight stereo decorrelation for space
    sig = [
        DelayC.ar(sig, 0.01, 0.002),
        DelayC.ar(sig, 0.01, 0.003)
    ];

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_aurora_cave_crystl loaded".postln;
