// scorn/rib — Lightweight end-stage generator
// rib: Bone architecture - ribbed resonant structures
SynthDef(\forge_scorn_rib, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var bone, hollow, crack, tension, marrow;

    bone = p[0].linlin(0, 1, 0.3, 1);  // P1: Bone resonance
    hollow = p[1].linlin(0, 1, 0.01, 0.05);  // P2: Hollow spacing
    crack = p[2].linlin(0, 1, 1, 8);  // P3: Crack/stress rate
    tension = p[3].linlin(0, 1, 0.2, 0.7);  // P4: Structural tension
    marrow = p[4].linlin(0, 1, 0.1, 0.5);  // P5: Inner marrow

    freq = In.kr(freqBus);

    // DSP: Bone resonance - hollow comb
    sig = CombL.ar(PinkNoise.ar(bone * 0.3), 0.1, hollow, tension * 2);

    // Continuous bone tone
    sig = sig + (BPF.ar(Saw.ar(freq * [0.5, 1]), freq * 2, 0.3) * bone * 0.25);

    // Crack sounds - stress on structure
    sig = sig + (Ringz.ar(Dust.ar(crack) * 0.2, freq * [3, 5, 7], 0.05) * tension);

    // Marrow - deep inner warmth
    sig = sig + (LPF.ar(BrownNoise.ar(marrow * 0.3), 300));

    // Structural hum
    sig = sig + (SinOsc.ar(freq * [0.5, 1]) * tension * 0.2);

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_scorn_rib loaded".postln;
