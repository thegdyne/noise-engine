// vapor_station/sodium — Lightweight end-stage generator
// sodium: Warm sodium lamp buzz and flicker
SynthDef(\forge_vapor_station_sodium, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var hum, warmth, flicker, ballast, glow;

    hum = p[0].linlin(0, 1, 0.3, 1);  // P1: 60Hz hum level
    warmth = p[1].linlin(0, 1, 0.2, 0.8);  // P2: Warm harmonics
    flicker = p[2].linlin(0, 1, 0, 0.3);  // P3: Flicker amount
    ballast = p[3].linlin(0, 1, 0, 0.5);  // P4: Ballast whine
    glow = p[4].linlin(0, 1, 0.1, 0.6);  // P5: Warm glow pad

    freq = In.kr(freqBus);

    // DSP: 60Hz hum with harmonics
    sig = SinOsc.ar(60 * [1, 2, 3, 4]) * [1, 0.5, 0.25, 0.12] * hum;
    sig = sig.sum;

    // Warm harmonics - pitched to freq
    sig = sig + (SinOsc.ar(freq * [1, 2, 3]) * [1, 0.4, 0.2] * warmth * 0.3).sum;

    // Flicker modulation
    sig = sig * (1 - (LFNoise2.kr(8) * flicker));

    // Ballast whine - high pitched
    sig = sig + (SinOsc.ar(120 * LFNoise1.kr(0.2).range(30, 35)) * ballast * 0.15);

    // Warm glow pad
    sig = sig + (LPF.ar(Saw.ar(freq * [0.5, 0.501]), 500) * glow * 0.3);

    sig = sig * 0.3;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_vapor_station_sodium loaded".postln;
