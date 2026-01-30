// drowned_temple/hymn — Lightweight end-stage generator
// hymn: Ancient prayer echoing through ruins
SynthDef(\forge_drowned_temple_hymn, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var voice, choir, sacred, ancient, fade;

    voice = p[0].linlin(0, 1, 0.3, 1);  // P1: Voice level
    choir = p[1].linlin(0, 1, 1, 4);  // P2: Choir voices
    sacred = p[2].linlin(0, 1, 0.1, 0.6);  // P3: Sacred harmonics
    ancient = p[3].linlin(0, 1, 0.05, 0.2);  // P4: Ancient waver
    fade = p[4].linlin(0, 1, 0.2, 0.7);  // P5: Fade into distance

    freq = In.kr(freqBus);

    // DSP: Formant voice drone
    sig = Formant.ar(
        freq * LFNoise1.kr(ancient).range(0.98, 1.02),
        freq * 2 * LFNoise1.kr(ancient * 0.7).range(0.95, 1.05),
        freq * 4
    ) * voice;

    // Choir - detuned copies
    sig = sig + (Formant.ar(
        freq * 1.003 * LFNoise1.kr(ancient).range(0.98, 1.02),
        freq * 2.5,
        freq * 5
    ) * voice * (choir / 4));

    // Sacred harmonics
    sig = sig + (SinOsc.ar(freq * [1.5, 2, 3]) * sacred * 0.15);

    // Distance blur
    sig = LPF.ar(sig, 2000 * (1 - (fade * 0.5)));

    sig = sig * 0.3;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_drowned_temple_hymn loaded".postln;
