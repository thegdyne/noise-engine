// Cascade - Water flowing and falling over moss-covered rocks
// Multiple filtered noise streams at different frequencies

SynthDef(\forge_drangarnir_cascade, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var flow, drop, stone, spatial, shimmer;
    var waterStreams, dropSplash, stoneTexture, shimmerTone;

    // Standard bus reads
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
    flow = In.kr(customBus0);
    drop = In.kr(customBus1);
    stone = In.kr(customBus2);
    spatial = In.kr(customBus3);
    shimmer = In.kr(customBus4);

    // Multiple water streams at different frequencies
    waterStreams = Mix.fill(6, { |i|
        var streamFreq = freq * (0.5 + (i * 0.3)) * LFNoise1.kr(0.5).range(0.95, 1.05);
        var streamFlow = flow * (1 - (i * 0.1));
        var noise = WhiteNoise.ar(streamFlow * 0.15);
        BPF.ar(noise, streamFreq, stone.linlin(0, 1, 0.3, 0.1));
    });

    // Drop splashes - impact at bottom of falls
    dropSplash = Dust2.ar(drop.linlin(0, 1, 50, 500)) * 0.2;
    dropSplash = Ringz.ar(dropSplash, freq * 2, drop.linlin(0, 1, 0.02, 0.1));
    dropSplash = HPF.ar(dropSplash, 1000);

    // Stone texture - the surface affecting flow
    stoneTexture = GrayNoise.ar((1 - stone) * 0.1);
    stoneTexture = BPF.ar(stoneTexture, freq * 0.75, 0.5);

    // Shimmer - light on water droplets
    shimmerTone = Mix.fill(4, { |i|
        var shimFreq = freq * (4 + i) * LFNoise2.kr(2).range(0.98, 1.02);
        SinOsc.ar(shimFreq, 0, shimmer * 0.03 / (i + 1));
    });
    shimmerTone = shimmerTone * LFNoise2.kr(5).range(0.3, 1);

    // Combine
    sig = waterStreams + dropSplash + stoneTexture + shimmerTone;

    // Add subtle low-end body for water mass
    sig = sig + LPF.ar(PinkNoise.ar(flow * 0.2), freq * 0.5);

    // Wide stereo spread for spatial cascade
    sig = ~stereoSpread.(sig, 0.5, spatial);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_drangarnir_cascade loaded".postln;
