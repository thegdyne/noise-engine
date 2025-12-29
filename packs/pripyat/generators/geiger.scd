SynthDef(\forge_pripyat_geiger, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var rad, prox, tube, room, deca;
    var clicks, clickRate, clickFreq, decayTime, roomSig;

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
    rad = In.kr(customBus0);
    prox = In.kr(customBus1);
    tube = In.kr(customBus2);
    room = In.kr(customBus3);
    deca = In.kr(customBus4);

    // Click rate based on radiation level
    clickRate = rad.linexp(0, 1, 0.5, 80);

    // Click frequency based on proximity and tube type
    clickFreq = freq * prox.linexp(0, 1, 0.5, 2) * tube.linlin(0, 1, 0.8, 1.5);
    decayTime = deca.linexp(0, 1, 0.005, 0.08);

    // Generate clicks with resonant character
    clicks = Dust.ar(clickRate);
    sig = Ringz.ar(clicks, [clickFreq, clickFreq * 1.02], decayTime);
    sig = sig * tube.linlin(0, 1, 0.3, 0.6);

    // Add slight pitch variation per click
    sig = sig + Ringz.ar(
        Dust.ar(clickRate * 0.3),
        clickFreq * LFNoise0.kr(10).range(0.95, 1.05),
        decayTime * 1.5
    ) * 0.3;

    // Room reflections - simple comb delay
    roomSig = CombL.ar(sig.sum, 0.1, room.linlin(0, 1, 0.01, 0.07), room.linlin(0, 1, 0.05, 0.3));
    sig = sig + (roomSig.dup * room * 0.4);

    sig = sig.sum;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_pripyat_geiger loaded".postln;
