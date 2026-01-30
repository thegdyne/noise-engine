// q121/shroud — Lightweight end-stage generator
SynthDef(\forge_q121_shroud, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var holes, metal, wind, size, feed;
    var exciter, combBank, decayTime, ratios;

    holes = p[0];
    metal = p[1];
    wind = p[2];
    size = p[3];
    feed = p[4];

    freq = In.kr(freqBus);

    // Excitation - wind through perforations
    exciter = BPF.ar(WhiteNoise.ar(1), freq * 8, holes.linlin(0, 1, 0.8, 0.2)) * wind;
    exciter = exciter + (PinkNoise.ar(0.3) * wind * 0.5);
    exciter = exciter + (Dust.ar(holes.linexp(0, 1, 10, 200)) * 0.2);

    // Decay time based on metal parameter
    decayTime = metal.linexp(0, 1, 0.05, 0.8);

    // Comb bank simulating circular hole array resonances
    // Using fixed ratios for hole spacing harmonics
    ratios = [1, 1.12, 1.33, 1.5, 1.78, 2.0, 2.37];
    combBank = Mix.fill(7, { |i|
        var ratio = ratios[i];
        var delayFreq = freq * ratio * size.linexp(0, 1, 0.5, 2);
        var delayTime = delayFreq.reciprocal.clip(0.0001, 0.05);
        CombL.ar(exciter, 0.05, delayTime, decayTime * (1 - (i * 0.08))) * (1 - (i * 0.1))
    });

    // Feedback path for metallic ring
    sig = combBank + (LocalIn.ar(1) * feed * 0.4);
    LocalOut.ar(DelayN.ar(HPF.ar(sig, 200), 0.01, 0.008) * 0.3);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_q121_shroud loaded".postln;
