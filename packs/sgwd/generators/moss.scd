// sgwd/moss — Lightweight end-stage generator
// moss: Green mossy rock surfaces
SynthDef(\forge_sgwd_moss, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var lush, damp, soft, green, ancient;

    lush = p[0].linlin(0, 1, 0.3, 0.8);  // P1: Density
    damp = p[1].linexp(0, 1, 800, 300);  // P2: Dampness (LPF)
    soft = p[2].linlin(0, 1, 0.2, 0.6);  // P3: Soft texture
    green = p[3].linlin(0, 1, 300, 600);  // P4: Green tone (BPF)
    ancient = p[4].linlin(0, 1, 0.1, 0.4);  // P5: Ancient drone

    freq = In.kr(freqBus);

    // DSP: Soft moss texture
    // Lush filtered base
    sig = LPF.ar(PinkNoise.ar(lush), damp);
    sig = sig * LFNoise1.kr(0.3).range(0.85, 1);

    // Soft breath
    sig = sig + (LPF.ar(BrownNoise.ar(soft), 200) * SinOsc.kr(0.15).range(0.7, 1));

    // Green tone - mid frequency presence
    sig = sig + (BPF.ar(PinkNoise.ar(0.3), green, 0.4) * lush);

    // Ancient presence
    sig = sig + (SinOsc.ar(freq * [0.5, 1] * LFNoise1.kr(0.05).range(0.99, 1.01)) * ancient * 0.3).sum;

    sig = sig * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_sgwd_moss loaded".postln;
