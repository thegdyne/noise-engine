// oldwinch/barrow — Lightweight end-stage generator
SynthDef(\forge_oldwinch_barrow, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var depthParam, spirit, earth, bronze, timeParam;
    var drone, spiritShimmer, bronzePartials, timeMod, earthFilter;

    depthParam = p[0];
    spirit = p[1];
    earth = p[2];
    bronze = p[3];
    timeParam = p[4];

    freq = In.kr(freqBus);

    // Deep time modulation - very slow
    timeMod = LFNoise2.kr(timeParam.linexp(0, 1, 0.02, 0.1)).range(0.98, 1.02);

    // Core spectral drone - layered sines
    drone = SinOsc.ar(freq * timeMod, 0, 0.25);
    drone = drone + SinOsc.ar(freq * 0.5 * timeMod, 0, 0.3 * depthParam);
    drone = drone + SinOsc.ar(freq * 0.25 * timeMod, 0, 0.25 * depthParam);
    drone = drone + SinOsc.ar(freq * 2 * timeMod, 0, 0.15 * (1 - depthParam));
    drone = drone + SinOsc.ar(freq * 1.5 * timeMod, 0, 0.12);

    // Spirit shimmer - detuned high partials
    spiritShimmer = SinOsc.ar(freq * 3 * LFNoise2.kr(0.5).range(0.99, 1.01), 0, 0.1 * spirit);
    spiritShimmer = spiritShimmer + SinOsc.ar(freq * 4 * LFNoise2.kr(0.4).range(0.99, 1.01), 0, 0.08 * spirit);
    spiritShimmer = spiritShimmer + SinOsc.ar(freq * 5 * LFNoise2.kr(0.3).range(0.99, 1.01), 0, 0.06 * spirit);
    spiritShimmer = spiritShimmer * LFNoise2.kr(1 + (spirit * 3)).range(0.5, 1.0);

    // Bronze Age metallic partials
    bronzePartials = SinOsc.ar(freq * 2.3, 0, 0.1 * bronze);
    bronzePartials = bronzePartials + SinOsc.ar(freq * 3.7, 0, 0.08 * bronze);
    bronzePartials = bronzePartials + SinOsc.ar(freq * 5.1, 0, 0.06 * bronze);
    bronzePartials = bronzePartials * LFNoise2.kr(0.2).range(0.7, 1.0);

    sig = drone + spiritShimmer + bronzePartials;

    // Earth damping - low pass based on earth covering
    earthFilter = earth.linexp(0, 1, 5000, 800);
    sig = LPF.ar(sig, earthFilter);

    // Underground resonance
    sig = sig + LPF.ar(BrownNoise.ar(0.1 * depthParam), 150);

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.06), 300);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_oldwinch_barrow loaded".postln;
