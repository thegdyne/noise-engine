// scorn/mucus — Lightweight end-stage generator
// mucus: Wet surfaces - slime, drip
SynthDef(\forge_scorn_mucus, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var slime, drip, viscous, pool, stretch;

    slime = p[0].linlin(0, 1, 0.3, 0.9);  // P1: Slime amount
    drip = p[1].linlin(0, 1, 3, 20);  // P2: Drip rate
    viscous = p[2].linlin(0, 1, 100, 800);  // P3: Viscosity filter
    pool = p[3].linlin(0, 1, 0.1, 0.5);  // P4: Pool depth
    stretch = p[4].linlin(0, 1, 0.1, 0.6);  // P5: Stretch sounds

    freq = In.kr(freqBus);

    // DSP: Slime texture - thick filtered noise
    sig = LPF.ar(BrownNoise.ar(slime * 0.5), viscous);

    // Drip sounds
    sig = sig + (Ringz.ar(Dust.ar(drip) * 0.2, freq * [2, 3, 5], 0.1) * slime * 0.4);

    // Pool - low resonance
    sig = sig + (LPF.ar(PinkNoise.ar(pool * 0.3), 300));

    // Stretch sounds - slow modulated
    sig = sig + (BPF.ar(PinkNoise.ar(stretch * 0.3), freq * LFNoise1.kr(0.3).range(1, 3), 0.2) * stretch);

    // Continuous wet presence
    sig = sig + (SinOsc.ar(freq * [0.5, 1]) * pool * 0.2);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_scorn_mucus loaded".postln;
