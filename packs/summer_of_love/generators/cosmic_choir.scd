// summer_of_love/cosmic_choir — Lightweight end-stage generator
SynthDef(\forge_summer_of_love_cosmic_choir, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var vowel, transcend, unity, breath, ascend;
    var source, formant1, formant2, formant3, breathNoise, shimmer;
    var f1Freqs, f2Freqs, f3Freqs, f1, f2, f3, ascendMod;
    var voices, detuneAmts;

    freq = In.kr(freqBus);

    vowel = p[0];  // Vowel morph
    transcend = p[1];  // Ethereal shimmer
    unity = p[2];  // Voice count
    breath = p[3];  // Breathy air
    ascend = p[4];  // Upward drift

    // Slow ascending pitch drift
    ascendMod = LFNoise1.kr(0.05) * ascend * 0.03;

    // Formant frequencies for OO, AH, EE vowels
    // F1 (first formant) - vowel height
    f1Freqs = [300, 700, 400];  // oo, ah, ee
    // F2 (second formant) - vowel frontness
    f2Freqs = [870, 1200, 2300];
    // F3 (third formant) - voice character
    f3Freqs = [2250, 2600, 3000];

    // Interpolate formants based on vowel position
    f1 = Select.kr(vowel * 2, f1Freqs);
    f2 = Select.kr(vowel * 2, f2Freqs);
    f3 = Select.kr(vowel * 2, f3Freqs);

    // Detune amounts for choir voices
    detuneAmts = [-0.02, -0.01, 0, 0.01, 0.02];

    // Create multiple detuned voice sources
    voices = detuneAmts.collect({ |det, i|
        var voiceFreq = freq * (1 + det + ascendMod + (LFNoise1.kr(0.1 + (i * 0.02)) * 0.005));
        var voiceSrc, pan;

        // Rich source - saw + pulse for vocal-like harmonics
        voiceSrc = Saw.ar(voiceFreq) + (Pulse.ar(voiceFreq, 0.3) * 0.5);

        pan = (i - 2) / 2 * unity;
        Pan2.ar(voiceSrc, pan) * unity.linlin(0, 1, 0.5, 1)
    }).sum;

    source = voices * 0.3;

    // Apply formant filters
    formant1 = BPF.ar(source, f1, 0.1) * 1.5;
    formant2 = BPF.ar(source, f2, 0.12) * 1.0;
    formant3 = BPF.ar(source, f3, 0.15) * 0.5;

    sig = formant1 + formant2 + formant3;

    // Breath - filtered noise through same formants
    breathNoise = PinkNoise.ar(breath * 0.15);
    breathNoise = BPF.ar(breathNoise, f1, 0.2) + BPF.ar(breathNoise, f2, 0.25);
    sig = sig + breathNoise;

    // Transcendent shimmer - high pitched harmonics
    shimmer = SinOsc.ar(freq * 3) * SinOsc.ar(freq * 5) * transcend * 0.1;
    shimmer = shimmer + (SinOsc.ar(freq * 7) * LFNoise1.kr(0.5).range(0, 1) * transcend * 0.05);
    sig = sig + shimmer;

    // Wide stereo for cosmic feel
    sig = ~stereoSpread.(sig, 0.1, 0.7);

    // Apply standard processing chain

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_summer_of_love_cosmic_choir loaded".postln;
