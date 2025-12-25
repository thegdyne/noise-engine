// Fuzzy Legs - Granular noise texture like the spider's hairy legs
// Multiple layers of filtered noise grains with organic movement

SynthDef(\forge_maratus_fuzzy_legs, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var fuzziness, hair, crawl, legs, spider;
    var grainDensity, layers, crawlLFO, chaosLFO;

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
    fuzziness = In.kr(customBus0);  // Grain density
    hair = In.kr(customBus1);  // High frequency
    crawl = In.kr(customBus2);  // Movement rate
    legs = In.kr(customBus3);  // Layer count
    spider = In.kr(customBus4);  // Chaos

    // Crawl modulation
    crawlLFO = LFNoise1.kr(crawl.linexp(0, 1, 0.2, 5));

    // Chaos modulation
    chaosLFO = LFNoise2.kr(spider.linexp(0, 1, 1, 20)) * spider;

    // Grain density from fuzziness
    grainDensity = fuzziness.linexp(0, 1, 20, 500);

    // Multiple texture layers (like multiple legs)
    layers = 4.collect({ |i|
        var layer, layerFreq, dust, filtered;
        var layerMix = (i / 3 * legs);  // Progressive mix based on legs param

        // Each layer at slightly different frequency
        layerFreq = freq * (1 + (i * 0.02) + (crawlLFO * 0.05));

        // Dust impulses for grain triggers
        dust = Dust.ar(grainDensity * (1 + (chaosLFO * 0.5)));

        // Filtered noise grains
        layer = dust * WhiteNoise.ar;

        // Resonant filter at layer frequency
        filtered = BPF.ar(layer, layerFreq.clip(50, 15000), 0.1 + (fuzziness * 0.2));

        // Add hair - high frequency content
        filtered = filtered + (HPF.ar(layer, 3000 + (hair * 5000)) * hair * 0.3);

        filtered * layerMix.clip(0, 1)
    });

    sig = Mix.ar(layers) * 1.5;

    // Add pitched resonance at freq
    sig = sig + (Ringz.ar(Dust.ar(grainDensity * 0.2), freq, 0.1) * 0.3);

    // Spider chaos - random pitch modulation
    sig = sig + (sig * LFNoise0.kr(30) * spider * 0.3);

    // Wider stereo for fuzzy spread
    sig = ~stereoSpread.(sig, 0.8, 0.6);

    // Mandatory output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_maratus_fuzzy_legs loaded".postln;
