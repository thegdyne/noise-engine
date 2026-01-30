// seagrass_bay/crystal_spring — Lightweight end-stage generator
SynthDef(\forge_seagrass_bay_crystal_spring, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var clarity, shimmer, flow, cold, light;
    var fundamental, partials, flowMod, lightSparkle;
    var panRate, panWidth;

    freq = In.kr(freqBus);

    clarity = p[0];  // Purity
    shimmer = p[1];  // Sparkle
    flow = p[2];  // Water movement
    cold = p[3];  // Brightness
    light = p[4];  // Sunlight sparkle

    // Flow modulation - gentle pitch/amplitude ripple
    flowMod = SinOsc.kr(flow.linexp(0, 1, 0.3, 2)) * flow * 0.005;
    freq = freq * (1 + flowMod);

    // Fundamental - pure sine for clarity
    fundamental = SinOsc.ar(freq) * clarity.linlin(0, 1, 0.4, 0.7);

    // Bell-like partials (slightly inharmonic for realism)
    partials = Mix.fill(6, { |i|
        var ratio, partial, partialAmp;
        ratio = [1, 2.0, 3.01, 4.02, 5.04, 6.08][i];
        partialAmp = (1 / (i + 1).squared) * shimmer;
        // Cold shifts partials brighter
        partial = SinOsc.ar(freq * ratio * (1 + (cold * 0.02 * i)));
        partial * partialAmp;
    });

    sig = fundamental + (partials * 0.6);

    // Light sparkle - high frequency shimmer
    lightSparkle = Ringz.ar(
        Dust.ar(light.linexp(0, 1, 2, 20)),
        freq * [4, 5, 6].choose,
        0.1
    ) * light * 0.15;
    sig = sig + lightSparkle;

    // Cold = high shelf boost
    sig = BHiShelf.ar(sig, 3000, 1, cold * 6);
    // Shimmer stereo spread
    panRate  = shimmer.linexp(0, 1, 0.05, 0.8);
    panWidth = shimmer.linlin(0, 1, 0.2, 0.8);
    sig = Pan2.ar(Mix(sig), SinOsc.kr(panRate).range(panWidth.neg, panWidth), 0.4);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_seagrass_bay_crystal_spring loaded".postln;
