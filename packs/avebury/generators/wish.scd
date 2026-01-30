// avebury/wish — Lightweight end-stage generator
SynthDef(\forge_avebury_wish, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var intent, sacred, ancient, spirit, ritual;
    var harmonics, spiritMod, ritualMod, baseAmp;

    intent = p[0];
    sacred = p[1];
    ancient = p[2];
    spirit = p[3];
    ritual = p[4];

    freq = In.kr(freqBus);

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

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_avebury_wish loaded".postln;
