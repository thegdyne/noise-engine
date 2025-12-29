SynthDef(\forge_ekrano_hull, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var mass, strike, sizeParam, ring, damp;
    var exciter, modes, decayTime, trigRate;

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
    mass = In.kr(customBus0).linexp(0, 1, 0.5, 4);
    strike = In.kr(customBus1).linlin(0, 1, 0.1, 0.6);
    sizeParam = In.kr(customBus2).linlin(0, 1, 0.5, 2);
    ring = In.kr(customBus3).linlin(0, 1, 0.3, 0.95);
    damp = In.kr(customBus4).linlin(0, 1, 0.1, 0.8);

    // Decay time based on mass
    decayTime = mass * (1 - (damp * 0.5));

    // Continuous excitation using Dust - avoids drone silence
    trigRate = strike.linexp(0.1, 0.6, 1, 8);
    exciter = Dust.ar(trigRate) * strike;
    exciter = exciter + (PinkNoise.ar(0.02) * (1 - damp));

    // Modal resonator - aluminum hull modes
    modes = DynKlank.ar(
        `[
            [1, 1.6, 2.3, 2.9, 4.1, 5.2, 6.8] * sizeParam,
            [1, 0.7, 0.5, 0.4, 0.25, 0.15, 0.1] * ring,
            [1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4] * decayTime
        ],
        exciter,
        freq,
        0,
        decayTime
    );

    sig = modes * 0.3;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ekrano_hull loaded".postln;
