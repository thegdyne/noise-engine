// bed_stuy/chain — Lightweight end-stage generator
// chain: Gold chain shimmer and clink
SynthDef(\forge_bed_stuy_chain, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var shine, weight, clink, swing, ice;

    shine = p[0].linlin(0, 1, 0.3, 0.9);  // P1: Shine brightness
    weight = p[1].linlin(0, 1, 0.2, 0.7);  // P2: Chain weight
    clink = p[2].linlin(0, 1, 5, 25);  // P3: Clink rate (boosted)
    swing = p[3].linlin(0, 1, 0.2, 0.6);  // P4: Swing modulation
    ice = p[4].linlin(0, 1, 0.1, 0.5);  // P5: Diamond sparkle

    freq = In.kr(freqBus);

    // DSP: Continuous metallic shimmer bed (always present)
    sig = BPF.ar(PinkNoise.ar(shine * 0.4), freq * 8, 0.15);

    // Metallic clinks - high harmonics (boosted)
    sig = sig + (Ringz.ar(Dust.ar(clink) * 0.25, freq * [6, 8, 10, 12], 0.1) * shine * 0.6);

    // Weight - lower body
    sig = sig + (Ringz.ar(Dust.ar(clink * 0.7) * 0.2, freq * [1.5, 2], 0.12) * weight);

    // Swing modulation on continuous bed
    sig = sig * (1 + (SinOsc.kr(swing * 3).range(0, 0.3)));

    // Ice sparkle - very high continuous shimmer
    sig = sig + (BPF.ar(WhiteNoise.ar(ice * 0.25), freq * 16, 0.1));

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_bed_stuy_chain loaded".postln;
