// kaiju_beats/kaiju — Lightweight end-stage generator
SynthDef(\forge_kaiju_beats_kaiju, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var throat, roar, breath, vowel, size;
    var source, formants, f1, f2, f3, breathNoise;

    throat = p[0];  // P1: Throat size - formant spacing
    roar = p[1];  // P2: Roar intensity - distortion
    breath = p[2];  // P3: Breath noise mix
    vowel = p[3];  // P4: Vowel morph (A-O-U)
    size = p[4];  // P5: Monster size - pitch shift

    freq = In.kr(freqBus);
    ampVal = 0.2;

    // Source - pulse with size scaling
    freq = freq * (1 - (size * 0.5));
    source = Pulse.ar(freq, 0.3 + (LFNoise1.kr(2) * 0.1));
    source = source + (Saw.ar(freq * 0.999) * 0.5);

    // Add growl modulation
    source = source * (1 + (LFNoise2.kr(3 + (roar * 8)) * roar * 0.5));

    // Formant frequencies - monster vowels
    f1 = LinXFade2.kr(800, 400, vowel * 2 - 1) * (1 - (throat * 0.3));
    f2 = LinXFade2.kr(1200, 800, vowel * 2 - 1) * (1 - (throat * 0.3));
    f3 = LinXFade2.kr(2500, 2200, vowel * 2 - 1) * (1 - (throat * 0.3));

    // Formant filters with gain boost
    formants = BPF.ar(source, f1, 0.1) * 4;
    formants = formants + (BPF.ar(source, f2, 0.12) * 3);
    formants = formants + (BPF.ar(source, f3, 0.15) * 2);

    // Breath noise
    breathNoise = BPF.ar(PinkNoise.ar(1), f1 * 1.5, 0.2) * breath * 0.4;

    // Mix and soft clip for roar
    sig = formants + breathNoise;
    sig = (sig * (1 + (roar * 3))).tanh;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_kaiju_beats_kaiju loaded".postln;
