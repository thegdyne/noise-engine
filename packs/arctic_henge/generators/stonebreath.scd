SynthDef(\forge_arctic_henge_stonebreath, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var gale, howl, gust, arch, freeze;
    var wind, gustMod, archRes, iceOvertones;

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
    gale = In.kr(customBus0);
    howl = In.kr(customBus1);
    gust = In.kr(customBus2);
    arch = In.kr(customBus3);
    freeze = In.kr(customBus4);

    // Gust modulation - turbulent wind
    gustMod = LFNoise2.kr(gust.linexp(0, 1, 0.2, 4)) * gust;

    // Base wind - filtered noise
    wind = PinkNoise.ar * gale;
    wind = wind + (BrownNoise.ar * gale * 0.5);

    // Howling resonance
    wind = BPF.ar(
        wind,
        howl.linexp(0, 1, 200, 2000) * (1 + (gustMod * 0.3)),
        arch.linexp(0, 1, 0.5, 0.05)
    );

    // Arch resonators - stone tube resonance
    archRes = Mix.fill(4, { |i|
        var resFreq = freq * (i + 1) * arch.linlin(0, 1, 0.8, 1.2);
        Ringz.ar(
            wind * 0.3,
            resFreq.min(6000),
            arch.linexp(0, 1, 0.2, 1.5)
        ) * (0.2 / (i + 1))
    });

    // Ice crystal overtones - high sparkle
    iceOvertones = Mix.fill(6, { |i|
        var iceFreq = freq * (8 + i) * (1 + (LFNoise1.kr(0.5) * 0.01));
        Ringz.ar(
            Dust.ar(freeze.linexp(0, 1, 1, 20)),
            iceFreq.min(12000),
            0.1
        ) * freeze * 0.05
    });

    sig = wind + archRes + iceOvertones;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_arctic_henge_stonebreath loaded".postln;
