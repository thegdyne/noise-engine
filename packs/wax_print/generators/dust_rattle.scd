// wax_print/dust_rattle — Lightweight end-stage generator
// ============================================================================
// WAX_PRINT: Dust Rattle
// Role: Accent - shakers, seed pods, ankle rattles
//
// DNS (Density)  - Seed/bead count, particle density
// SIZ (Size)     - Particle size, pitch of impacts
// SHL (Shell)    - Container material, resonance
// SHK (Shake)    - Shake intensity, movement amount
// RNG (Ring)     - Metal vs organic ring character
// ============================================================================

SynthDef(\forge_wax_print_dust_rattle, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var density, size, shell, shake, ring;
    var particles, shellRes, envTrig;

    freq = In.kr(freqBus);

    density = p[0].linexp(0, 1, 10, 500);
    size = p[1].linexp(0, 1, 0.5, 2.0);
    shell = p[2].linlin(0, 1, 0.0, 1.0);
    shake = p[3].linlin(0, 1, 0.3, 1.0);
    ring = p[4].linlin(0, 1, 0.0, 1.0);

    // One-shot trigger (end-stage handles retriggering)
    envTrig = Impulse.ar(0);

    // Particle impacts
    particles = Dust.ar(density * shake) * 0.5;
    particles = Ringz.ar(particles, freq * size * LFNoise0.kr(20).range(0.8, 1.2), 0.01 + (ring * 0.03));
    particles = particles + Ringz.ar(Dust.ar(density * shake * 0.5), freq * size * 2, 0.008) * 0.5;
    particles = HPF.ar(particles, 500);

    // Shell resonance
    shellRes = Ringz.ar(particles, freq * 0.5, 0.1 * shell);
    shellRes = shellRes + Resonz.ar(particles, freq, 0.2) * shell * 2;
    shellRes = LPF.ar(shellRes, 3000);

    // Crackle texture for organic feel
    sig = particles + shellRes + (Crackle.ar(1.5 + (shake * 0.3)) * (1 - ring) * 0.05);

    sig = sig * EnvGen.ar(Env.perc(0.001, 0.3), Trig.ar(envTrig, 0.01));
    sig = (sig * 3).tanh * 0.5;

    sig = ~stereoSpread.(sig, 0.3, 0.5);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_wax_print_dust_rattle loaded".postln;
