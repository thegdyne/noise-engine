// ICEBELL - Crystalline struck ice
// Modal resonator with inharmonic ice ratios

SynthDef(\forge_glacialis_icebell, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                      filterTypeBus, envEnabledBus, envSourceBus=0,
                                      clockRateBus, clockTrigBus,
                                      midiTrigBus=0, slotIndex=0,
                                      customBus0, customBus1, customBus2, customBus3, customBus4,
                                      portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var crystal, ring, strike, frost, size;
    var exciter, modes, ratios, decays, shimmer;

    // Theme params
    crystal = In.kr(customBus0);   // Inharmonicity
    ring = In.kr(customBus1);      // Ring time
    strike = In.kr(customBus2);    // Strike brightness
    frost = In.kr(customBus3);     // High shimmer
    size = In.kr(customBus4);      // Modal spread

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

    // Ice-like modal ratios (between harmonic and bar modes)
    ratios = [1, 2.32, 3.86, 5.17, 6.71, 8.23];
    ratios = ratios + (crystal * [0, 0.24, 0.41, 0.52, 0.38, 0.27]);
    ratios = ratios * (1 + (size * 0.3 * [0, 0.1, -0.05, 0.15, -0.1, 0.08]));

    // Per-mode decay times
    decays = ring.linexp(0, 1, 0.3, 4.0) * [1, 0.8, 0.6, 0.5, 0.4, 0.35];

    // Bright noise exciter
    exciter = WhiteNoise.ar(1) * Env.perc(0.001, 0.01 + (strike * 0.03)).ar(0);
    exciter = HPF.ar(exciter, strike.linexp(0, 1, 500, 3000));

    // Modal resonators
    modes = Mix.fill(6, { |i|
        Ringz.ar(exciter, (freq * ratios[i]).clip(20, 18000), decays[i]) * (i + 1).reciprocal
    });

    sig = modes * 0.15;

    // High frequency frost shimmer
    shimmer = Ringz.ar(exciter * frost,
        freq * [9.7, 12.3, 15.1],
        ring.linexp(0, 1, 0.1, 0.5) * 0.3
    ).sum * 0.1 * frost;

    sig = sig + shimmer;

    // Subtle stereo from size
    sig = [sig, DelayC.ar(sig, 0.01, size * 0.005)];

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_glacialis_icebell loaded".postln;
