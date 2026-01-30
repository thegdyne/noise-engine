// icarus/ash — Lightweight end-stage generator
// Ash -- disintegration, becoming particles
// Role: accent

SynthDef(\forge_icarus_ash, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var scatter, ember, dust, fade, memory;
    var particles, glow, fine, echo, scatterRate;

    freq = In.kr(freqBus);

    scatter = p[0].linlin(0, 1, 5, 60);  // Particle rate
    ember = p[1].linlin(0, 1, 0.0, 0.5);  // Glow level
    dust = p[2].linlin(0, 1, 20, 200);  // Fine dust density
    fade = p[3].linlin(0, 1, 0.5, 0.05);  // Ring time
    memory = p[4].linlin(0, 1, 0.0, 0.5);  // Echo feedback

    // Scattering particles - pitched impulses
    particles = Dust.ar(scatter);
    particles = Ringz.ar(particles, freq * LFNoise0.kr(scatter * 0.1, 1, 2), fade);

    // Glowing embers - sine tones with random decay
    glow = SinOsc.ar(freq * LFNoise2.kr(2, 0.1, 1), 0, ember);
    glow = glow * LFNoise2.kr(4, 0.5, 0.5);

    // Fine dust - high density tiny particles
    fine = Dust2.ar(dust) * 0.2;
    fine = HPF.ar(fine, 2000);
    fine = Ringz.ar(fine, freq * 4 * LFNoise0.kr(10, 0.5, 1), 0.01);

    // Memory echoes - comb filter feedback
    echo = particles + glow;
    echo = CombL.ar(echo, 0.5, freq.reciprocal, memory * 2);

    // Combine - everything dissolving
    sig = particles + glow + fine + (echo * memory);

    // Wide scatter across stereo field
    sig = ~stereoSpread.(sig, 0.5, 0.8);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_icarus_ash loaded".postln;
