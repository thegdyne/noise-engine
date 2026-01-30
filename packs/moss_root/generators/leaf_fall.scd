// moss_root/leaf_fall — Lightweight end-stage generator
SynthDef(\forge_moss_root_leaf_fall, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var rustle, wind, wet, pile, curl;
    var leaves, crunch, pileDelay;

    freq = In.kr(freqBus);

    rustle = p[0];
    wind = p[1];
    wet = p[2];
    pile = p[3];
    curl = p[4];

    // Multiple rustling layers
    leaves = Mix(Array.fill(4, { |i|
        var rate = wind.linexp(0, 1, 2, 20) * (1 + (i * 0.3));
        var noiseFreq = freq * (2 + i);
        var ampMod = LFNoise2.kr(rate).range(0.3, 1);
        var layer = BPF.ar(
            WhiteNoise.ar,
            noiseFreq.clip(100, 10000),
            curl.linexp(0, 1, 0.5, 0.1)
        ) * ampMod;
        layer * (rustle * 0.5)
    }));

    // Crunch: high-frequency crackle
    crunch = HPF.ar(
        Dust2.ar(wind.linexp(0, 1, 50, 500) * rustle) * 0.8,
        curl.linexp(0, 1, 3000, 6000)
    ) * curl;

    sig = leaves + crunch;

    // Wetness: dampen high frequencies
    sig = LPF.ar(sig, wet.linexp(0, 1, 12000, 2000));
    sig = sig * wet.linlin(0, 1, 1, 0.6); // Wet leaves are quieter

    // Pile: multiple short delays for depth
    pileDelay = Mix([
        DelayL.ar(sig, 0.1, 0.02) * 0.3,
        DelayL.ar(sig, 0.1, 0.05) * 0.2,
        DelayL.ar(sig, 0.1, 0.08) * 0.15
    ]) * pile;
    sig = (sig + pileDelay) * 8;  // Boost quiet texture

    // Stereo scatter
    sig = Pan2.ar(Mix(sig), SinOsc.kr(wind.linexp(0, 1, 0.2, 0.8).max(0.001)) * rustle.linlin(0, 1, 0.3, 0.8));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_moss_root_leaf_fall loaded".postln;
