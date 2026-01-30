// icarus/glory — Lightweight end-stage generator
// Glory -- blinding beauty of the sun up close
// Role: accent

SynthDef(\forge_icarus_glory, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var blind, awe, rays, divine, moment;
    var light, harmonics, shimmer, frozen, numRays;

    freq = In.kr(freqBus);

    blind = p[0].linlin(0, 1, 0.3, 1.0);  // Overall brightness
    awe = p[1].linlin(0, 1, 0.5, 6);  // FM index (harmonic richness)
    rays = p[2];  // Ray count (discrete)
    divine = p[3].linlin(0, 1, 0.0, 0.5);  // Upper shimmer
    moment = p[4].linlin(0, 1, 1, 0.1);  // Time dilation (mod speed)

    // Number of light rays (2-8)
    numRays = rays.linlin(0, 1, 2, 8).round;

    // Core blinding light - FM synthesis
    light = SinOsc.ar(freq, SinOsc.ar(freq * 2.01, 0, awe));

    // Harmonic rays - additive partials
    harmonics = SinOsc.ar(freq * 2, 0, 0.3);
    harmonics = harmonics + SinOsc.ar(freq * 3, 0, 0.2 * (numRays > 2).asInteger.asInteger);
    harmonics = harmonics + SinOsc.ar(freq * 4, 0, 0.15 * (numRays > 3).asInteger.asInteger);
    harmonics = harmonics + SinOsc.ar(freq * 5, 0, 0.12 * (numRays > 4).asInteger.asInteger);
    harmonics = harmonics + SinOsc.ar(freq * 6, 0, 0.1 * (numRays > 5).asInteger.asInteger);
    harmonics = harmonics + SinOsc.ar(freq * 7, 0, 0.08 * (numRays > 6).asInteger.asInteger);
    harmonics = harmonics + SinOsc.ar(freq * 8, 0, 0.06 * (numRays > 7).asInteger.asInteger);

    // Divine shimmer - detuned high partials
    shimmer = SinOsc.ar(freq * 4 * LFNoise2.kr(moment, 0.02, 1), 0, divine);
    shimmer = shimmer + SinOsc.ar(freq * 6 * LFNoise2.kr(moment * 1.1, 0.02, 1), 0, divine * 0.7);

    // Combine in blinding glory
    sig = (light + harmonics + shimmer) * blind;

    // Wide stereo spread - enveloping light
    sig = Pan2.ar(Mix(sig), SinOsc.kr((0.3 * moment).max(0.001)).range(-0.6, 0.6));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_icarus_glory loaded".postln;
