// tricorn/tower — Lightweight end-stage generator
SynthDef(\forge_tricorn_tower, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var height, steps, angular, wind, shadow;
    var harmonics, windMod, baseAmp;

    height = p[0];
    steps = p[1];
    angular = p[2];
    wind = p[3];
    shadow = p[4];

    freq = In.kr(freqBus);

    // Wind modulation
    windMod = LFNoise2.kr(0.5 + (wind * 2)).range(0.7, 1.0);

    // Base amplitude scaling - boosted for presence
    baseAmp = 0.25;

    // Build harmonic series - 12 harmonics with height-based rolloff
    // Core harmonics always present, height adds upper extension
    harmonics = SinOsc.ar(freq * 1, 0, baseAmp * (1 + shadow));
    harmonics = harmonics + SinOsc.ar(freq * 2, 0, baseAmp * 0.7 * (1 - (angular * 0.3)));
    harmonics = harmonics + SinOsc.ar(freq * 3, 0, baseAmp * 0.6 * (1 + (angular * 0.5)));
    harmonics = harmonics + SinOsc.ar(freq * 4, 0, baseAmp * 0.4 * (0.3 + (height * 0.7)));
    harmonics = harmonics + SinOsc.ar(freq * 5, 0, baseAmp * 0.35 * (1 + (angular * 0.6)) * (0.3 + (height * 0.7)));
    harmonics = harmonics + SinOsc.ar(freq * 6, 0, baseAmp * 0.25 * (0.2 + (height * 0.8)));
    harmonics = harmonics + SinOsc.ar(freq * 7, 0, baseAmp * 0.22 * (1 + (angular * 0.7)) * (0.2 + (height * 0.8)));
    harmonics = harmonics + SinOsc.ar(freq * 8, 0, baseAmp * 0.15 * (0.1 + (height * 0.9)));
    harmonics = harmonics + SinOsc.ar(freq * 9, 0, baseAmp * 0.12 * (1 + (angular * 0.4)) * (0.1 + (height * 0.9)));
    harmonics = harmonics + SinOsc.ar(freq * 10, 0, baseAmp * 0.1 * height);
    harmonics = harmonics + SinOsc.ar(freq * 11, 0, baseAmp * 0.08 * (1 + angular) * height);
    harmonics = harmonics + SinOsc.ar(freq * 12, 0, baseAmp * 0.06 * height);

    // Steps: add slight inharmonicity
    harmonics = harmonics + SinOsc.ar(freq * (1 + (steps * 0.02)), 0, baseAmp * 0.2 * (0.3 + (steps * 0.7)));
    harmonics = harmonics + SinOsc.ar(freq * (3 + (steps * 0.05)), 0, baseAmp * 0.15 * (0.3 + (steps * 0.7)));

    sig = harmonics * windMod;

    // Continuous noise bed for air - always present
    sig = sig + PinkNoise.ar(0.05);
    sig = sig + (PinkNoise.ar(0.03) * wind);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_tricorn_tower loaded".postln;
