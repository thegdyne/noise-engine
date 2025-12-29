SynthDef(\forge_avebury_wish, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var intent, sacred, ancient, spirit, ritual;
    var harmonics, spiritMod, ritualMod, baseAmp;

    // Theme params
    intent = In.kr(customBus0);
    sacred = In.kr(customBus1);
    ancient = In.kr(customBus2);
    spirit = In.kr(customBus3);
    ritual = In.kr(customBus4);

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

    // Spirit shimmer modulation
    spiritMod = LFNoise2.kr(2 + (spirit * 6)).range(0.85, 1.0);

    // Ritual pulse - slow breath-like
    ritualMod = SinOsc.kr(ritual.linexp(0, 1, 0.05, 0.3)).range(0.7, 1.0);

    // Base amplitude
    baseAmp = 0.2;

    // Harmonic series - sacred overtones
    // Fundamental and low harmonics (ancient power)
    harmonics = SinOsc.ar(freq, 0, baseAmp * (1 + (ancient * 0.5)));
    harmonics = harmonics + SinOsc.ar(freq * 2, 0, baseAmp * 0.7);
    harmonics = harmonics + SinOsc.ar(freq * 3, 0, baseAmp * 0.5);

    // Mid harmonics (sacred resonance)
    harmonics = harmonics + SinOsc.ar(freq * 4, 0, baseAmp * 0.35 * (0.3 + (sacred * 0.7)));
    harmonics = harmonics + SinOsc.ar(freq * 5, 0, baseAmp * 0.3 * (0.3 + (sacred * 0.7)));
    harmonics = harmonics + SinOsc.ar(freq * 6, 0, baseAmp * 0.25 * (0.2 + (sacred * 0.8)));

    // High harmonics (intent brightness)
    harmonics = harmonics + SinOsc.ar(freq * 7, 0, baseAmp * 0.2 * intent * sacred);
    harmonics = harmonics + SinOsc.ar(freq * 8, 0, baseAmp * 0.15 * intent * sacred);
    harmonics = harmonics + SinOsc.ar(freq * 9, 0, baseAmp * 0.12 * intent * sacred);
    harmonics = harmonics + SinOsc.ar(freq * 10, 0, baseAmp * 0.1 * intent * sacred);

    // Sub harmonic for grounding
    harmonics = harmonics + SinOsc.ar(freq * 0.5, 0, baseAmp * 0.4 * ancient);

    // Apply modulations
    sig = harmonics * spiritMod * ritualMod;

    // Subtle air/breath texture
    sig = sig + (HPF.ar(PinkNoise.ar(0.02), 3000) * spirit);

    // Continuous bed
    sig = sig + PinkNoise.ar(0.03);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_avebury_wish loaded".postln;
