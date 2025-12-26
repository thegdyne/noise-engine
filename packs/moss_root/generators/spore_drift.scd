SynthDef(\forge_moss_root_spore_drift, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var density, float, glimmer, settle, swarm;
    var dust, particles, drifted, glimmerSig, swarmMod;

    // Standard reads
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

    // Custom params
    density = In.kr(customBus0);
    float = In.kr(customBus1);
    glimmer = In.kr(customBus2);
    settle = In.kr(customBus3);
    swarm = In.kr(customBus4);

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
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_moss_root_spore_drift loaded".postln;
