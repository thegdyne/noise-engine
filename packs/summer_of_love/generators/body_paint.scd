SynthDef(\forge_summer_of_love_body_paint, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                                filterTypeBus, envEnabledBus, envSourceBus=0,
                                                clockRateBus, clockTrigBus,
                                                midiTrigBus=0, slotIndex=0,
                                                customBus0, customBus1, customBus2, customBus3, customBus4,
                                                portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var blue, orange, vivid, morph, shine;
    var blueTone, orangeTone, morphLfo, index, shineOsc;

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
    blue = In.kr(customBus0);      // Cool FM ratio (higher, metallic)
    orange = In.kr(customBus1);    // Warm FM ratio (lower, woody)
    vivid = In.kr(customBus2);     // Modulation intensity
    morph = In.kr(customBus3);     // Morphing speed
    shine = In.kr(customBus4);     // High harmonic shimmer

    // FM modulation index based on vivid
    index = vivid.linexp(0, 1, 0.5, 8);

    // Blue tone - cool, metallic (ratio ~3.5:1)
    blueTone = SinOsc.ar(
        freq,
        SinOsc.ar(freq * 3.51) * index * blue * 2pi
    );

    // Orange tone - warm, woody (ratio ~1.5:1 with sub-harmonics)
    orangeTone = SinOsc.ar(
        freq,
        SinOsc.ar(freq * 1.498) * index * orange * 2pi
    ) + (SinOsc.ar(freq * 0.5) * orange * 0.3);

    // Morph LFO - crossfade between blue and orange
    morphLfo = SinOsc.kr(morph.linexp(0, 1, 0.05, 2)).range(0, 1);
    sig = XFade2.ar(orangeTone, blueTone, morphLfo.linlin(0, 1, -1, 1));

    // Shine - add high harmonic content
    shineOsc = SinOsc.ar(freq * 5) * SinOsc.ar(freq * 7) * shine * 0.15;
    sig = sig + shineOsc;

    // Gentle stereo spread
    sig = ~stereoSpread.(sig, 0.2, 0.4);

    // Apply standard processing chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_summer_of_love_body_paint loaded".postln;
