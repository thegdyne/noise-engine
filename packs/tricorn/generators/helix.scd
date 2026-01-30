// tricorn/helix — Lightweight end-stage generator
SynthDef(\forge_tricorn_helix, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var rotation, radius, gradient, vertigo, motion;
    var modRate, modDepth, ratio, carrier, modulator, phase1, phase2;

    rotation = p[0];
    radius = p[1];
    gradient = p[2];
    vertigo = p[3];
    motion = p[4];

    freq = In.kr(freqBus);

    // Modulation parameters
    modRate = rotation.linexp(0, 1, 0.1, 4);
    modDepth = radius.linlin(0, 1, 0.5, 8);
    ratio = gradient.linlin(0, 1, 1, 4);

    // Phase modulators - spiral motion
    phase1 = SinOsc.ar(freq * ratio, 0, modDepth);
    phase1 = phase1 * LFTri.kr(modRate).range(0.3, 1.0);

    // Vertigo - chaotic phase perturbation
    phase1 = phase1 + (LFNoise2.ar(freq * 0.1) * vertigo * 2);

    // Second modulator for thickness
    phase2 = SinOsc.ar(freq * (ratio + 0.01), 0, modDepth * 0.7);
    phase2 = phase2 * LFTri.kr(modRate * 1.01).range(0.3, 1.0);

    // Carriers with phase modulation
    carrier = SinOsc.ar(freq, phase1, 0.4);
    carrier = carrier + SinOsc.ar(freq * 1.001, phase2, 0.35);

    // Motion spread - additional detuned layers
    carrier = carrier + SinOsc.ar(freq * (1 + (motion * 0.005)), phase1 * 0.8, 0.2 * motion);
    carrier = carrier + SinOsc.ar(freq * (1 - (motion * 0.005)), phase2 * 0.8, 0.2 * motion);

    sig = carrier;

    // Add sub for weight
    sig = sig + SinOsc.ar(freq * 0.5, 0, 0.15);

    // Continuous presence layer
    sig = sig + (PinkNoise.ar(0.02));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_tricorn_helix loaded".postln;
