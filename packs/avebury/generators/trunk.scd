// avebury/trunk — Lightweight end-stage generator
SynthDef(\forge_avebury_trunk, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var girth, grain, twist, age, sap;
    var pulse1, pulse2, sub, grainNoise, pwm, twistMod, sapMod;

    girth = p[0];
    grain = p[1];
    twist = p[2];
    age = p[3];
    sap = p[4];

    freq = In.kr(freqBus);

    // Twist modulation - very slow organic pitch drift
    twistMod = LFNoise2.kr(0.05 + (twist * 0.1)).range(0.98, 1.02);
    freq = freq * twistMod;

    // Sap flow - internal amplitude movement
    sapMod = LFNoise2.kr(0.2 + (sap * 0.5)).range(0.8, 1.0);

    // Pulse width - slow organic movement
    pwm = LFTri.kr(0.07 + (age * 0.05)).range(0.35, 0.65) * girth.linlin(0, 1, 0.8, 1.2);

    // Main pulse oscillators - thick trunk tone
    pulse1 = Pulse.ar(freq, pwm.clip(0.15, 0.85), 0.35);
    pulse2 = Pulse.ar(freq * 1.002, (1 - pwm).clip(0.15, 0.85), 0.3);

    // Sub harmonic for depth
    sub = Pulse.ar(freq * 0.5, 0.5, 0.25 * girth);
    sub = sub + SinOsc.ar(freq * 0.25, 0, 0.2 * girth);

    sig = (pulse1 + pulse2 + sub) * sapMod;

    // Wood grain texture - filtered noise
    grainNoise = BPF.ar(PinkNoise.ar(0.4), freq * 2, 0.3) * grain;
    grainNoise = grainNoise + (BPF.ar(BrownNoise.ar(0.3), freq * 0.5, 0.4) * grain * age);
    sig = sig + grainNoise;

    // Age character - add roughness
    sig = sig + (LFNoise1.ar(freq * 0.05, 0.1) * age);
    sig = sig * LFNoise2.kr(0.3 + age).range(0.85, 1.0);

    // Continuous bed
    sig = sig + BrownNoise.ar(0.04);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_avebury_trunk loaded".postln;
