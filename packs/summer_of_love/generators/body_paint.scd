// summer_of_love/body_paint — Lightweight end-stage generator
SynthDef(\forge_summer_of_love_body_paint, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var blue, orange, vivid, morph, shine;
    var blueTone, orangeTone, morphLfo, index, shineOsc;

    freq = In.kr(freqBus);

    blue = p[0];  // Cool FM ratio (higher, metallic)
    orange = p[1];  // Warm FM ratio (lower, woody)
    vivid = p[2];  // Modulation intensity
    morph = p[3];  // Morphing speed
    shine = p[4];  // High harmonic shimmer

    // FM modulation index based on vivid
    index = vivid.linexp(0, 1, 0.5, 8);

    // Blue tone - cool, metallic (ratio ~3.5:1)
    blueTone = SinOsc.ar(
        freq,
        SinOsc.ar(freq * 3.51) * index * blue * 2pi
    );

    // Orange tone - warm, woody (ratio ~1.5:1 with sub-harmonics)
    orangeTone = SinOsc.ar(
        freq,
        SinOsc.ar(freq * 1.498) * index * orange * 2pi
    ) + (SinOsc.ar(freq * 0.5) * orange * 0.3);

    // Morph LFO - crossfade between blue and orange
    morphLfo = SinOsc.kr(morph.linexp(0, 1, 0.05, 2)).range(0, 1);
    sig = XFade2.ar(orangeTone, blueTone, morphLfo.linlin(0, 1, -1, 1));

    // Shine - add high harmonic content
    shineOsc = SinOsc.ar(freq * 5) * SinOsc.ar(freq * 7) * shine * 0.15;
    sig = sig + shineOsc;

    // Gentle stereo spread
    sig = ~stereoSpread.(sig, 0.2, 0.4);

    // Apply standard processing chain

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_summer_of_love_body_paint loaded".postln;
