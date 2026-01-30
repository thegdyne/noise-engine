// drowned_temple/pool — Lightweight end-stage generator
// pool: Flooded temple floor
SynthDef(\forge_drowned_temple_pool, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var ripple, depth, drip, reflect, still;

    ripple = p[0].linlin(0, 1, 0.1, 1);  // P1: Ripple intensity
    depth = p[1].linlin(0, 1, 0.3, 1);  // P2: Water depth
    drip = p[2].linlin(0, 1, 1, 10);  // P3: Drip rate
    reflect = p[3].linlin(0, 1, 0.1, 0.6);  // P4: Surface reflection
    still = p[4].linlin(0, 1, 0.2, 0.7);  // P5: Still water tone

    freq = In.kr(freqBus);

    // DSP: Still water - filtered sine cluster
    sig = SinOsc.ar(freq * [0.5, 1, 2.01] * LFNoise1.kr(0.1).range(0.99, 1.01)) * still * 0.2;
    sig = Splay.ar(sig, 0.5);

    // Ripple modulation
    sig = sig * (1 + (SinOsc.kr(ripple * 2).range(0, 0.3)));

    // Drip impacts - stereo array
    sig = sig + (Ringz.ar(Dust.ar(drip) * 0.25, freq * [4, 6], 0.08 * depth) * reflect);

    // Deep water presence
    sig = sig + (SinOsc.ar(freq * 0.25) * depth * 0.2);

    // Surface shimmer
    sig = sig + (BPF.ar(PinkNoise.ar(reflect * 0.2), freq * 8, 0.2) * LFNoise1.kr(0.5).range(0.3, 1));

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_drowned_temple_pool loaded".postln;
