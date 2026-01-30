// ekrano/flyby — Lightweight end-stage generator
SynthDef(\forge_ekrano_flyby, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var doppler, speed, distance, engine, width;
    var dopplerMod, fmIndex, carrier, modulator, phaseMod, panPos, distFilter;

    freq = In.kr(freqBus);

    doppler = p[0].linexp(0, 1, 0.05, 2);
    speed = p[1].linlin(0, 1, 0.1, 0.5);
    distance = p[2];
    engine = p[3].linlin(0, 1, 1, 8);
    width = p[4];

    // Doppler pitch modulation - slow sweep up and down
    dopplerMod = LFTri.kr(doppler).range(1 - speed, 1 + speed);

    // Phase modulation FM
    fmIndex = engine;
    modulator = SinOsc.ar(freq * dopplerMod * 2) * fmIndex * freq;
    carrier = SinOsc.ar(freq * dopplerMod + modulator);

    // Add harmonics for engine richness
    phaseMod = carrier + (SinOsc.ar(freq * dopplerMod * 0.5 + (modulator * 0.5)) * 0.4);
    phaseMod = phaseMod + (SinOsc.ar(freq * dopplerMod * 3 + (modulator * 0.3)) * 0.2);

    sig = phaseMod * 0.4;

    // Distance filter - closer = brighter
    distFilter = distance.linexp(0, 1, 800, 12000);
    sig = LPF.ar(sig, distFilter);

    // Stereo panning following doppler
    panPos = LFTri.kr(doppler).range(width.neg, width);
    sig = Pan2.ar(sig, panPos);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ekrano_flyby loaded".postln;
