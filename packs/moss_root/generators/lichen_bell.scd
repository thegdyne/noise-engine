// moss_root/lichen_bell — Lightweight end-stage generator
SynthDef(\forge_moss_root_lichen_bell, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var stone, ring, crust, age, spot;
    var exciter, modes, crustNoise, spotPartial;
    var modeRatios, modeAmps, ringTime;

    freq = In.kr(freqBus);

    stone = p[0];
    ring = p[1];
    crust = p[2];
    age = p[3];
    spot = p[4];

    // Exciter: stone-like impulse + continuous Dust for drone mode
    exciter = Mix([
        HPF.ar(WhiteNoise.ar, stone.linexp(0, 1, 1000, 5000)),
        Impulse.ar(0) * 0.5 + Dust.ar(3) * 0.3
    ]) * EnvGen.ar(Env.perc(0.001, stone.linexp(0, 1, 0.01, 0.05)));

    // Ring time based on ring parameter
    ringTime = ring.linexp(0, 1, 0.3, 4);

    // Modal ratios - inharmonic for bell-like character, age adds stretch
    modeRatios = [1, 2.32, 3.56, 4.87, 6.23, 7.89] * (1 + (age * 0.1 * Array.series(6, 0, 0.02)));
    modeAmps = [1, 0.6, 0.4, 0.25, 0.15, 0.1];

    // Modal synthesis
    modes = Mix(Array.fill(6, { |i|
        var modeFreq = freq * modeRatios[i];
        var modeDecay = ringTime / (1 + (i * 0.3));
        Ringz.ar(exciter, modeFreq.clip(20, 15000), modeDecay) * modeAmps[i]
    })) * 0.3;

    // Add fundamental sine for body
    modes = modes + (SinOsc.ar(freq) * EnvGen.ar(Env.perc(0.001, ringTime * 0.5)) * 0.2);

    // Continuous resonant bed for drone mode
    modes = modes + (Ringz.ar(Dust.ar(5) * 0.15, freq * [1, 2.32, 3.56], ringTime * 0.5).sum * 0.2);

    sig = modes;

    // Crust: textural noise layer
    crustNoise = BPF.ar(
        GrayNoise.ar,
        freq * 4,
        0.3
    ) * EnvGen.ar(Env.perc(0.01, crust.linexp(0, 1, 0.05, 0.3))) * crust * 0.2;
    sig = sig + crustNoise;

    // Spot: emphasized bright partial
    spotPartial = SinOsc.ar(freq * 5.5) * EnvGen.ar(Env.perc(0.001, ringTime * 0.3)) * spot * 0.15;
    sig = sig + spotPartial;

    // Continuous subtle shimmer
    sig = sig + (SinOsc.ar(freq * [1, 2.32]) * 0.05).sum;

    // Subtle stereo from age-induced detuning
    sig = Pan2.ar(Mix(sig), SinOsc.kr(0.15) * age.linlin(0, 1, 0.2, 0.5));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_moss_root_lichen_bell loaded".postln;
