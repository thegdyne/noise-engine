SynthDef(\forge_moss_root_leaf_fall, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var rustle, wind, wet, pile, curl;
    var leaves, crunch, pileDelay;

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
    rustle = In.kr(customBus0);
    wind = In.kr(customBus1);
    wet = In.kr(customBus2);
    pile = In.kr(customBus3);
    curl = In.kr(customBus4);

    // Multiple rustling layers
    leaves = Mix(Array.fill(4, { |i|
        var rate = wind.linexp(0, 1, 2, 20) * (1 + (i * 0.3));
        var noiseFreq = freq * (2 + i);
        var ampMod = LFNoise2.kr(rate).range(0, 1);
        var layer = BPF.ar(
            WhiteNoise.ar,
            noiseFreq.clip(100, 10000),
            curl.linexp(0, 1, 0.5, 0.1)
        ) * ampMod;
        layer * (rustle / 4)
    }));

    // Crunch: high-frequency crackle
    crunch = HPF.ar(
        Dust2.ar(wind.linexp(0, 1, 50, 500) * rustle) * 0.3,
        curl.linexp(0, 1, 3000, 6000)
    ) * curl;

    sig = leaves + crunch;

    // Wetness: dampen high frequencies
    sig = LPF.ar(sig, wet.linexp(0, 1, 12000, 2000));
    sig = sig * wet.linlin(0, 1, 1, 0.6); // Wet leaves are quieter

    // Pile: multiple short delays for depth
    pileDelay = Mix([
        DelayL.ar(sig, 0.1, 0.02) * 0.3,
        DelayL.ar(sig, 0.1, 0.05) * 0.2,
        DelayL.ar(sig, 0.1, 0.08) * 0.15
    ]) * pile;
    sig = sig + pileDelay;

    // Stereo scatter
    sig = ~stereoSpread.(sig, wind.linlin(0, 1, 0.2, 0.8), rustle.linlin(0, 1, 0.3, 0.8));

    // MANDATORY output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_moss_root_leaf_fall loaded".postln;
