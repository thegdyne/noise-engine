// hoar_frost/willow_drip — Lightweight end-stage generator
// willow_drip: Ice drops from willow branches - delicate FM bells
SynthDef(\forge_hoar_frost_willow_drip, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var ratio, modDepth, brightness, inharmonic, decay2;

    ratio = p[0].linlin(0, 1, 1.5, 5);  // P1: FM ratio
    modDepth = p[1].linlin(0, 1, 0.5, 4);  // P2: FM depth
    brightness = p[2].linlin(0, 1, 1, 8);  // P3: Harmonic brightness
    inharmonic = p[3].linlin(0, 1, 0, 0.05);  // P4: Inharmonicity
    decay2 = p[4].linlin(0, 1, 0.3, 2);  // P5: Bell decay

    freq = In.kr(freqBus);

    // DSP: FM bell with inharmonic partials
    sig = PMOsc.ar(
        freq * (1 + (inharmonic * LFNoise0.kr(0.5))),
        freq * ratio,
        modDepth * Line.kr(1, 0.1, decay2),
        0
    );

    // Add shimmer partial
    sig = sig + (SinOsc.ar(freq * brightness * (1 + (inharmonic * 2))) * 0.1 * Line.kr(1, 0, decay2 * 0.5));

    sig = sig * 0.3;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_hoar_frost_willow_drip loaded".postln;
