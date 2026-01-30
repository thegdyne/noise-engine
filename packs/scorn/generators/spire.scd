// scorn/spire — Lightweight end-stage generator
// spire: Towering structure - hollow resonance
SynthDef(\forge_scorn_spire, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var tower, hollow, wind, creak, ancient;

    tower = p[0].linlin(0, 1, 0.4, 1);  // P1: Tower presence
    hollow = p[1].linlin(0, 1, 0.015, 0.08);  // P2: Hollow depth
    wind = p[2].linlin(0, 1, 0.3, 0.8);  // P3: Wind through
    creak = p[3].linlin(0, 1, 1, 6);  // P4: Structural creak
    ancient = p[4].linlin(0, 1, 0.2, 0.6);  // P5: Ancient presence

    freq = In.kr(freqBus);

    // DSP: Continuous tower body tone (always present)
    sig = Saw.ar(freq * [1, 1.002]) * tower * 0.3;

    // Ancient presence - deep drone (boosted)
    sig = sig + (SinOsc.ar(freq * [0.25, 0.5] * LFNoise1.kr(0.05).range(0.98, 1.02)) * ancient * 0.35);

    // Hollow resonance - comb delay
    sig = sig + CombL.ar(PinkNoise.ar(tower * 0.35), 0.1, hollow, 1.8);

    // Wind through structure (boosted)
    sig = sig + (BPF.ar(PinkNoise.ar(wind * 0.6), freq * [2, 3, 5] * LFNoise1.kr(0.2).range(0.9, 1.1), 0.2));

    // Structural creak (boosted)
    sig = sig + (Ringz.ar(Dust.ar(creak) * 0.2, freq * [0.5, 1, 1.5], 0.25) * tower * 0.5);

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_scorn_spire loaded".postln;
