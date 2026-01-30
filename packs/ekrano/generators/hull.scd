// ekrano/hull — Lightweight end-stage generator
SynthDef(\forge_ekrano_hull, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var mass, strike, sizeParam, ring, damp;
    var exciter, modes, decayTime, trigRate;

    freq = In.kr(freqBus);

    mass = p[0].linexp(0, 1, 0.5, 4);
    strike = p[1].linlin(0, 1, 0.1, 0.6);
    sizeParam = p[2].linlin(0, 1, 0.5, 2);
    ring = p[3].linlin(0, 1, 0.3, 0.95);
    damp = p[4].linlin(0, 1, 0.1, 0.8);

    // Decay time based on mass
    decayTime = mass * (1 - (damp * 0.5));

    // Continuous excitation using Dust - avoids drone silence
    trigRate = strike.linexp(0.1, 0.6, 1, 8);
    exciter = Dust.ar(trigRate) * strike;
    exciter = exciter + (PinkNoise.ar(0.02) * (1 - damp));

    // Modal resonator - aluminum hull modes
    modes = DynKlank.ar(
        `[
            [1, 1.6, 2.3, 2.9, 4.1, 5.2, 6.8] * sizeParam,
            [1, 0.7, 0.5, 0.4, 0.25, 0.15, 0.1] * ring,
            [1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4] * decayTime
        ],
        exciter,
        freq,
        0,
        decayTime
    );

    sig = modes * 0.3;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ekrano_hull loaded".postln;
