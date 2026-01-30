// oldwinch/ritual — Lightweight end-stage generator
SynthDef(\forge_oldwinch_ritual, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var sacred, chant, gather, season, power;
    var harmonics, seasonMod, gatherSpread, baseAmp;

    sacred = p[0];
    chant = p[1];
    gather = p[2];
    season = p[3];
    power = p[4];

    freq = In.kr(freqBus);

    // Seasonal modulation - very slow
    seasonMod = SinOsc.kr(season.linexp(0, 1, 0.03, 0.15)).range(0.9, 1.0);

    // Gathering chorus spread
    gatherSpread = gather * 0.008;

    // Base amplitude
    baseAmp = 0.18;

    // Core harmonic series - sacred chant
    harmonics = SinOsc.ar(freq, 0, baseAmp * (1 + (power * 0.5)));
    harmonics = harmonics + SinOsc.ar(freq * (1 + gatherSpread), 0.3, baseAmp * 0.4 * gather);
    harmonics = harmonics + SinOsc.ar(freq * (1 - gatherSpread), 0.6, baseAmp * 0.4 * gather);

    // Sub harmonics (earth power)
    harmonics = harmonics + SinOsc.ar(freq * 0.5, 0, baseAmp * 0.6 * power);
    harmonics = harmonics + SinOsc.ar(freq * 0.25, 0, baseAmp * 0.4 * power);

    // Upper harmonics (chant brightness)
    harmonics = harmonics + SinOsc.ar(freq * 2, 0, baseAmp * 0.5 * (0.3 + (chant * 0.7)));
    harmonics = harmonics + SinOsc.ar(freq * 3, 0, baseAmp * 0.35 * (0.2 + (chant * 0.8)));
    harmonics = harmonics + SinOsc.ar(freq * 4, 0, baseAmp * 0.25 * chant * sacred);
    harmonics = harmonics + SinOsc.ar(freq * 5, 0, baseAmp * 0.18 * chant * sacred);
    harmonics = harmonics + SinOsc.ar(freq * 6, 0, baseAmp * 0.12 * chant * sacred);

    // Sacred shimmer
    harmonics = harmonics + SinOsc.ar(freq * 7, 0, baseAmp * 0.08 * sacred);
    harmonics = harmonics + SinOsc.ar(freq * 8, 0, baseAmp * 0.06 * sacred);

    // Apply seasonal modulation
    sig = harmonics * seasonMod;

    // Breath texture
    sig = sig + (HPF.ar(PinkNoise.ar(0.03), 2000) * sacred * LFNoise2.kr(2).range(0, 1));

    // Continuous bed
    sig = sig + PinkNoise.ar(0.04);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_oldwinch_ritual loaded".postln;
