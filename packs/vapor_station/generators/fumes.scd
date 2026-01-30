// vapor_station/fumes — Lightweight end-stage generator
// fumes: Chemical vapor shimmer and haze
SynthDef(\forge_vapor_station_fumes, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var volatile, iridescent, toxic, haze, nausea;

    volatile = p[0].linlin(0, 1, 0.5, 4);  // P1: FM modulation depth
    iridescent = p[1].linlin(0, 1, 0.2, 1);  // P2: Shimmering overtones
    toxic = p[2].linlin(0, 1, 0, 0.5);  // P3: Harsh dissonance
    haze = p[3].linlin(0, 1, 0.1, 0.6);  // P4: Soft blur
    nausea = p[4].linlin(0, 1, 0.1, 1);  // P5: Slow undulation

    freq = In.kr(freqBus);

    // DSP: FM shimmer
    sig = PMOsc.ar(
        freq,
        freq * LFNoise1.kr(nausea).range(1.99, 2.01),
        volatile * SinOsc.kr(nausea * 0.3).range(0.5, 1),
        0
    );

    // Iridescent overtones
    sig = sig + (SinOsc.ar(freq * [3, 5.01, 7.02, 9.03]) * iridescent * [0.2, 0.15, 0.1, 0.05]);
    sig = Splay.ar(sig, 0.6);

    // Toxic dissonance
    sig = sig + (SinOsc.ar(freq * [1.06, 1.94]) * toxic * 0.2);

    // Haze blur - filtered copy
    sig = sig + (LPF.ar(sig, 500) * haze);

    sig = sig * 0.3;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_vapor_station_fumes loaded".postln;
