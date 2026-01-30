// pripyat/ferris — Lightweight end-stage generator
SynthDef(\forge_pripyat_ferris, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var rust, spin, mass, groan, sway;
    var exciter, modes, groanSig, creakRate, swayMod;

    freq = In.kr(freqBus);

    rust = p[0];
    spin = p[1];
    mass = p[2];
    groan = p[3];
    sway = p[4];

    // Rotation-based creak rate
    creakRate = spin.linexp(0, 1, 0.1, 2);
    swayMod = LFNoise2.kr(0.2) * sway * 0.1;

    // Modal exciter - continuous dust triggers for creaks
    exciter = Dust.ar(creakRate * 3) * 0.3;
    exciter = exciter + (LFNoise2.ar(creakRate) * 0.02); // Continuous friction

    // Modal resonances - rusted metal frequencies
    modes = DynKlank.ar(
        `[
            [1, 2.3, 4.5, 6.7, 8.2, 11.3] * (1 + (rust * 0.15)),  // Rust detunes
            [1, 0.6, 0.3, 0.2, 0.15, 0.1] * (1 - (rust * 0.3)),   // Rust dampens
            [1.2, 0.9, 0.7, 0.5, 0.4, 0.3] * mass.linlin(0, 1, 0.5, 2)  // Mass affects decay
        ],
        exciter,
        freq * (1 + swayMod),
        0,
        mass.linexp(0, 1, 0.5, 3)
    );

    // Low groan - structural stress
    groanSig = SinOsc.ar(freq * 0.25 * (1 + (LFNoise2.kr(0.3) * 0.05)));
    groanSig = groanSig * LFNoise2.kr(spin.linlin(0, 1, 0.05, 0.3)).range(0, 1);
    groanSig = groanSig * groan * 0.3;

    // Mix
    sig = modes + groanSig;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_pripyat_ferris loaded".postln;
