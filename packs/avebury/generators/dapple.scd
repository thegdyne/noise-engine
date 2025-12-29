SynthDef(\forge_avebury_dapple, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                   filterTypeBus, envEnabledBus, envSourceBus=0,
                                   clockRateBus, clockTrigBus,
                                   midiTrigBus=0, slotIndex=0,
                                   customBus0, customBus1, customBus2, customBus3, customBus4,
                                   portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var flicker, beam, warmth, scatter, dance;
    var carrier1, carrier2, carrier3, carrier4, amRate, amDepth, danceMod;

    // Theme params
    flicker = In.kr(customBus0);
    beam = In.kr(customBus1);
    warmth = In.kr(customBus2);
    scatter = In.kr(customBus3);
    dance = In.kr(customBus4);

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

    // AM parameters
    amRate = flicker.linexp(0, 1, 0.5, 8);
    amDepth = beam.linlin(0, 1, 0.2, 0.8);

    // Dancing light modulation
    danceMod = LFNoise2.kr(dance.linexp(0, 1, 0.2, 3)).range(0.95, 1.05);

    // Multiple carriers with scatter detuning and AM
    carrier1 = SinOsc.ar(freq * danceMod, 0, 0.3);
    carrier1 = carrier1 * SinOsc.kr(amRate, 0, amDepth, 1 - amDepth);

    carrier2 = SinOsc.ar(freq * (1 + (scatter * 0.008)) * danceMod, 0, 0.25);
    carrier2 = carrier2 * SinOsc.kr(amRate * 1.1, 0.5, amDepth, 1 - amDepth);

    carrier3 = SinOsc.ar(freq * (1 - (scatter * 0.008)) * danceMod, 0, 0.25);
    carrier3 = carrier3 * SinOsc.kr(amRate * 0.9, 1, amDepth, 1 - amDepth);

    carrier4 = SinOsc.ar(freq * 2 * danceMod, 0, 0.15 * warmth);
    carrier4 = carrier4 * SinOsc.kr(amRate * 1.3, 0.3, amDepth * 0.7, 1 - (amDepth * 0.7));

    sig = carrier1 + carrier2 + carrier3 + carrier4;

    // Warmth - add harmonics
    sig = sig + SinOsc.ar(freq * 3, 0, 0.1 * warmth);
    sig = sig + SinOsc.ar(freq * 0.5, 0, 0.15);

    // Subtle noise shimmer
    sig = sig + (HPF.ar(PinkNoise.ar(0.03), 4000) * LFNoise2.kr(amRate).range(0, 1) * dance);

    // Continuous bed
    sig = sig + PinkNoise.ar(0.03);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_avebury_dapple loaded".postln;
