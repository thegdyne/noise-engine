SynthDef(\forge_overgrown_spore_drift, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var density, scatter, glow, drift, grainSize;
    var grains, shimmer, dust1, dust2, mod1, mod2;

    // Theme params
    density = In.kr(customBus0);
    scatter = In.kr(customBus1);
    glow = In.kr(customBus2);
    drift = In.kr(customBus3);
    grainSize = In.kr(customBus4);

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

    // Slow drift modulation
    mod1 = SinOsc.kr(drift.linexp(0, 1, 0.02, 0.5)).range(0.98, 1.02);
    mod2 = SinOsc.kr(drift.linexp(0, 1, 0.03, 0.7), pi/2).range(0.97, 1.03);

    // Grain triggers - continuous dust for drone mode
    dust1 = Dust.ar(density.linexp(0, 1, 2, 40));
    dust2 = Dust.ar(density.linexp(0, 1, 3, 50));

    // Granular sine particles
    grains = SinOsc.ar(freq * mod1 * [1, 1.002]) * Decay2.ar(dust1, 0.001, grainSize.linexp(0, 1, 0.02, 0.3));
    grains = grains + (SinOsc.ar(freq * 2 * mod2 * [1.001, 1]) * Decay2.ar(dust2, 0.001, grainSize.linexp(0, 1, 0.015, 0.2)) * 0.5);
    grains = grains + (SinOsc.ar(freq * 3 * mod1 * [1, 1.003]) * Decay2.ar(Dust.ar(density.linexp(0, 1, 1, 20)), 0.001, grainSize.linexp(0, 1, 0.01, 0.15)) * 0.25);

    // Harmonic shimmer layer
    shimmer = SinOsc.ar(freq * [4.01, 3.99]) * LFNoise1.kr(0.5).range(0, 1) * glow * 0.15;
    shimmer = shimmer + (SinOsc.ar(freq * [5.02, 4.98]) * LFNoise1.kr(0.7).range(0, 1) * glow * 0.08);

    // Soft noise bed for continuous drone
    sig = grains + shimmer + (PinkNoise.ar(0.02 * density) * [1, 1]);

    // Scatter - stereo width
    sig = Balance2.ar(sig[0], sig[1], LFNoise1.kr(scatter.linexp(0, 1, 0.1, 2)).range(scatter.neg, scatter));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_overgrown_spore_drift loaded".postln;
