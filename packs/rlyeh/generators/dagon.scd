// rlyeh/dagon — Lightweight end-stage generator
// dagon: Father of the deep ones - aquatic horror
SynthDef(\forge_rlyeh_dagon, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var bubble, depth, scale, call, ancient;

    bubble = p[0].linlin(0, 1, 2, 25);  // P1: Bubble rate
    depth = p[1].linlin(0, 1, 0.3, 1);  // P2: Ocean depth filter
    scale = p[2].linlin(0, 1, 0, 0.5);  // P3: Fish scale shimmer
    call = p[3].linlin(0, 1, 0, 0.7);  // P4: Deep one call
    ancient = p[4].linlin(0, 1, 0.3, 1);  // P5: Ancient presence

    freq = In.kr(freqBus);

    // DSP: Ancient presence - deep drone
    sig = SinOsc.ar(freq * [0.5, 1, 1.01]) * ancient;
    sig = Splay.ar(sig, 0.5);

    // Bubble texture - stereo array, no .sum needed
    sig = sig + Ringz.ar(Dust.ar(bubble) * 0.2, freq * LFNoise0.kr(bubble).range(2, 5) * [1, 1.03], 0.08);

    // Depth filtering
    sig = LPF.ar(sig, freq * depth * 8);

    // Scale shimmer
    sig = sig + (Blip.ar(freq * 2, LFNoise1.kr(0.5).range(3, 8)) * scale * 0.2);

    // Deep one call - eerie formant
    sig = sig + (Formant.ar(
        freq * 0.5 * LFNoise1.kr(0.3).range(0.95, 1.05),
        freq * 1.5,
        freq * 3
    ) * call * 0.3);

    sig = sig * 0.3;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_rlyeh_dagon loaded".postln;
