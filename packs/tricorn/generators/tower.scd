SynthDef(\forge_tricorn_tower, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                   filterTypeBus, envEnabledBus, envSourceBus=0,
                                   clockRateBus, clockTrigBus,
                                   midiTrigBus=0, slotIndex=0,
                                   customBus0, customBus1, customBus2, customBus3, customBus4,
                                   portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var height, steps, angular, wind, shadow;
    var harmonics, windMod, baseAmp;

    // Theme params
    height = In.kr(customBus0);
    steps = In.kr(customBus1);
    angular = In.kr(customBus2);
    wind = In.kr(customBus3);
    shadow = In.kr(customBus4);

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

    // Wind modulation
    windMod = LFNoise2.kr(0.5 + (wind * 2)).range(0.7, 1.0);

    // Base amplitude scaling - boosted for presence
    baseAmp = 0.25;

    // Build harmonic series - 12 harmonics with height-based rolloff
    // Core harmonics always present, height adds upper extension
    harmonics = SinOsc.ar(freq * 1, 0, baseAmp * (1 + shadow));
    harmonics = harmonics + SinOsc.ar(freq * 2, 0, baseAmp * 0.7 * (1 - (angular * 0.3)));
    harmonics = harmonics + SinOsc.ar(freq * 3, 0, baseAmp * 0.6 * (1 + (angular * 0.5)));
    harmonics = harmonics + SinOsc.ar(freq * 4, 0, baseAmp * 0.4 * (0.3 + (height * 0.7)));
    harmonics = harmonics + SinOsc.ar(freq * 5, 0, baseAmp * 0.35 * (1 + (angular * 0.6)) * (0.3 + (height * 0.7)));
    harmonics = harmonics + SinOsc.ar(freq * 6, 0, baseAmp * 0.25 * (0.2 + (height * 0.8)));
    harmonics = harmonics + SinOsc.ar(freq * 7, 0, baseAmp * 0.22 * (1 + (angular * 0.7)) * (0.2 + (height * 0.8)));
    harmonics = harmonics + SinOsc.ar(freq * 8, 0, baseAmp * 0.15 * (0.1 + (height * 0.9)));
    harmonics = harmonics + SinOsc.ar(freq * 9, 0, baseAmp * 0.12 * (1 + (angular * 0.4)) * (0.1 + (height * 0.9)));
    harmonics = harmonics + SinOsc.ar(freq * 10, 0, baseAmp * 0.1 * height);
    harmonics = harmonics + SinOsc.ar(freq * 11, 0, baseAmp * 0.08 * (1 + angular) * height);
    harmonics = harmonics + SinOsc.ar(freq * 12, 0, baseAmp * 0.06 * height);

    // Steps: add slight inharmonicity
    harmonics = harmonics + SinOsc.ar(freq * (1 + (steps * 0.02)), 0, baseAmp * 0.2 * (0.3 + (steps * 0.7)));
    harmonics = harmonics + SinOsc.ar(freq * (3 + (steps * 0.05)), 0, baseAmp * 0.15 * (0.3 + (steps * 0.7)));

    sig = harmonics * windMod;

    // Continuous noise bed for air - always present
    sig = sig + PinkNoise.ar(0.05);
    sig = sig + (PinkNoise.ar(0.03) * wind);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_tricorn_tower loaded".postln;
