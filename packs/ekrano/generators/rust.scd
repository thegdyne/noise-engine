SynthDef(\forge_ekrano_rust, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var dustParam, creak, peel, grit, voidParam;
    var dustTrig, creakSig, gritSig, resSig, voidSig;

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
    dustParam = In.kr(customBus0).linexp(0, 1, 1, 30);
    creak = In.kr(customBus1).linexp(0, 1, 0.5, 4);
    peel = In.kr(customBus2).linexp(0, 1, 0.1, 2);
    grit = In.kr(customBus3);
    voidParam = In.kr(customBus4);

    // Dust triggers
    dustTrig = Dust.ar(dustParam);

    // Creaking resonator - metal stress sounds
    creakSig = Ringz.ar(
        dustTrig,
        freq * creak * LFNoise1.kr(0.5).range(0.9, 1.1),
        peel
    ) * 0.3;

    // Secondary resonance at different pitch
    resSig = Ringz.ar(
        dustTrig,
        freq * creak * 1.7,
        peel * 0.7
    ) * 0.2;

    // Grit noise layer
    gritSig = BPF.ar(
        GrayNoise.ar(0.3) * Decay.ar(dustTrig, 0.05),
        freq * 2,
        0.8
    ) * grit;

    // Void - sparse reverberant space
    voidSig = CombL.ar(creakSig + resSig, 0.5, 0.3, 3) * voidParam * 0.3;

    sig = creakSig + resSig + gritSig + voidSig;

    // Add subtle continuous noise bed for drone mode
    sig = sig + (BrownNoise.ar(0.02) * (1 - grit));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ekrano_rust loaded".postln;
