// rlyeh/abyss — Lightweight end-stage generator
// abyss: The deep unknown - impenetrable darkness below
SynthDef(\forge_rlyeh_abyss, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var darkness, pressure, movement, cold, void;

    darkness = p[0].linlin(0, 1, 200, 2000);  // P1: Filter darkness
    pressure = p[1].linlin(0, 1, 0.3, 1);  // P2: Crushing pressure
    movement = p[2].linlin(0, 1, 0.02, 0.2);  // P3: Slow movement rate
    cold = p[3].linlin(0, 1, 0, 0.4);  // P4: Cold shimmer
    void = p[4].linlin(0, 1, 0, 0.6);  // P5: Void noise

    freq = In.kr(freqBus);

    // DSP: Deep dark pad
    sig = Pulse.ar(freq * [0.5, 0.501, 1, 1.002], LFNoise1.kr(movement).range(0.3, 0.7));
    sig = Splay.ar(sig, 0.6) * pressure;

    // Darkness filter
    sig = LPF.ar(sig, darkness * LFNoise1.kr(movement).range(0.7, 1.3));

    // Cold shimmer
    sig = sig + (SinOsc.ar(freq * [4, 5.01, 6.02]) * cold * LFNoise1.kr(movement * 2).range(0, 1) * 0.1);

    // Void noise layer
    sig = sig + (LPF.ar(PinkNoise.ar(void), darkness * 0.5) * 0.3);

    sig = sig * 0.3;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_rlyeh_abyss loaded".postln;
