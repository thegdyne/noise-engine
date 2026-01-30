// gotham_stairs/mirror — Lightweight end-stage generator
SynthDef(\forge_gotham_stairs_mirror, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var fracture, selfParam, distort, shatter, double;
    var partials, shards, doubled;

    fracture = p[0];
    selfParam = p[1];
    distort = p[2];
    shatter = p[3];
    double = p[4];

    freq = In.kr(freqBus);

    // Additive partials - the "self" reflection
    partials = Mix.fill(12, { |i|
        var partial = i + 1;
        var partialFreq = freq * partial;
        var detune = fracture * LFNoise1.kr(0.5 + (i * 0.1)).range(0.98, 1.02);
        var amplitude = selfParam / (partial + (distort * 2));
        SinOsc.ar(partialFreq * detune, 0, amplitude * 0.15)
    });

    // Shattered fragments - irregular high partials
    shards = Mix.fill(6, { |i|
        var shardFreq = freq * (7 + i + (shatter * LFNoise0.kr(2).range(0, 3)));
        var shardAmp = shatter * 0.05 / (i + 1);
        SinOsc.ar(shardFreq * LFNoise2.kr(1).range(0.99, 1.01), 0, shardAmp)
    });

    // Doubled self - slightly offset reflection
    doubled = Mix.fill(8, { |i|
        var partial = i + 1;
        var partialFreq = freq * partial * 1.002;
        var amplitude = double * selfParam / (partial + 1);
        SinOsc.ar(partialFreq, pi * 0.25, amplitude * 0.1)
    });

    sig = partials + (shards * shatter) + (doubled * double);

    // Distortion waveshaping on reflection
    sig = sig + (sig.tanh * distort * 0.3);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_gotham_stairs_mirror loaded".postln;
