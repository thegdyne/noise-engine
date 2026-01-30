// sgwd/cascade — Lightweight end-stage generator
// cascade: Main curtain of falling water
SynthDef(\forge_sgwd_cascade, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var width, weight, height, foam, veil;

    width = p[0].linlin(0, 1, 0.3, 1);  // P1: Curtain width
    weight = p[1].linlin(0, 1, 200, 800);  // P2: Water weight (LPF)
    height = p[2].linlin(0, 1, 0.2, 0.8);  // P3: Drop height (pitch)
    foam = p[3].linlin(0, 1, 0.1, 0.5);  // P4: White foam
    veil = p[4].linlin(0, 1, 0.2, 0.7);  // P5: Veil texture

    freq = In.kr(freqBus);

    // DSP: Layered falling water
    // Main cascade body - filtered noise
    sig = BrownNoise.ar(width) + PinkNoise.ar(width * 0.5);
    sig = LPF.ar(sig, weight);
    sig = sig * LFNoise1.kr(3).range(0.8, 1);  // Gentle variation

    // Foam layer - bright hiss
    sig = sig + (WhiteNoise.ar(foam) * HPF.ar(WhiteNoise.ar(0.3), 3000));

    // Height creates pitch content
    sig = sig + (Resonz.ar(PinkNoise.ar(height * 0.4), freq * [1, 1.5, 2], 0.15).sum);

    // Veil texture - delicate high frequencies
    sig = sig + (BPF.ar(WhiteNoise.ar(veil * 0.3), 4000 * LFNoise1.kr(0.5).range(0.8, 1.2), 0.3));

    sig = sig * 0.35;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_sgwd_cascade loaded".postln;
