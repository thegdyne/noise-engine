// hoar_frost/rime_veil — Lightweight end-stage generator
// rime_veil: Crystalline frost forming - shimmering high harmonics
SynthDef(\forge_hoar_frost_rime_veil, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var shimmer, density, brightness, spread, drift;

    shimmer = p[0].linlin(0, 1, 0.1, 4);  // P1: Shimmer rate
    density = p[1].linlin(0, 1, 0.3, 1);  // P2: Harmonic density (amplitude rolloff)
    brightness = p[2].linlin(0, 1, 0.3, 1);  // P3: High partial level
    spread = p[3].linlin(0, 1, 0, 0.02);  // P4: Stereo spread
    drift = p[4].linlin(0, 1, 0, 0.01);  // P5: Pitch drift

    freq = In.kr(freqBus);

    // DSP: Additive harmonics with shimmer (fixed 12 partials, density controls rolloff)
    sig = Mix.fill(12, { |i|
        var partial = i + 1;
        var partialFreq = freq * partial * (1 + (LFNoise1.kr(drift * partial) * drift));
        var partialAmp = (1 / partial.sqrt) * (density ** (i / 6)) * (brightness ** (i / 12));
        var shimmerMod = SinOsc.kr(shimmer * (1 + (i * 0.1)), Rand(0, 2pi)).range(0.5, 1);
        SinOsc.ar(partialFreq, 0, partialAmp * shimmerMod * 0.1)
    });

    // Stereo spread
    sig = Splay.ar(sig.dup(2), spread);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_hoar_frost_rime_veil loaded".postln;
