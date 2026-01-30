// mirrors/focus — Lightweight end-stage generator
SynthDef(\forge_mirrors_focus, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var converge, focal, gather, distance, clarity;
    var partials, convergeMod, focalIntensity, baseAmp;

    converge = p[0];
    focal = p[1];
    gather = p[2];
    distance = p[3];
    clarity = p[4];

    freq = In.kr(freqBus);

    // Convergence modulation - waves aligning
    convergeMod = LFNoise2.kr(0.2 + (converge * 0.3)).range(0.98, 1.02);

    // Focal intensity - pulsing at focus point
    focalIntensity = SinOsc.kr(focal.linexp(0, 1, 0.1, 0.5)).range(0.8, 1.0);

    // Base amplitude
    baseAmp = 0.18;

    // Additive partials - gathering waves from distance
    partials = SinOsc.ar(freq * convergeMod, 0, baseAmp * focalIntensity);
    partials = partials + SinOsc.ar(freq * 2 * convergeMod, 0, baseAmp * 0.6 * (0.3 + (gather * 0.7)));
    partials = partials + SinOsc.ar(freq * 3 * convergeMod, 0, baseAmp * 0.4 * (0.2 + (gather * 0.8)));
    partials = partials + SinOsc.ar(freq * 4 * convergeMod, 0, baseAmp * 0.3 * gather * distance);
    partials = partials + SinOsc.ar(freq * 5 * convergeMod, 0, baseAmp * 0.2 * gather * distance);
    partials = partials + SinOsc.ar(freq * 6 * convergeMod, 0, baseAmp * 0.15 * gather * distance);

    // Sub harmonic - distant low rumble
    partials = partials + SinOsc.ar(freq * 0.5 * convergeMod, 0, baseAmp * 0.5 * (1 - distance));

    // Slightly detuned copies for width
    partials = partials + SinOsc.ar(freq * 1.002 * convergeMod, 0.3, baseAmp * 0.3 * converge);
    partials = partials + SinOsc.ar(freq * 0.998 * convergeMod, 0.6, baseAmp * 0.3 * converge);

    sig = partials * focalIntensity;

    // Distance affects brightness
    sig = LPF.ar(sig, distance.linexp(0, 1, 2000, 8000));

    // Clarity - noise floor
    sig = sig + (PinkNoise.ar(0.08) * (1 - clarity));

    // Continuous bed
    sig = sig + PinkNoise.ar(0.05);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mirrors_focus loaded".postln;
