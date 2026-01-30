// backyard/paddle — Lightweight end-stage generator
SynthDef(\forge_backyard_paddle, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var splash, depth, ripple, kick, sun;
    var splashGrain, waterBody, rippleWave, kickSplash, sunShimmer;
    var grainTrig, grainDur;

    splash = p[0];
    depth = p[1];
    ripple = p[2];
    kick = p[3];
    sun = p[4];

    freq = In.kr(freqBus);

    // Splash grains - bursts of filtered noise
    grainTrig = Dust.ar(splash.linexp(0, 1, 2, 20));
    grainDur = LFNoise1.kr(5).range(0.01, 0.08);
    splashGrain = WhiteNoise.ar(1) * Decay2.ar(grainTrig, 0.002, grainDur);
    splashGrain = BPF.ar(splashGrain, freq.linlin(20, 2000, 800, 4000) * LFNoise0.kr(10).range(0.8, 1.5), 0.5);
    splashGrain = splashGrain * splash * 0.4;

    // Water body - continuous filtered noise representing pool
    waterBody = PinkNoise.ar(0.3) + BrownNoise.ar(0.2);
    waterBody = LPF.ar(waterBody, depth.linexp(0, 1, 200, 800));
    waterBody = waterBody * (0.3 + (depth * 0.4));

    // Ripple waves - modulated sine clusters
    rippleWave = Mix.fill(4, { |i|
        var ripFreq = freq * (1 + (i * 0.1)) * LFNoise1.kr(ripple.linlin(0, 1, 0.2, 2)).range(0.95, 1.05);
        SinOsc.ar(ripFreq, 0, 0.08 * (1 / (i + 1)))
    });
    rippleWave = rippleWave * LFTri.kr(ripple.linlin(0, 1, 0.3, 2)).range(0.3, 1);
    rippleWave = rippleWave * ripple * 0.3;

    // Kick splash - bigger impacts
    kickSplash = Dust.ar(kick.linexp(0, 1, 0.3, 3));
    kickSplash = WhiteNoise.ar(1) * Decay2.ar(kickSplash, 0.005, 0.15);
    kickSplash = HPF.ar(kickSplash, 500);
    kickSplash = kickSplash * kick * 0.5;

    // Sun shimmer - high frequency sparkle
    sunShimmer = Mix.fill(3, { |i|
        SinOsc.ar(
            freq * (8 + i) * LFNoise2.kr(2).range(0.98, 1.02),
            0,
            0.03 * sun * LFNoise1.kr(1 + (i * 0.5)).range(0, 1)
        )
    });

    // Mix all components
    sig = splashGrain + waterBody + rippleWave + kickSplash + sunShimmer;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_backyard_paddle loaded".postln;
