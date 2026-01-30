// vapor_station/nozzle — Lightweight end-stage generator
// nozzle: Hissing fuel spray and drip
SynthDef(\forge_vapor_station_nozzle, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var spray, drip, splatter, flow, vapors;

    spray = p[0].linlin(0, 1, 0.2, 1);  // P1: Spray intensity
    drip = p[1].linlin(0, 1, 1, 15);  // P2: Drip rate
    splatter = p[2].linlin(0, 1, 0, 0.6);  // P3: Splatter amount
    flow = p[3].linlin(0, 1, 0.1, 0.7);  // P4: Flow noise
    vapors = p[4].linlin(0, 1, 0, 0.5);  // P5: Vapor shimmer

    freq = In.kr(freqBus);

    // DSP: Spray hiss - filtered noise
    sig = BPF.ar(WhiteNoise.ar(spray), 4000 * LFNoise1.kr(0.5).range(0.7, 1.3), 0.5) * 2;

    // Drip impacts
    sig = sig + (Ringz.ar(Dust.ar(drip) * 0.3, freq * [3, 4.5], 0.03) * splatter);

    // Flow noise - continuous
    sig = sig + (LPF.ar(PinkNoise.ar(flow), freq * 4) * 0.5);

    // Vapor shimmer - high ethereal
    sig = sig + (SinOsc.ar(freq * [6, 8.01, 10.02]) * vapors * LFNoise1.kr(0.3).range(0.2, 1) * 0.15);

    sig = sig * 0.35;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_vapor_station_nozzle loaded".postln;
