// CITYSCAPE - Wide urban drone, the city breathing
// Family: spectral (additive)
// Role: bed

SynthDef(\forge_barbican_hound_cityscape, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                             filterTypeBus, envEnabledBus, envSourceBus=0,
                                             clockRateBus, clockTrigBus,
                                             midiTrigBus=0, slotIndex=0,
                                             customBus0, customBus1, customBus2, customBus3, customBus4,
                                             portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var sky, steel, stone, air, haze;
    var partials, lowPartials, midPartials, hiPartials, breath;

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

    // Custom params
    sky = In.kr(customBus0);    // High frequency
    steel = In.kr(customBus1); // Metallic
    stone = In.kr(customBus2); // Low harmonics
    air = In.kr(customBus3);   // Breathiness
    haze = In.kr(customBus4);  // Blur

    // Stone - low harmonics (concrete foundation)
    lowPartials = Mix.fill(4, { |i|
        var ratio = i + 1;
        var detune = LFNoise1.kr(0.1) * haze * 0.01;
        SinOsc.ar(freq * ratio * (1 + detune)) * (1 / (ratio + 1)) * stone
    });

    // Steel - metallic mid harmonics (building structure)
    midPartials = Mix.fill(5, { |i|
        var ratio = (i + 3) * 1.5;  // Non-integer for metallic
        var shimmer = LFNoise2.kr(0.2 + (i * 0.1)) * 0.02;
        SinOsc.ar(freq * ratio * (1 + shimmer)) * (1 / (ratio * 2)) * steel
    });

    // Sky - high harmonics
    hiPartials = Mix.fill(4, { |i|
        var ratio = (i + 8);
        var drift = LFNoise1.kr(0.05) * haze * 0.05;
        SinOsc.ar(freq * ratio * (1 + drift)) * (1 / (ratio * 4)) * sky
    });

    // Air - filtered noise breath of the city
    breath = BPF.ar(PinkNoise.ar(1), freq * 4, 0.5) * air * 0.3;
    breath = breath + (HPF.ar(WhiteNoise.ar(1), 4000) * air * 0.1);

    // Combine all layers
    partials = lowPartials + midPartials + hiPartials + breath;

    // Haze blur - subtle chorus/detune
    partials = partials + DelayC.ar(partials, 0.05, LFNoise1.kr(0.2).range(0.01, 0.03) * haze) * haze * 0.5;

    // Wide stereo spread
    sig = Splay.ar([partials, DelayC.ar(partials, 0.1, 0.015)], 0.8);

    // Post-chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_barbican_hound_cityscape loaded".postln;
