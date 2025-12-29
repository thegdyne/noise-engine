SynthDef(\forge_pripyat_echo, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var size, conc, empt, drip, chill;
    var exciter, combs, dripSig, delayTime, decayTime, dripRate;

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
    conc = In.kr(customBus1);
    empt = In.kr(customBus2);
    drip = In.kr(customBus3);
    chill = In.kr(customBus4);

    // Continuous noise bed for drone mode
    exciter = PinkNoise.ar(0.05);
    // Add sparse impulses
    exciter = exciter + (Dust.ar(empt.linexp(0, 1, 3, 0.5)) * 0.3);

    // Water drips
    dripRate = drip.linexp(0, 1, 0.5, 4);
    dripSig = Dust.ar(dripRate);
    dripSig = Ringz.ar(dripSig, freq * LFNoise0.kr(dripRate).range(2, 6), 0.15) * drip * 0.5;

    // Add drips to exciter
    exciter = exciter + dripSig;

    // Delay time based on size (room dimensions)
    delayTime = size.linexp(0, 1, 0.01, 0.15);
    decayTime = size.linlin(0, 1, 0.5, 4) * (1 - (chill * 0.5));

    // Multiple comb filters for concrete resonance
    combs = CombL.ar(exciter, 0.2, delayTime, decayTime);
    combs = combs + CombL.ar(exciter, 0.2, delayTime * 0.7, decayTime * 0.8);
    combs = combs + CombL.ar(exciter, 0.2, delayTime * 1.3, decayTime * 0.9);

    // Pitch the resonance
    sig = Resonz.ar(combs, freq, conc.linexp(0, 1, 0.5, 0.1));
    sig = sig * conc.linlin(0, 1, 2, 8); // Gain compensation for resonance

    // Cold dampening - reduce highs
    sig = LPF.ar(sig, chill.linexp(0, 1, 12000, 2000));

    // Add some of the raw combs for body
    sig = sig + (combs * 0.5);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_pripyat_echo loaded".postln;
