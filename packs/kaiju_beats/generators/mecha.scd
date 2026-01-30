// kaiju_beats/mecha — Lightweight end-stage generator
SynthDef(\forge_kaiju_beats_mecha, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var mass, hydraulic, armor, groan, rust;
    var exciter, modes, metalBody, hydraulicHiss;

    mass = p[0];  // P1: Body mass - shifts modal frequencies
    hydraulic = p[1];  // P2: Hydraulic hiss amount
    armor = p[2];  // P3: Armor thickness - dampening
    groan = p[3];  // P4: Metal groan/stress
    rust = p[4];  // P5: Rust - adds noise/grit

    freq = In.kr(freqBus);
    ampVal = 0.2;

    // Exciter - metallic impulse with rust noise
    exciter = Dust.ar(1 + (groan * 3)) * 0.5;
    exciter = exciter + (PinkNoise.ar(0.02) * rust);

    // Modal resonator - giant robot body
    modes = DynKlank.ar(
        `[
            [1, 2.1, 3.5, 4.8, 6.2, 8.1] * (1 + (mass.neg * 0.3)),
            [1, 0.7, 0.5, 0.3, 0.2, 0.1],
            [2, 1.8, 1.5, 1.2, 1.0, 0.8] * (1 + (armor * 2))
        ],
        exciter,
        freq,
        0,
        (2 + (armor * 4)).reciprocal
    );

    // Metal stress/groan - slow LFO modulated resonance
    metalBody = SinOsc.ar(freq * 0.5 * (1 + (LFNoise1.kr(0.2) * groan * 0.1)));
    metalBody = metalBody * LFNoise2.kr(0.5 + (groan * 2)).range(0.3, 1) * groan * 0.3;

    // Hydraulic hiss
    hydraulicHiss = BPF.ar(WhiteNoise.ar(0.5), 3000 + (LFNoise1.kr(2) * 1000), 0.3);
    hydraulicHiss = hydraulicHiss * hydraulic * 0.2;

    // Mix
    sig = (modes * 0.6) + metalBody + hydraulicHiss;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_kaiju_beats_mecha loaded".postln;
