// wicker/hymn — Lightweight end-stage generator
SynthDef(\forge_wicker_hymn, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var chant, fervor, ancient, circle, rite;
    var chantMod, fervorMod, ancientMod, circleMod, riteMod;
    var voices, drone, breath, overtones;

    // Read custom params
    chant = p[0];  // P1: Chant intensity - scaled by ancient
    fervor = p[1];  // P2: Fervor passion - curve set by rite
    ancient = p[2];  // P3: Ancient depth - modulates chant AND circle
    circle = p[3];  // P4: Circle unity - feeds back to fervor
    rite = p[4];  // P5: Rite power - master transcendence axis

    // BUTTERFLY EFFECT: Cross-modulation network
    chantMod = chant * (0.3 + (ancient * 0.7));
    fervorMod = fervor.linexp(0, 1, 0.2, 5) * (1 + (circle * rite * 1.2));
    ancientMod = ancient * (1 + (rite.squared * 0.6));
    circleMod = circle * (0.4 + (chant * fervor * 0.6));
    riteMod = rite * (1 + (ancient * circle * 0.4));

    freq = In.kr(freqBus);

    // DSP: Harmonic series choir

    // Voices: fundamental with harmonic partials
    voices = Mix.fill(8, { |i|
        var partial, vibrato, gain;
        partial = i + 1;
        vibrato = SinOsc.kr(
            fervorMod * LFNoise1.kr(0.1).range(0.8, 1.2),
            i * 0.3
        ) * chantMod.linlin(0, 1, 0.001, 0.008);
        gain = (1 / (partial.sqrt)) * (1 - (ancientMod * i * 0.08));
        SinOsc.ar(freq * partial * (1 + vibrato), 0, gain.max(0))
    }) * 0.2;

    // Drone: low foundation
    drone = SinOsc.ar(freq * [0.5, 1], 0, 0.15).sum;
    drone = drone + (SinOsc.ar(freq * 0.25, 0, 0.08) * ancientMod);
    drone = drone * (1 + (LFNoise1.kr(circleMod * 0.5) * 0.1));

    // Breath: airy texture
    breath = PinkNoise.ar(0.05) * Resonz.ar(WhiteNoise.ar(0.3), freq * [2, 3, 4], 0.1).sum;
    breath = breath * fervorMod.linlin(0, 1, 0.1, 0.4);
    breath = breath * (1 + (SinOsc.kr(riteMod * 3) * 0.2));

    // Overtones: high ethereal shimmer
    overtones = Mix.fill(4, { |i|
        var oct, shimmer;
        oct = i + 3;
        shimmer = SinOsc.kr(riteMod * 0.3 * (i + 1), i).range(0.3, 1);
        SinOsc.ar(freq * (2 ** oct) * [1, 1.002], 0, 0.02 * shimmer / (oct + 1))
    }).sum;
    overtones = overtones * circleMod;

    // Mix based on rite (transcendence axis)
    sig = voices + drone + (breath * riteMod.linlin(0, 1, 0.5, 1.5)) + overtones;

    // Subtle chorus for circle unity
    sig = sig + (DelayC.ar(sig, 0.03, SinOsc.kr(circleMod * 0.2).range(0.01, 0.025)) * 0.2);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_wicker_hymn loaded".postln;
