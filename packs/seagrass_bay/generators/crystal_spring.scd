SynthDef(\forge_seagrass_bay_crystal_spring, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var clarity, shimmer, flow, cold, light;
    var fundamental, partials, flowMod, lightSparkle;

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
    clarity = In.kr(customBus0);    // Purity
    shimmer = In.kr(customBus1);    // Sparkle
    flow = In.kr(customBus2);       // Water movement
    cold = In.kr(customBus3);       // Brightness
    light = In.kr(customBus4);      // Sunlight sparkle

    // Flow modulation - gentle pitch/amplitude ripple
    flowMod = SinOsc.kr(flow.linexp(0, 1, 0.3, 2)) * flow * 0.005;
    freq = freq * (1 + flowMod);

    // Fundamental - pure sine for clarity
    fundamental = SinOsc.ar(freq) * clarity.linlin(0, 1, 0.4, 0.7);

    // Bell-like partials (slightly inharmonic for realism)
    partials = Mix.fill(6, { |i|
        var ratio, partial, partialAmp;
        ratio = [1, 2.0, 3.01, 4.02, 5.04, 6.08][i];
        partialAmp = (1 / (i + 1).squared) * shimmer;
        // Cold shifts partials brighter
        partial = SinOsc.ar(freq * ratio * (1 + (cold * 0.02 * i)));
        partial * partialAmp;
    });

    sig = fundamental + (partials * 0.6);

    // Light sparkle - high frequency shimmer
    lightSparkle = Ringz.ar(
        Dust.ar(light.linexp(0, 1, 2, 20)),
        freq * [4, 5, 6].choose,
        0.1
    ) * light * 0.15;
    sig = sig + lightSparkle;

    // Cold = high shelf boost
    sig = BHiShelf.ar(sig, 3000, 1, cold * 6);

    // Shimmer stereo spread
    sig = ~stereoSpread.(sig, shimmer.linlin(0, 1, 0.2, 0.8), 0.4);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_seagrass_bay_crystal_spring loaded".postln;
