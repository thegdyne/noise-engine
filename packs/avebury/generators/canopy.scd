SynthDef(\forge_avebury_canopy, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                   filterTypeBus, envEnabledBus, envSourceBus=0,
                                   clockRateBus, clockTrigBus,
                                   midiTrigBus=0, slotIndex=0,
                                   customBus0, customBus1, customBus2, customBus3, customBus4,
                                   portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var rustle, breeze, density, height, sway;
    var leaves, wind, rustleMod, breezeMod, layer1, layer2, layer3;

    // Theme params
    rustle = In.kr(customBus0);
    breeze = In.kr(customBus1);
    density = In.kr(customBus2);
    height = In.kr(customBus3);
    sway = In.kr(customBus4);

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

    // Breeze modulation - gusting
    breezeMod = LFNoise2.kr(0.3 + (breeze * 0.8)).range(0.4, 1.0);
    breezeMod = breezeMod * LFNoise2.kr(0.1).range(0.7, 1.0);

    // Rustle modulation - rapid flutter
    rustleMod = LFNoise2.kr(5 + (rustle * 15)).range(0.6, 1.0);

    // High frequency leaf layer - white/pink filtered (boosted)
    layer1 = HPF.ar(WhiteNoise.ar(0.5), height.linexp(0, 1, 1500, 4000));
    layer1 = layer1 * rustleMod * (0.5 + (breezeMod * 0.5));

    // Mid frequency branch movement (boosted, wider Q)
    layer2 = BPF.ar(PinkNoise.ar(0.8), freq * height.linlin(0, 1, 2, 6), 0.8) * 3;
    layer2 = layer2 * (0.5 + (breezeMod * 0.5));

    // Low air movement (boosted)
    layer3 = LPF.ar(BrownNoise.ar(0.5), 500);
    layer3 = layer3 * LFNoise2.kr(0.2).range(0.6, 1.0);

    // Combine layers - always present base levels
    leaves = (layer1 * 0.5) + (layer2 * (0.4 + (density * 0.4))) + (layer3 * 0.5);

    // Wind tone - pitched component
    wind = BPF.ar(PinkNoise.ar(0.4), freq, 0.4) * 3;
    wind = wind * (0.4 + (breezeMod * 0.6));

    sig = leaves + wind;

    // Strong continuous bed
    sig = sig + PinkNoise.ar(0.15);
    sig = sig + LPF.ar(BrownNoise.ar(0.12), 300);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_avebury_canopy loaded".postln;
