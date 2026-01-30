// moss_root/moss_pad — Lightweight end-stage generator
SynthDef(\forge_moss_root_moss_pad, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var thickness, dampness, growth, scatter, sun;
    var voices, fuzz, bright, panPos;

    freq = In.kr(freqBus);

    thickness = p[0];
    dampness = p[1];
    growth = p[2];
    scatter = p[3];
    sun = p[4];

    // Multiple soft voices with subtle detuning
    voices = Mix(Array.fill(6, { |i|
        var detune = (i - 2.5) * 0.003 * thickness;
        var ampMod = LFNoise1.kr(growth.linexp(0, 1, 0.05, 0.4) + (i * 0.02));
        var voiceAmp = thickness.linlin(0, 1, 0.3, 1) / 6;
        SinOsc.ar(freq * (1 + detune)) * voiceAmp * ampMod.range(0.5, 1)
    }));

    // Add soft triangles for fullness
    voices = voices + (LFTri.ar(freq * 0.5) * 0.2 * thickness);

    // Fuzzy moss texture: filtered noise
    fuzz = LPF.ar(
        PinkNoise.ar(0.08 * thickness),
        freq * 4 * dampness.linexp(0, 1, 0.5, 2)
    );

    // Sunlight: bright harmonics via gentle FM
    bright = SinOsc.ar(
        freq * 2,
        SinOsc.ar(freq * 3) * sun.linlin(0, 1, 0, 1.5)
    ) * sun * 0.15;

    sig = voices + fuzz + bright;

    // Internal dampness filter (low-pass moss feeling)
    sig = LPF.ar(sig, dampness.linexp(0, 1, 8000, 1500));

    // Scatter: randomized stereo positioning
    panPos = LFNoise1.kr(scatter.linexp(0, 1, 0.1, 0.5)).range(scatter.neg * 0.8, scatter * 0.8);
    sig = Pan2.ar(sig, panPos);

    // MANDATORY output chain
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_moss_root_moss_pad loaded".postln;
