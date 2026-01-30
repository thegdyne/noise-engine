// hoar_frost/frozen_breath — Lightweight end-stage generator
// frozen_breath: Cold air exhalation - breathy formants
SynthDef(\forge_hoar_frost_frozen_breath, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var airiness, formant1, formant2, breathRate, tonal;

    airiness = p[0].linlin(0, 1, 0.3, 1);
    formant1 = p[1].linexp(0, 1, 400, 1800);
    formant2 = p[2].linexp(0, 1, 1000, 3500);
    breathRate = p[3].linlin(0, 1, 0.1, 0.8);
    tonal = p[4].linlin(0, 1, 0.1, 0.6);

    freq = In.kr(freqBus);

    // DSP: Breath noise through formant filters - boosted gain
    sig = PinkNoise.ar(airiness) + (WhiteNoise.ar(airiness * 0.3));

    // Formant resonances with higher gain
    sig = Resonz.ar(sig, formant1 * LFNoise1.kr(breathRate).range(0.92, 1.08), 0.15) * 6;
    sig = sig + (Resonz.ar(PinkNoise.ar(airiness * 0.5), formant2 * LFNoise1.kr(breathRate * 0.7).range(0.92, 1.08), 0.2) * 4);

    // Add tonal undertone
    sig = sig + (SinOsc.ar(freq * [1, 2.01]) * tonal * LFNoise1.kr(breathRate).range(0.4, 1) * 0.4);

    // Breath amplitude modulation
    sig = sig * LFNoise1.kr(breathRate * 2).range(0.6, 1);

    sig = sig * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_hoar_frost_frozen_breath loaded".postln;
