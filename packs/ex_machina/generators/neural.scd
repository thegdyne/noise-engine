// ex_machina/neural — Lightweight end-stage generator
// neural: Processing thoughts - digital cognition
SynthDef(\forge_ex_machina_neural, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var process, spark, depth, cascade, dream;

    process = p[0].linlin(0, 1, 10, 50);  // P1: Processing rate
    spark = p[1].linlin(0, 1, 0.2, 0.7);  // P2: Neural spark
    depth = p[2].linlin(0, 1, 0.3, 0.9);  // P3: Thought depth
    cascade = p[3].linlin(0, 1, 0.1, 0.6);  // P4: Cascade events
    dream = p[4].linlin(0, 1, 0.2, 0.6);  // P5: Dream state

    freq = In.kr(freqBus);

    // DSP: Continuous processing hum (always present)
    sig = BPF.ar(WhiteNoise.ar(depth * 0.4), 4000, 0.2);
    sig = sig + (SinOsc.ar(freq * [1, 2]) * depth * 0.2);

    // Neural sparks - high frequency clicks (boosted)
    sig = sig + (Ringz.ar(Dust.ar(process) * 0.25, freq * [8, 10, 12, 16], 0.03) * spark * 0.6);

    // Thought depth - layered digital tones
    sig = sig + (Pulse.ar(freq * [1, 2, 4] * LFNoise0.kr(0.5).range(0.98, 1.02), 0.2) * depth * 0.2);

    // Cascade events - rapid sequences
    sig = sig + (Ringz.ar(Dust.ar(cascade * 40) * 0.12, freq * LFNoise0.kr(10).range(2, 8), 0.015) * cascade);

    // Dream state - soft wandering
    sig = sig + (SinOsc.ar(freq * LFNoise1.kr(0.2).range(0.5, 2)) * dream * 0.25);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ex_machina_neural loaded".postln;
