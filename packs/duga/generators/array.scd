SynthDef(\forge_duga_array, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var size, rust, tens, wind, reso;
    var exciter, modes, windNoise, tensionMod;

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
    size = In.kr(customBus0);
    rust = In.kr(customBus1);
    tens = In.kr(customBus2);
    wind = In.kr(customBus3);
    reso = In.kr(customBus4);

    // Wind noise excitation - continuous for drone mode
    windNoise = PinkNoise.ar(0.05) * LFNoise2.kr(wind.linexp(0, 1, 0.1, 2)).range(0.5, 1);
    windNoise = windNoise + (Dust.ar(wind.linexp(0, 1, 1, 10)) * 0.2);

    // Tension modulation affects pitch slightly
    tensionMod = LFNoise2.kr(0.1).range(1 - (tens * 0.02), 1 + (tens * 0.02));

    // Exciter combines wind and sparse impacts
    exciter = windNoise;

    // Modal resonances of massive steel structure
    modes = DynKlank.ar(
        `[
            [1, 1.5, 2.2, 3.1, 4.7, 6.3] * size.linlin(0, 1, 1.5, 0.5),
            [1, 0.7, 0.5, 0.3, 0.2, 0.15] * (1 - (rust * 0.4)),
            [2, 1.8, 1.5, 1.2, 1, 0.8] * reso.linlin(0, 1, 0.5, 2)
        ],
        exciter,
        freq * tensionMod,
        0,
        size.linexp(0, 1, 1, 4)
    );

    sig = modes * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_duga_array loaded".postln;
