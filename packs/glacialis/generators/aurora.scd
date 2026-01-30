// glacialis/aurora — Lightweight end-stage generator
// AURORA - Spectral aurora shimmer
// Additive synthesis with drifting phase interference

SynthDef(\forge_glacialis_aurora, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var bands, drift, glow, shift, veil;
    var partials, driftLFOs, shiftMod;

    bands = p[0];  // Band density
    drift = p[1];  // Phase drift rate
    glow = p[2];  // Brightness
    shift = p[3];  // Spectral shift
    veil = p[4];  // Diffusion

    freq = In.kr(freqBus);

    // Spectral shift modulation
    shiftMod = SinOsc.kr(drift.linexp(0, 1, 0.02, 0.15)).range(1, 1 + (shift * 0.1));

    // Additive partials with phase drift - 8 fixed partials with crossfade
    partials = Mix.fill(8, { |i|
        var ratio, ampScale, driftRate, phase;
        ratio = (i + 1) * shiftMod;
        ampScale = (bands * 8 - i).clip(0, 1) * ((i + 1).reciprocal ** (1 - glow));
        driftRate = drift.linexp(0, 1, 0.01, 0.1) * (i + 1).sqrt * 0.3;
        phase = SinOsc.kr(driftRate, i * 0.7).range(0, 2pi);
        SinOsc.ar(freq * ratio, phase) * ampScale
    });

    sig = partials * 0.3;

    // Veil/diffusion via chorus
    sig = sig + (DelayC.ar(sig, 0.05,
        SinOsc.kr(veil.linexp(0, 1, 0.1, 2), 0).range(0.005, 0.02)
    ) * veil * 0.5);

    // Stereo shimmer
    sig = [
        sig + (DelayC.ar(sig, 0.03, SinOsc.kr(0.13).range(0.003, 0.015)) * 0.3),
        sig + (DelayC.ar(sig, 0.03, SinOsc.kr(0.17).range(0.004, 0.018)) * 0.3)
    ];

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_glacialis_aurora loaded".postln;
