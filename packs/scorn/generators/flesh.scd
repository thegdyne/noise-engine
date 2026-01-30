// scorn/flesh — Lightweight end-stage generator
// flesh: Organic walls - wet membrane texture
SynthDef(\forge_scorn_flesh, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var wet, membrane, squelch, warmth, breath;

    wet = p[0].linlin(0, 1, 0.3, 0.9);  // P1: Wetness
    membrane = p[1].linlin(0, 1, 0.2, 0.8);  // P2: Membrane flex
    squelch = p[2].linlin(0, 1, 3, 20);  // P3: Squelch rate
    warmth = p[3].linlin(0, 1, 200, 1200);  // P4: Body warmth
    breath = p[4].linlin(0, 1, 0.05, 0.2);  // P5: Breathing rate

    freq = In.kr(freqBus);

    // DSP: Membrane texture - continuous filtered noise
    sig = LPF.ar(BrownNoise.ar(wet * 0.5), warmth) * SinOsc.kr(breath).range(0.7, 1);

    // Wet squelch sounds
    sig = sig + (Ringz.ar(Dust.ar(squelch) * 0.2, freq * [1, 1.5, 2], 0.1) * wet * 0.4);

    // Membrane flex - low resonance
    sig = sig + (SinOsc.ar(freq * [0.5, 1] * LFNoise1.kr(0.1).range(0.98, 1.02)) * membrane * 0.3);

    // Organic warmth
    sig = sig + (LPF.ar(Pulse.ar(freq * 0.5, 0.3), warmth) * membrane * 0.2);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_scorn_flesh loaded".postln;
