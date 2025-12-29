SynthDef(\forge_oldwinch_ritual, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var sacred, chant, gather, season, power;
    var harmonics, seasonMod, gatherSpread, baseAmp;

    // Theme params
    sacred = In.kr(customBus0);
    chant = In.kr(customBus1);
    gather = In.kr(customBus2);
    season = In.kr(customBus3);
    power = In.kr(customBus4);

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

    // Seasonal modulation - very slow
    seasonMod = SinOsc.kr(season.linexp(0, 1, 0.03, 0.15)).range(0.9, 1.0);

    // Gathering chorus spread
    gatherSpread = gather * 0.008;

    // Base amplitude
    baseAmp = 0.18;

    // Core harmonic series - sacred chant
    harmonics = SinOsc.ar(freq, 0, baseAmp * (1 + (power * 0.5)));
    harmonics = harmonics + SinOsc.ar(freq * (1 + gatherSpread), 0.3, baseAmp * 0.4 * gather);
    harmonics = harmonics + SinOsc.ar(freq * (1 - gatherSpread), 0.6, baseAmp * 0.4 * gather);

    // Sub harmonics (earth power)
    harmonics = harmonics + SinOsc.ar(freq * 0.5, 0, baseAmp * 0.6 * power);
    harmonics = harmonics + SinOsc.ar(freq * 0.25, 0, baseAmp * 0.4 * power);

    // Upper harmonics (chant brightness)
    harmonics = harmonics + SinOsc.ar(freq * 2, 0, baseAmp * 0.5 * (0.3 + (chant * 0.7)));
    harmonics = harmonics + SinOsc.ar(freq * 3, 0, baseAmp * 0.35 * (0.2 + (chant * 0.8)));
    harmonics = harmonics + SinOsc.ar(freq * 4, 0, baseAmp * 0.25 * chant * sacred);
    harmonics = harmonics + SinOsc.ar(freq * 5, 0, baseAmp * 0.18 * chant * sacred);
    harmonics = harmonics + SinOsc.ar(freq * 6, 0, baseAmp * 0.12 * chant * sacred);

    // Sacred shimmer
    harmonics = harmonics + SinOsc.ar(freq * 7, 0, baseAmp * 0.08 * sacred);
    harmonics = harmonics + SinOsc.ar(freq * 8, 0, baseAmp * 0.06 * sacred);

    // Apply seasonal modulation
    sig = harmonics * seasonMod;

    // Breath texture
    sig = sig + (HPF.ar(PinkNoise.ar(0.03), 2000) * sacred * LFNoise2.kr(2).range(0, 1));

    // Continuous bed
    sig = sig + PinkNoise.ar(0.04);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_oldwinch_ritual loaded".postln;
