// rlyeh/rlyeh — Lightweight end-stage generator
// rlyeh: The sunken city - impossible architecture emerging
SynthDef(\forge_rlyeh_rlyeh, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var angles, depth, stone, echo, wrongness;

    angles = p[0].linlin(0, 1, 0, 0.1);  // P1: Wrong angles detune
    depth = p[1].linlin(0, 1, 0.5, 2);  // P2: Submerged depth
    stone = p[2].linlin(0, 1, 0.1, 0.8);  // P3: Ancient stone resonance
    echo = p[3].linlin(0, 1, 0.1, 0.7);  // P4: Cyclopean echo
    wrongness = p[4].linlin(0, 1, 0, 0.5);  // P5: Geometric wrongness

    freq = In.kr(freqBus);

    // DSP: Non-Euclidean harmonics
    sig = Saw.ar(freq * [1, 1 + angles, 1 + (angles * 1.7), 1 + (angles * 2.3)]);
    sig = sig * [1, 0.7, 0.5, 0.3];
    sig = Splay.ar(sig, wrongness);

    // Submerged filtering
    sig = LPF.ar(sig, freq * depth * 4);

    // Stone resonance
    sig = sig + (Ringz.ar(sig * 0.1, freq * [2, 3.01, 4.02], stone) * stone * 0.3);

    // Cyclopean echo
    sig = sig + (CombL.ar(sig, 0.5, LFNoise1.kr(0.1).range(0.15, 0.25), echo * 3) * echo * 0.4);

    sig = sig * 0.2;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_rlyeh_rlyeh loaded".postln;
