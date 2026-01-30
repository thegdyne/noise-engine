// mirrors/dish — Lightweight end-stage generator
SynthDef(\forge_mirrors_dish, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var curveAmt, concrete, diameter, windAmt, age;
    var exciter, comb1, comb2, comb3, comb4, delayTime, feedback;

    curveAmt = p[0];
    concrete = p[1];
    diameter = p[2];
    windAmt = p[3];
    age = p[4];

    freq = In.kr(freqBus);

    // Wind exciter across parabolic surface
    exciter = PinkNoise.ar(0.3) + BrownNoise.ar(0.2);
    exciter = exciter * LFNoise2.kr(0.4 + (windAmt * 0.8)).range(0.4, 1.0);
    exciter = exciter * (0.4 + (windAmt * 0.6));

    // Base delay time from frequency and diameter
    delayTime = freq.reciprocal * (0.8 + (diameter * 0.4));
    feedback = concrete.linlin(0, 1, 0.4, 0.8);

    // Parabolic curve creates multiple reflection paths
    comb1 = CombL.ar(exciter, 0.2, delayTime.clip(0.002, 0.2), 0.5 + (concrete * 1.0), 0.35);
    comb2 = CombL.ar(exciter, 0.2, (delayTime * (1 + (curveAmt * 0.3))).clip(0.002, 0.2), 0.4 + (concrete * 0.8), 0.3);
    comb3 = CombL.ar(exciter, 0.2, (delayTime * (1 - (curveAmt * 0.2))).clip(0.002, 0.2), 0.45 + (concrete * 0.7), 0.28);
    comb4 = CombL.ar(exciter, 0.2, (delayTime * 0.5).clip(0.002, 0.2), 0.6 + (concrete * 0.5), 0.25 * diameter);

    sig = (comb1 + comb2 + comb3 + comb4) * 0.35;

    // Focal point resonance
    sig = sig + BPF.ar(sig, freq, 0.1 + (curveAmt * 0.15)) * 2;

    // Age weathering - damping and filtering
    sig = LPF.ar(sig, age.linexp(0, 1, 6000, 2000));

    // Concrete surface texture
    sig = sig + BPF.ar(BrownNoise.ar(0.15), freq * 0.7, 0.3) * 2;

    // Continuous bed
    sig = sig + LPF.ar(BrownNoise.ar(0.1), 250);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mirrors_dish loaded".postln;
