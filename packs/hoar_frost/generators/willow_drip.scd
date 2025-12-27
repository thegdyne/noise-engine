// willow_drip: Ice drops from willow branches - delicate FM bells
SynthDef(\forge_hoar_frost_willow_drip, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var ratio, modDepth, brightness, inharmonic, decay2;

    // Theme params
    ratio = In.kr(customBus0).linlin(0, 1, 1.5, 5);        // P1: FM ratio
    modDepth = In.kr(customBus1).linlin(0, 1, 0.5, 4);     // P2: FM depth
    brightness = In.kr(customBus2).linlin(0, 1, 1, 8);     // P3: Harmonic brightness
    inharmonic = In.kr(customBus3).linlin(0, 1, 0, 0.05);  // P4: Inharmonicity
    decay2 = In.kr(customBus4).linlin(0, 1, 0.3, 2);       // P5: Bell decay

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

    // DSP: FM bell with inharmonic partials
    sig = PMOsc.ar(
        freq * (1 + (inharmonic * LFNoise0.kr(0.5))),
        freq * ratio,
        modDepth * Line.kr(1, 0.1, decay2),
        0
    );

    // Add shimmer partial
    sig = sig + (SinOsc.ar(freq * brightness * (1 + (inharmonic * 2))) * 0.1 * Line.kr(1, 0, decay2 * 0.5));

    sig = sig * 0.3;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_hoar_frost_willow_drip loaded".postln;
