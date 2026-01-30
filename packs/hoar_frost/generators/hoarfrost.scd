// hoar_frost/hoarfrost — Lightweight end-stage generator
// hoarfrost: Frost crackling - granular texture
SynthDef(\forge_hoar_frost_hoarfrost, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var grainRate, grainSize, scatter, tonal, texture;

    grainRate = p[0].linexp(0, 1, 5, 80);  // P1: Grain rate
    grainSize = p[1].linlin(0, 1, 0.005, 0.05);  // P2: Grain size
    scatter = p[2].linlin(0, 1, 0, 1);  // P3: Pitch scatter
    tonal = p[3].linlin(0, 1, 0, 1);  // P4: Tonal vs noise
    texture = p[4].linlin(0, 1, 0.1, 0.9);  // P5: Texture density

    freq = In.kr(freqBus);

    // DSP: Granular with tonal/noise blend
    sig = GrainSin.ar(
        2,
        Dust.ar(grainRate * texture),
        grainSize,
        freq * (1 + (TRand.ar(scatter.neg, scatter, Dust.ar(grainRate)))),
        0,
        -1
    ) * tonal;

    // Add noise grains
    sig = sig + (GrainBuf.ar(
        2,
        Dust.ar(grainRate * texture * 0.5),
        grainSize * 2,
        LocalBuf(512).set(Array.fill(512, { |i| (i / 512 * 2 - 1).rand })),
        1,
        TRand.ar(0, 1, Dust.ar(grainRate)),
        2
    ) * (1 - tonal) * 0.3);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_hoar_frost_hoarfrost loaded".postln;
