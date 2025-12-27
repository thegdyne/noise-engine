// ice_mirror: Reflections on frozen water - comb/delay shimmer
SynthDef(\forge_hoar_frost_ice_mirror, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var feedback, shimmer, spread, combTune, glisten;

    // Theme params
    feedback = In.kr(customBus0).linlin(0, 1, 0.3, 0.85);  // P1: Comb feedback
    shimmer = In.kr(customBus1).linlin(0, 1, 0.1, 2);      // P2: Shimmer rate
    spread = In.kr(customBus2).linlin(0, 1, 0.001, 0.01);  // P3: Stereo spread delay
    combTune = In.kr(customBus3).linlin(0, 1, 0.5, 2);     // P4: Comb tuning ratio
    glisten = In.kr(customBus4).linlin(0, 1, 0, 0.5);      // P5: High frequency sparkle

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

    // DSP: Resonant comb with shimmer modulation
    sig = Saw.ar(freq * [1, 1.003]) * 0.3;

    // Comb filters tuned to frequency
    sig = CombL.ar(sig,
        0.1,
        (freq * combTune).reciprocal * (1 + (SinOsc.kr(shimmer).range(0, 0.02))),
        feedback * 2
    );

    // Add high glisten
    sig = sig + (Ringz.ar(
        Dust.ar(shimmer * 5) * 0.1,
        freq * [4, 5, 6],
        0.1
    ).sum * glisten);

    // Stereo delay spread
    sig = [
        DelayL.ar(sig[0], 0.02, spread),
        DelayL.ar(sig[1], 0.02, spread * 1.3)
    ];

    sig = sig * 0.4;

    // Output chain (with Limiter for feedback safety)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_hoar_frost_ice_mirror loaded".postln;
