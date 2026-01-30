// avebury/roots — Lightweight end-stage generator
SynthDef(\forge_avebury_roots, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var spread, depth, earth, pulse, tangle;
    var exciter, comb1, comb2, comb3, comb4, delayTime, feedback, pulseMod;

    spread = p[0];
    depth = p[1];
    earth = p[2];
    pulse = p[3];
    tangle = p[4];

    freq = In.kr(freqBus);

    // Slow organic pulse modulation
    pulseMod = LFTri.kr(pulse.linexp(0, 1, 0.05, 0.5)).range(0.7, 1.0);

    // Exciter - earth rumble + organic texture
    exciter = BrownNoise.ar(0.3) + LPF.ar(PinkNoise.ar(0.2), 400);
    exciter = exciter * pulseMod;

    // Base delay time from frequency
    delayTime = freq.reciprocal;
    feedback = earth.linlin(0, 1, 0.7, 0.4);

    // Root network - multiple comb delays with tangle detuning
    comb1 = CombL.ar(exciter, 0.2, delayTime.clip(0.002, 0.2), 0.8 + (spread * 1.5), 0.4);
    comb2 = CombL.ar(exciter, 0.2, (delayTime * (1 + (tangle * 0.05))).clip(0.002, 0.2), 0.6 + spread, 0.3);
    comb3 = CombL.ar(exciter, 0.2, (delayTime * 2 * (1 - (tangle * 0.03))).clip(0.002, 0.2), 0.5 + (spread * 0.5), 0.25);
    comb4 = CombL.ar(exciter, 0.2, (delayTime * 0.5).clip(0.002, 0.2), 0.7 + spread, 0.35 * depth);

    sig = (comb1 + comb2 + comb3 + comb4) * 0.35;

    // Depth emphasis - sub layer
    sig = sig + (SinOsc.ar(freq * 0.5, 0, 0.2 * depth) * pulseMod);
    sig = sig + LPF.ar(BrownNoise.ar(0.15 * depth), 150);

    // Earth filtering - low pass for underground feel
    sig = LPF.ar(sig, depth.linexp(0, 1, 2000, 600));

    // Add allpass for spread
    sig = AllpassC.ar(sig, 0.3, spread.linlin(0, 1, 0.05, 0.2), spread * 2);

    // Continuous bed
    sig = sig + LPF.ar(BrownNoise.ar(0.08), 200);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_avebury_roots loaded".postln;
