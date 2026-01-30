// tricorn/slab — Lightweight end-stage generator
SynthDef(\forge_tricorn_slab, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var mass, weight, stress, grit, pressure;
    var pulse1, pulse2, sub, noisemod, pwm;

    mass = p[0];
    weight = p[1];
    stress = p[2];
    grit = p[3];
    pressure = p[4];

    freq = In.kr(freqBus);

    // Pulse width modulation - slow, heavy
    pwm = LFTri.kr(0.1 + (stress * 0.3)).range(0.3, 0.7) * mass;

    // Main pulse oscillators with stress detuning
    pulse1 = Pulse.ar(freq * (1 + (stress * 0.01)), pwm.clip(0.1, 0.9), 0.4);
    pulse2 = Pulse.ar(freq * (1 - (stress * 0.01)) * 0.999, (1 - pwm).clip(0.1, 0.9), 0.4);

    // Sub harmonic for weight
    sub = Pulse.ar(freq * 0.5, 0.5, weight * 0.5);
    sub = sub + SinOsc.ar(freq * 0.25, 0, weight * 0.3);

    // Combine
    sig = pulse1 + pulse2 + sub;

    // Grit modulation - noise on amplitude
    noisemod = LFNoise1.kr(2 + (grit * 5)).range(0.8, 1.0);
    sig = sig * noisemod;

    // Add filtered noise layer for texture
    sig = sig + (BrownNoise.ar(0.15) * grit);

    // Pressure drive - soft clip
    sig = (sig * (1 + (pressure * 2))).tanh * (1 / (1 + pressure));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_tricorn_slab loaded".postln;
