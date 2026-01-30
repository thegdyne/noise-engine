// moss_root/spore_drift — Lightweight end-stage generator
SynthDef(\forge_moss_root_spore_drift, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var density, float, glimmer, settle, swarm;
    var dust, particles, drifted, glimmerSig, swarmMod;

    freq = In.kr(freqBus);

    density = p[0];
    float = p[1];
    glimmer = p[2];
    settle = p[3];
    swarm = p[4];

    // Swarm modulation: clustered bursts
    swarmMod = LFNoise1.kr(swarm.linexp(0, 1, 0.2, 2)).range(
        1 - (swarm * 0.7),
        1 + (swarm * 0.5)
    );

    // Base dust particles at various densities
    dust = Mix([
        Dust.ar(density.linexp(0, 1, 5, 80) * swarmMod),
        Dust2.ar(density.linexp(0, 1, 3, 40) * swarmMod) * 0.5
    ]);

    // Resonant particles at frequency-related pitches
    particles = Mix(Array.fill(4, { |i|
        var partFreq = freq * [1, 1.5, 2, 3][i];
        var decayTime = settle.linexp(0, 1, 0.5, 0.05);
        Ringz.ar(dust * (0.4 - (i * 0.08)), partFreq.clip(80, 12000), decayTime)
    })) * 0.25;

    // Add soft sine layer for body
    particles = particles + (SinOsc.ar(freq) * dust * settle.linexp(0, 1, 0.2, 0.05));

    // Float: delay network for drifting effect
    drifted = Mix([
        DelayL.ar(particles, 0.5, float.linlin(0, 1, 0.05, 0.3) + LFNoise1.kr(0.5).range(0, 0.05)) * 0.4,
        DelayL.ar(particles, 0.5, float.linlin(0, 1, 0.1, 0.4) + LFNoise1.kr(0.3).range(0, 0.08)) * 0.3,
        CombL.ar(particles, 0.3, float.linlin(0, 1, 0.08, 0.2), float.linlin(0, 1, 0.3, 1.5)) * 0.2
    ]);

    sig = particles + drifted;

    // Glimmer: high frequency sparkle
    glimmerSig = Ringz.ar(
        Dust.ar(density.linexp(0, 1, 10, 100) * glimmer),
        freq * 6,
        0.02
    ) * glimmer * 0.2;
    glimmerSig = HPF.ar(glimmerSig, 4000);
    sig = sig + glimmerSig;

    // Random stereo placement for floating effect
    sig = Pan2.ar(sig, LFNoise1.kr(float.linexp(0, 1, 0.2, 1.5)).range(-0.8, 0.8));

    // MANDATORY output chain
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_moss_root_spore_drift loaded".postln;
