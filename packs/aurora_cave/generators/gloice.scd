// aurora_cave/gloice — Lightweight end-stage generator
SynthDef(\forge_aurora_cave_gloice, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var density, glow, grain, scatter, frost;
    var grainTrig, grainDur, grainPitch, grains, frostLayer;
    var buf;

    freq = In.kr(freqBus);

    density = p[0];
    glow = p[1];
    grain = p[2];
    scatter = p[3];
    frost = p[4];

    // Grain triggering
    grainTrig = Dust.ar(density.linexp(0, 1, 5, 100));
    grainDur = grain.linexp(0, 1, 0.01, 0.15);

    // Pitch variation for scatter effect
    grainPitch = freq * (1 + (TRand.ar(-1, 1, grainTrig) * scatter * 0.5));

    // Granular synthesis using sinusoidal grains (no buffer needed)
    grains = Array.fill(6, { |i|
        var trig = Dust.ar(density.linexp(0, 1, 2, 40));
        var pitchVar = 1 + (TRand.ar(-1, 1, trig) * scatter * 0.3);
        var harmonic = [1, 2, 3, 4, 5, 6][i];
        var grainEnv = EnvGen.ar(
            Env.perc(0.001, grain.linexp(0, 1, 0.02, 0.2)),
            trig
        );
        SinOsc.ar(freq * harmonic * pitchVar) * grainEnv * (1 / harmonic.sqrt)
    }).sum;

    // Add higher sparkle layer
    grains = grains + Array.fill(4, { |i|
        var trig = Dust.ar(density.linexp(0, 1, 3, 60) * glow);
        var pitchVar = 1 + (TRand.ar(-0.5, 0.5, trig) * scatter);
        var sparkleFreq = freq * [5, 7, 9, 11][i] * pitchVar;
        var grainEnv = EnvGen.ar(
            Env.perc(0.0005, grain.linexp(0, 1, 0.01, 0.08)),
            trig
        );
        SinOsc.ar(sparkleFreq) * grainEnv * 0.15 * glow
    }).sum;

    // Frost texture - high frequency haze
    frostLayer = WhiteNoise.ar * frost * 0.05;
    frostLayer = BPF.ar(frostLayer, freq * 8, 0.5);
    frostLayer = frostLayer * LFNoise2.kr(2).range(0.3, 1);

    sig = (grains * 0.25) + frostLayer;

    // Glow saturation
    sig = (sig * (1 + glow)).tanh * (1 / (1 + (glow * 0.5)));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_aurora_cave_gloice loaded".postln;
