// duga/array — Lightweight end-stage generator
SynthDef(\forge_duga_array, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var size, rust, tens, wind, reso;
    var exciter, modes, windNoise, tensionMod;

    freq = In.kr(freqBus);

    size = p[0];
    rust = p[1];
    tens = p[2];
    wind = p[3];
    reso = p[4];

    // Wind noise excitation - continuous for drone mode
    windNoise = PinkNoise.ar(0.05) * LFNoise2.kr(wind.linexp(0, 1, 0.1, 2)).range(0.5, 1);
    windNoise = windNoise + (Dust.ar(wind.linexp(0, 1, 1, 10)) * 0.2);

    // Tension modulation affects pitch slightly
    tensionMod = LFNoise2.kr(0.1).range(1 - (tens * 0.02), 1 + (tens * 0.02));

    // Exciter combines wind and sparse impacts
    exciter = windNoise;

    // Modal resonances of massive steel structure
    modes = DynKlank.ar(
        `[
            [1, 1.5, 2.2, 3.1, 4.7, 6.3] * size.linlin(0, 1, 1.5, 0.5),
            [1, 0.7, 0.5, 0.3, 0.2, 0.15] * (1 - (rust * 0.4)),
            [2, 1.8, 1.5, 1.2, 1, 0.8] * reso.linlin(0, 1, 0.5, 2)
        ],
        exciter,
        freq * tensionMod,
        0,
        size.linexp(0, 1, 1, 4)
    );

    sig = modes * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_duga_array loaded".postln;
