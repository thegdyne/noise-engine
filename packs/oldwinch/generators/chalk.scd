SynthDef(\forge_oldwinch_chalk, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                   filterTypeBus, envEnabledBus, envSourceBus=0,
                                   clockRateBus, clockTrigBus,
                                   midiTrigBus=0, slotIndex=0,
                                   customBus0, customBus1, customBus2, customBus3, customBus4,
                                   portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var grass, down, white, soil, openAmt;
    var grassRustle, downWind, chalkTone, soilLow, space;

    // Theme params
    grass = In.kr(customBus0);
    down = In.kr(customBus1);
    white = In.kr(customBus2);
    soil = In.kr(customBus3);
    openAmt = In.kr(customBus4);

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

    // Grass rustle - high frequency filtered noise
    grassRustle = HPF.ar(WhiteNoise.ar(0.35), 2000 + (white * 3000));
    grassRustle = grassRustle * LFNoise2.kr(3 + (grass * 8)).range(0.4, 1.0);
    grassRustle = grassRustle * (0.3 + (grass * 0.7));

    // Downland wind
    downWind = BPF.ar(PinkNoise.ar(0.5), freq * down.linlin(0, 1, 1, 3), 0.4) * 2;
    downWind = downWind * LFNoise2.kr(0.3 + (down * 0.5)).range(0.5, 1.0);
    downWind = downWind * (0.4 + (down * 0.6));

    // Chalk tone - bright filtered
    chalkTone = BPF.ar(PinkNoise.ar(0.4) + WhiteNoise.ar(0.2 * white), freq * 2, 0.3) * 3;
    chalkTone = chalkTone * white;

    // Soil low frequency
    soilLow = LPF.ar(BrownNoise.ar(0.4), 200 + (freq * 0.3));
    soilLow = soilLow * (0.3 + (soil * 0.7));

    sig = grassRustle + downWind + chalkTone + soilLow;

    // Open landscape reverb
    space = sig;
    space = AllpassC.ar(space, 0.3, openAmt.linlin(0, 1, 0.05, 0.2), openAmt * 2.5);
    space = AllpassC.ar(space, 0.3, openAmt.linlin(0, 1, 0.08, 0.25), openAmt * 2);

    sig = (sig * (1 - (openAmt * 0.4))) + (space * openAmt * 0.5);

    // Pitched wind tone
    sig = sig + BPF.ar(PinkNoise.ar(0.15), freq, 0.3) * 2;

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.1), 350);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_oldwinch_chalk loaded".postln;
