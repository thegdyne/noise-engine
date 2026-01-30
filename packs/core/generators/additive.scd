// core/additive — Lightweight end-stage generator
/*
Additive Generator
Harmonic partial synthesis with spectral shaping

Signal flow: Partials -> Mix -> Filter -> ENV VCA -> Output

Custom params:
  - P1 partial_ratio: 0.5-4.0 (harmonic spacing multiplier)
  - P2 partial_curve: -2 to +2 (spectral shape/rolloff)
  - P3 num_partials: 2-16 discrete (number of harmonics)
  - P4 amp_env_depth: 0-1 (per-partial envelope modulation)
  - P5 spectral_tilt: -1 to +1 (dark <-> bright)
*/

SynthDef(\additive, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var partialRatio, partialCurve, numPartials, envDepth, tilt;

    freq = In.kr(freqBus);

    partialRatio = p[0];
    partialCurve = p[1];
    numPartials = p[2];
    envDepth = p[3];
    tilt = p[4];

    // === SOUND SOURCE ===
    sig = Mix.fill(16, { |i|
        var harmonic = i + 1;
        var partialFreq, partialAmp, partialPhase;

        partialFreq = (freq * harmonic * partialRatio.linlin(0.5, 4.0, 0.98, 1.02)).clip(20, 20000);
        partialAmp = 1 / (harmonic ** (1.5 + partialCurve));
        partialAmp = partialAmp * (1 + (tilt * (harmonic - 1) * 0.1));
        partialPhase = LFNoise1.kr(0.1 + (i * 0.02)).range(-0.003, 0.003);
        partialAmp = partialAmp * (1 - (envDepth * LFNoise1.kr(0.5 + (i * 0.1)).range(0, 0.3)));

        SinOsc.ar(partialFreq * (1 + partialPhase)) * partialAmp * (harmonic <= numPartials)
    });
    sig = sig / numPartials.sqrt * 0.5;

    sig = ~stereoSpread.(sig, 0.2, 0.3);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] additive loaded".postln;
