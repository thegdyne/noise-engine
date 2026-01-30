// summer_of_love/crowd_murmur — Lightweight end-stage generator
SynthDef(\forge_summer_of_love_crowd_murmur, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var density, distance, mood, movement, space;
    var noise, formants, formantFreqs, formantMods, distanceFilter;

    freq = In.kr(freqBus);

    density = p[0];  // Voice density
    distance = p[1];  // Near/far (affects brightness)
    mood = p[2];  // Relaxed to excited
    movement = p[3];  // Formant modulation
    space = p[4];  // Stereo width

    // Base noise source - pink for more natural voice-like spectrum
    noise = PinkNoise.ar(1) + (BrownNoise.ar(0.3) * (1 - mood));

    // Formant frequencies - speech-like bands shifted by mood and freq
    formantFreqs = [
        freq * 1.0,   // F1 - low vowel formant
        freq * 2.5,   // F2 - mid vowel formant
        freq * 4.0,   // F3 - high formant
        freq * 6.0    // F4 - presence
    ];

    // Movement modulation on formants
    formantMods = formantFreqs.collect({ |f, i|
        var modRate = 0.1 + (movement * 0.5) + (i * 0.05);
        var modDepth = movement * 0.15;
        f * (1 + (LFNoise1.kr(modRate) * modDepth))
    });

    // Create formant bands with resonant bandpass filters
    formants = formantMods.collect({ |f, i|
        var bw = f * 0.3;  // Bandwidth
        var gain = [1.0, 0.7, 0.4, 0.2][i] * density;
        BPF.ar(noise, f.clip(100, 8000), 0.2) * gain
    }).sum;

    // Add some impulse-like energy for consonants
    formants = formants + (Dust.ar(density.linlin(0, 1, 5, 30)) * BPF.ar(WhiteNoise.ar(0.1), 2500, 0.5) * density);

    sig = formants;

    // Distance filter - further = darker
    distanceFilter = distance.linexp(0, 1, 8000, 1500);
    sig = LPF.ar(sig, distanceFilter);

    // Add subtle room character for distance
    sig = sig + (CombL.ar(sig, 0.1, distance.linlin(0, 1, 0.01, 0.05), distance * 0.5) * distance * 0.3);

    // Stereo spread for space
    sig = ~stereoSpread.(sig, 0.15 + (movement * 0.2), space * 0.8);

    // Apply standard processing chain
    sig = sig * 4;  // gain boost

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_summer_of_love_crowd_murmur loaded".postln;
