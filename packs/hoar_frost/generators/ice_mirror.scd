// hoar_frost/ice_mirror — Lightweight end-stage generator
// ice_mirror: Reflections on frozen water - comb/delay shimmer
SynthDef(\forge_hoar_frost_ice_mirror, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var feedback, shimmer, spread, combTune, glisten;

    feedback = p[0].linlin(0, 1, 0.3, 0.85);  // P1: Comb feedback
    shimmer = p[1].linlin(0, 1, 0.1, 2);  // P2: Shimmer rate
    spread = p[2].linlin(0, 1, 0.001, 0.01);  // P3: Stereo spread delay
    combTune = p[3].linlin(0, 1, 0.5, 2);  // P4: Comb tuning ratio
    glisten = p[4].linlin(0, 1, 0, 0.5);  // P5: High frequency sparkle

    freq = In.kr(freqBus);

    // DSP: Resonant comb with shimmer modulation
    sig = Saw.ar(freq * [1, 1.003]) * 0.3;

    // Comb filters tuned to frequency
    sig = CombL.ar(sig,
        0.1,
        (freq * combTune).reciprocal * (1 + (SinOsc.kr(shimmer).range(0, 0.02))),
        feedback * 2
    );

    // Add high glisten
    sig = sig + (Ringz.ar(
        Dust.ar(shimmer * 5) * 0.1,
        freq * [4, 5, 6],
        0.1
    ).sum * glisten);

    // Stereo delay spread
    sig = [
        DelayL.ar(sig[0], 0.02, spread),
        DelayL.ar(sig[1], 0.02, spread * 1.3)
    ];

    sig = sig * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_hoar_frost_ice_mirror loaded".postln;
