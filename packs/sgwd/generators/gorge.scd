// sgwd/gorge — Lightweight end-stage generator
// gorge: Hollow space behind waterfall
SynthDef(\forge_sgwd_gorge, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var depth, echo, dark, behind, ancient;

    depth = p[0].linlin(0, 1, 0.03, 0.1);  // P1: Gorge depth (comb)
    echo = p[1].linlin(0, 1, 1, 4);  // P2: Echo decay
    dark = p[2].linexp(0, 1, 400, 100);  // P3: Darkness (LPF)
    behind = p[3].linlin(0, 1, 0.2, 0.6);  // P4: Behind falls
    ancient = p[4].linlin(0, 1, 0.1, 0.4);  // P5: Ancient presence

    freq = In.kr(freqBus);

    // DSP: Cavernous gorge
    // Deep drone
    sig = SinOsc.ar(freq * [0.25, 0.5, 1] * LFNoise1.kr(0.03).range(0.98, 1.02)) * [0.4, 0.3, 0.2];
    sig = sig.sum;

    // Dark filtered noise
    sig = sig + (LPF.ar(BrownNoise.ar(0.4), dark) * behind);

    // Gorge resonance
    sig = CombL.ar(sig, 0.2, depth, echo);

    // Allpass diffusion
    sig = AllpassL.ar(sig, 0.1, 0.037, echo * 0.5);
    sig = AllpassL.ar(sig, 0.1, 0.059, echo * 0.4);

    // Ancient presence
    sig = sig + (SinOsc.ar(freq * 0.125) * ancient * 0.3);

    // Muffled waterfall sound from behind
    sig = sig + (LPF.ar(PinkNoise.ar(behind * 0.3), 300));

    sig = sig * 0.35;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_sgwd_gorge loaded".postln;
