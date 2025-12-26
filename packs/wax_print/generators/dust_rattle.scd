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

SynthDef(\forge_wax_print_dust_rattle, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var density, size, shell, shake, ring;
    var particles, shellRes, envTrig;

    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);

    density = In.kr(customBus0).linexp(0, 1, 10, 500);
    size = In.kr(customBus1).linexp(0, 1, 0.5, 2.0);
    shell = In.kr(customBus2).linlin(0, 1, 0.0, 1.0);
    shake = In.kr(customBus3).linlin(0, 1, 0.3, 1.0);
    ring = In.kr(customBus4).linlin(0, 1, 0.0, 1.0);

    envTrig = Select.ar(envSource, [
        DC.ar(1),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);

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
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_wax_print_dust_rattle loaded".postln;
