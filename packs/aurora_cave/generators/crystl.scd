SynthDef(\forge_aurora_cave_crystl, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var clarity, ring, size, chime, ice;
    var exciter, modes, ratios, decays, amps;

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

    // Theme params
    clarity = In.kr(customBus0);
    ring = In.kr(customBus1);
    size = In.kr(customBus2);
    chime = In.kr(customBus3);
    ice = In.kr(customBus4);

    // Crystal exciter - sparse bright impulses
    exciter = Dust.ar(chime.linexp(0, 1, 1, 20)) * 0.8;
    exciter = exciter + (Impulse.ar(0) * 0.5); // Initial strike
    exciter = HPF.ar(exciter, 2000); // Bright excitation

    // Modal ratios - crystalline inharmonic series
    ratios = [1, 2.76, 5.41, 8.93, 13.34, 18.64] * size.linlin(0, 1, 0.7, 1.3);
    
    // Ring times based on modal frequency
    decays = ring.linlin(0, 1, 0.3, 3) * [1, 0.8, 0.6, 0.5, 0.4, 0.3];
    
    // Amplitude rolloff (higher modes quieter)
    amps = [1, 0.7, 0.5, 0.35, 0.25, 0.15] * clarity.linlin(0, 1, 0.5, 1);

    // Build modal resonator
    modes = Array.fill(6, { |i|
        Ringz.ar(exciter, freq * ratios[i], decays[i]) * amps[i]
    }).sum;

    // Add icy high shimmer
    modes = modes + (
        Ringz.ar(exciter * ice, freq * 21.7, 0.1) * ice * 0.1
    );
    modes = modes + (
        Ringz.ar(exciter * ice, freq * 34.2, 0.08) * ice * 0.05
    );

    sig = modes * 0.15;
    
    // Slight stereo decorrelation for space
    sig = [
        DelayC.ar(sig, 0.01, 0.002),
        DelayC.ar(sig, 0.01, 0.003)
    ];

    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_aurora_cave_crystl loaded".postln;
