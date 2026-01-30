// aurora_cave/aurora — Lightweight end-stage generator
SynthDef(\forge_aurora_cave_aurora, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var shimmer, bands, drift, glow, spread;
    var harmonics, driftMod;

    freq = In.kr(freqBus);

    shimmer = p[0];
    bands = p[1];
    drift = p[2];
    glow = p[3];
    spread = p[4];

    driftMod = LFNoise2.kr(drift.linexp(0, 1, 0.05, 0.5));

    // Fixed 8 harmonics, bands controls amplitude rolloff
    harmonics = SinOsc.ar(freq * (1 + (driftMod * 0.02))) * 1.0 *
        SinOsc.kr(shimmer.linexp(0, 1, 0.1, 3), 0).range(0.3, 1);
    harmonics = harmonics + (SinOsc.ar(freq * 2 * (1 + (driftMod * 0.04))) * (0.7 * bands.linlin(0, 1, 0.3, 1)) *
        SinOsc.kr(shimmer.linexp(0, 1, 0.1, 3) * 1.1, 0.5).range(0.3, 1));
    harmonics = harmonics + (SinOsc.ar(freq * 3 * (1 + (driftMod * 0.06))) * (0.55 * bands.linlin(0, 1, 0.2, 1)) *
        SinOsc.kr(shimmer.linexp(0, 1, 0.1, 3) * 1.2, 1.0).range(0.3, 1));
    harmonics = harmonics + (SinOsc.ar(freq * 4 * (1 + (driftMod * 0.08))) * (0.45 * bands.linlin(0, 1, 0.1, 1)) *
        SinOsc.kr(shimmer.linexp(0, 1, 0.1, 3) * 1.3, 1.5).range(0.3, 1));
    harmonics = harmonics + (SinOsc.ar(freq * 5 * (1 + (driftMod * 0.1))) * (0.35 * bands) *
        SinOsc.kr(shimmer.linexp(0, 1, 0.1, 3) * 1.4, 2.0).range(0.3, 1));
    harmonics = harmonics + (SinOsc.ar(freq * 6 * (1 + (driftMod * 0.12))) * (0.25 * bands) *
        SinOsc.kr(shimmer.linexp(0, 1, 0.1, 3) * 1.5, 2.5).range(0.3, 1));
    harmonics = harmonics + (SinOsc.ar(freq * 7 * (1 + (driftMod * 0.14))) * (0.18 * bands) *
        LFNoise2.kr(shimmer.linexp(0, 1, 0.2, 2)).range(0, 0.15));
    harmonics = harmonics + (SinOsc.ar(freq * 8 * (1 + (driftMod * 0.16))) * (0.12 * bands) *
        LFNoise2.kr(shimmer.linexp(0, 1, 0.15, 1.5)).range(0, 0.1));

    sig = harmonics * 0.2;
    sig = (sig * (1 + (glow * 2))).tanh * (1 - (glow * 0.3));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_aurora_cave_aurora loaded".postln;
