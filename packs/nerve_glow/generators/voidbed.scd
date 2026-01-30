// nerve_glow/voidbed — Lightweight end-stage generator
// VOIDBED -- Deep void background
// Dark filtered noise drone -- the black space around the tissue

SynthDef(\forge_nerve_glow_voidbed, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var depth, viscosity, darkness, flow, abyss;
    var noise, sub, movement, cutMod;

    // Standard bus reads
    freq = In.kr(freqBus);

    depth = p[0].linexp(0, 1, 100, 30);  // Base frequency (inverted for depth)
    viscosity = p[1].linexp(0, 1, 0.02, 0.5);  // Filter movement rate
    darkness = p[2].linexp(0, 1, 4000, 200);  // HF cutoff (inverted)
    flow = p[3].linexp(0, 1, 0.05, 2.0);  // Internal modulation
    abyss = p[4].linlin(0, 1, 0.0, 0.8);  // Sub amount

    // Deep noise layers
    noise = BrownNoise.ar(0.5) + (PinkNoise.ar(0.2));

    // Slow filter movement
    cutMod = SinOsc.kr(flow, 0, 0.3, 1);
    noise = LPF.ar(noise, darkness * cutMod);
    noise = LPF.ar(noise, darkness * 0.5);  // Extra darkness

    // Resonant depth
    movement = BPF.ar(noise, freq.clip(20, 500), 0.2) * depth.reciprocal.linlin(30, 100, 0.5, 2);

    // Sub harmonic rumble
    sub = SinOsc.ar(freq * 0.5) * abyss * 0.3;
    sub = sub * LFNoise1.kr(viscosity).range(0.5, 1);

    sig = (noise * 0.4) + (movement * 0.4) + sub;

    // Very slow stereo drift
    sig = [
        DelayN.ar(sig, 0.05, SinOsc.kr(viscosity * 0.3, 0, 0.02, 0.025)),
        DelayN.ar(sig, 0.05, SinOsc.kr(viscosity * 0.3, pi, 0.02, 0.025))
    ];

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_nerve_glow_voidbed loaded".postln;
