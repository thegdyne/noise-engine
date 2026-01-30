// sgwd/stone — Lightweight end-stage generator
// stone: Ancient rock ledge resonance
SynthDef(\forge_sgwd_stone, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var ledge, mass, wet, age, hollow;

    ledge = p[0].linlin(0, 1, 0.3, 0.8);  // P1: Ledge resonance
    mass = p[1].linlin(0, 1, 0.5, 2);  // P2: Stone mass (decay)
    wet = p[2].linlin(0, 1, 0.2, 0.6);  // P3: Wet surface
    age = p[3].linlin(0, 1, 0.1, 0.4);  // P4: Weathered
    hollow = p[4].linlin(0, 1, 0.02, 0.08);  // P5: Hollow behind

    freq = In.kr(freqBus);

    // DSP: Stone resonance
    // Deep rock drone
    sig = SinOsc.ar(freq * [0.5, 1, 1.5] * LFNoise1.kr(0.05).range(0.99, 1.01)) * [0.4, 0.3, 0.2];
    sig = sig.sum;

    // Ledge resonance - comb filtering
    sig = sig + CombL.ar(PinkNoise.ar(ledge * 0.2), 0.1, freq.reciprocal, mass);

    // Wet surface drips
    sig = sig + (Ringz.ar(Dust.ar(wet * 8) * 0.15, freq * [2, 3, 5], 0.2).sum);

    // Hollow space behind
    sig = sig + CombL.ar(sig * 0.3, 0.1, hollow, mass * 0.5);

    // Age texture
    sig = sig + (LPF.ar(BrownNoise.ar(age * 0.2), 150));

    sig = sig * 0.35;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_sgwd_stone loaded".postln;
