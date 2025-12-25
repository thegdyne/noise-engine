SynthDef(\forge_fuego_celeste_cosmic_dust, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                             filterTypeBus, envEnabledBus, envSourceBus=0,
                                             clockRateBus, clockTrigBus,
                                             midiTrigBus=0, slotIndex=0,
                                             customBus0, customBus1, customBus2, customBus3, customBus4,
                                             portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var cloud, shimmer, fine, drift, glitter;
    var dustCloud, shimmerMod, fineFreq, driftLFO, glitterPings, dustBase;

    // Standard bus reads
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

    // Theme parameters
    cloud = In.kr(customBus0);      // density
    shimmer = In.kr(customBus1);    // light scattering
    fine = In.kr(customBus2);       // particle size
    drift = In.kr(customBus3);      // movement
    glitter = In.kr(customBus4);    // sparkle

    // Fine frequency - smaller particles = higher frequencies
    fineFreq = fine.linexp(0, 1, 2000, 12000);

    // Drift modulation - slow cosmic movement
    driftLFO = LFNoise1.kr(drift.linexp(0, 1, 0.05, 0.5)).range(0.95, 1.05);

    // Dust cloud base - filtered noise
    dustBase = WhiteNoise.ar * cloud * 0.3;
    dustBase = BPF.ar(dustBase, fineFreq * driftLFO, 0.5);

    // Shimmer modulation - rapid amplitude flutter
    shimmerMod = SinOsc.kr(shimmer.linexp(0, 1, 5, 30)).range(0.6, 1.0);
    dustBase = dustBase * shimmerMod;

    // Add subtle tonal component
    dustCloud = dustBase + (SinOsc.ar(freq * 4 * driftLFO, 0, 0.1 * cloud));

    // Glitter - bright random sparkles
    glitterPings = Dust.ar(glitter.linexp(0, 1, 5, 80));
    glitterPings = Ringz.ar(glitterPings, fineFreq * [1, 1.2, 1.5], 0.05);
    glitterPings = Mix(glitterPings) * glitter * 0.4;

    // Add high frequency dust particles
    glitterPings = glitterPings + (Dust2.ar(cloud.linexp(0, 1, 50, 500)) * 0.1);
    glitterPings = HPF.ar(glitterPings, 4000);

    // Mix
    sig = dustCloud + glitterPings;

    // Stereo spread with drift
    sig = Pan2.ar(sig, LFNoise1.kr(drift * 2).range(-0.7, 0.7));

    // Standard post-chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_fuego_celeste_cosmic_dust loaded".postln;
