// drowned_temple/vault — Lightweight end-stage generator
// vault: Vast stone chamber resonance
SynthDef(\forge_drowned_temple_vault, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var size, stone, echo, darkness, age;

    size = p[0].linlin(0, 1, 0.3, 0.9);  // P1: Chamber size
    stone = p[1].linlin(0, 1, 0.3, 0.9);  // P2: Stone resonance (boosted)
    echo = p[2].linlin(0, 1, 0.2, 0.7);  // P3: Echo density
    darkness = p[3].linlin(0, 1, 400, 2500);  // P4: Damping darkness (brighter)
    age = p[4].linlin(0, 1, 0.2, 0.6);  // P5: Ancient dust

    freq = In.kr(freqBus);

    // DSP: Base drone - pitched to freq (boosted)
    sig = SinOsc.ar(freq * [0.5, 1, 1.002]) * stone * 0.5;
    sig = Splay.ar(sig, 0.5);

    // Chamber reverb via comb (boosted input)
    sig = sig + CombL.ar(sig * 0.3, 0.3, size * 0.12 + 0.03, size * 3);

    // Sparse echo reflections (boosted)
    sig = sig + (Ringz.ar(Dust.ar(echo * 5) * 0.2, freq * [1, 1.5, 2], size * 1.5) * echo * 0.5);

    // Darkness filter
    sig = LPF.ar(sig, darkness);

    // Ancient dust texture (boosted)
    sig = sig + (LPF.ar(PinkNoise.ar(age * 0.5), 800));

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_drowned_temple_vault loaded".postln;
