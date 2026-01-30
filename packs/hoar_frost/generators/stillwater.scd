// hoar_frost/stillwater — Lightweight end-stage generator
// stillwater: Frozen lake surface - deep slow pad
SynthDef(\forge_hoar_frost_stillwater, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var depth, ice, movement, sub, clarity;

    depth = p[0].linlin(0, 1, 0.5, 2);  // P1: Sub octave depth
    ice = p[1].linlin(0, 1, 0, 0.5);  // P2: Icy overtone
    movement = p[2].linlin(0, 1, 0.01, 0.2);  // P3: Slow drift rate
    sub = p[3].linlin(0, 1, 0, 0.8);  // P4: Sub level
    clarity = p[4].linlin(0, 1, 0.1, 0.9);  // P5: Waveform clarity

    freq = In.kr(freqBus);

    // DSP: Deep pad with slow modulation
    sig = VarSaw.ar(freq, 0, LFNoise1.kr(movement).range(0.3, 0.7)) * clarity;
    sig = sig + (SinOsc.ar(freq) * (1 - clarity));
    sig = sig + (SinOsc.ar(freq / depth) * sub * 0.5);
    sig = sig + (SinOsc.ar(freq * 3) * ice * LFNoise1.kr(movement * 2).range(0, 1) * 0.2);

    // Slow stereo movement
    sig = Pan2.ar(sig, SinOsc.kr(movement * 0.5).range(-0.3, 0.3));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_hoar_frost_stillwater loaded".postln;
