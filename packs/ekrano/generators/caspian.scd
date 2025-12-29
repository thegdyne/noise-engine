SynthDef(\forge_ekrano_caspian, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var wave, chop, salt, depth, foam;
    var grainTrig, grainRate, grainFreq, grainSig, foamSig, saltSig;

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
    wave = In.kr(customBus0).linexp(0, 1, 5, 80);
    chop = In.kr(customBus1).linlin(0, 1, 0.1, 0.9);
    salt = In.kr(customBus2);
    depth = In.kr(customBus3).linexp(0, 1, 0.5, 2);
    foam = In.kr(customBus4).linlin(0, 1, 0.1, 0.8);

    // Grain trigger with choppiness variation
    grainRate = wave * LFNoise1.kr(2).range(1 - (chop * 0.5), 1 + (chop * 0.5));
    grainTrig = Dust.ar(grainRate);

    // Grain frequency modulated by depth
    grainFreq = freq * LFNoise0.kr(10).range(1 / depth, depth);

    // Granular sine clouds - water wave character
    grainSig = GrainSin.ar(
        numChannels: 2,
        trigger: grainTrig,
        dur: LFNoise1.kr(3).range(0.02, 0.08),
        freq: grainFreq,
        pan: LFNoise1.kr(5).range(-0.8, 0.8)
    );

    // Foam layer - filtered noise bursts
    foamSig = BPF.ar(
        WhiteNoise.ar(Decay.ar(Dust.ar(wave * 0.5), 0.05)),
        freq * 3,
        0.5
    ) * foam;

    // Salt spray - high frequency crackle
    saltSig = HPF.ar(Dust.ar(wave * 2) * 0.3, 6000) * salt;

    sig = (grainSig * 0.5) + (foamSig * 0.3) + (saltSig * 0.2);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ekrano_caspian loaded".postln;
