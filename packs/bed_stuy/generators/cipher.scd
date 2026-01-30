// bed_stuy/cipher — Lightweight end-stage generator
// cipher: MC vocal presence - formant drone
SynthDef(\forge_bed_stuy_cipher, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var voice, flow, breath, crowd, hype;

    voice = p[0].linlin(0, 1, 0.3, 1);  // P1: Voice presence
    flow = p[1].linlin(0, 1, 0.05, 0.3);  // P2: Flow modulation
    breath = p[2].linlin(0, 1, 0.1, 0.5);  // P3: Breath texture
    crowd = p[3].linlin(0, 1, 0, 0.4);  // P4: Crowd murmur
    hype = p[4].linlin(0, 1, 0, 0.5);  // P5: Hype energy

    freq = In.kr(freqBus);

    // DSP: Vocal formant drone
    sig = Formant.ar(
        freq * LFNoise1.kr(flow).range(0.98, 1.02),
        freq * 3 * LFNoise1.kr(flow * 0.7).range(0.9, 1.1),
        freq * 6
    ) * voice * 0.4;

    // Breath - aspirant noise
    sig = sig + (BPF.ar(PinkNoise.ar(breath), freq * 4, 0.3) * LFNoise1.kr(0.3).range(0.5, 1) * 0.5);

    // Crowd murmur - filtered noise
    sig = sig + (BPF.ar(PinkNoise.ar(crowd), 500 * LFNoise0.kr(0.5).range(0.7, 1.4), 0.3));

    // Hype energy - bright bursts
    sig = sig + (Ringz.ar(Dust.ar(hype * 8) * 0.15, freq * [4, 6], 0.05) * hype);

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_bed_stuy_cipher loaded".postln;
