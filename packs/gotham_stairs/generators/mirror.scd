SynthDef(\forge_gotham_stairs_mirror, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var fracture, selfParam, distort, shatter, double;
    var partials, shards, doubled;

    // Theme params
    fracture = In.kr(customBus0);
    selfParam = In.kr(customBus1);
    distort = In.kr(customBus2);
    shatter = In.kr(customBus3);
    double = In.kr(customBus4);

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

    // Additive partials - the "self" reflection
    partials = Mix.fill(12, { |i|
        var partial = i + 1;
        var partialFreq = freq * partial;
        var detune = fracture * LFNoise1.kr(0.5 + (i * 0.1)).range(0.98, 1.02);
        var amplitude = selfParam / (partial + (distort * 2));
        SinOsc.ar(partialFreq * detune, 0, amplitude * 0.15)
    });

    // Shattered fragments - irregular high partials
    shards = Mix.fill(6, { |i|
        var shardFreq = freq * (7 + i + (shatter * LFNoise0.kr(2).range(0, 3)));
        var shardAmp = shatter * 0.05 / (i + 1);
        SinOsc.ar(shardFreq * LFNoise2.kr(1).range(0.99, 1.01), 0, shardAmp)
    });

    // Doubled self - slightly offset reflection
    doubled = Mix.fill(8, { |i|
        var partial = i + 1;
        var partialFreq = freq * partial * 1.002;
        var amplitude = double * selfParam / (partial + 1);
        SinOsc.ar(partialFreq, pi * 0.25, amplitude * 0.1)
    });

    sig = partials + (shards * shatter) + (doubled * double);

    // Distortion waveshaping on reflection
    sig = sig + (sig.tanh * distort * 0.3);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_gotham_stairs_mirror loaded".postln;
