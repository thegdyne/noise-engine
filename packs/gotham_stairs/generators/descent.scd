// gotham_stairs/descent — Lightweight end-stage generator
SynthDef(\forge_gotham_stairs_descent, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var stepRate, concrete, echo, weight, irregular;
    var trig, stepTrig, impact, modes, delayedSig;

    stepRate = p[0].linlin(0, 1, 0.5, 8);
    concrete = p[1];
    echo = p[2];
    weight = p[3];
    irregular = p[4];

    freq = In.kr(freqBus);

    // Irregular step trigger with timing variation
    stepTrig = Dust.ar(stepRate * (1 + (irregular * LFNoise1.kr(2).range(0, 0.5))));

    // Impact excitation - thump of foot on concrete
    impact = stepTrig * (weight.linlin(0, 1, 0.3, 1.0));
    impact = impact + (PinkNoise.ar(0.1) * Decay.ar(stepTrig, 0.02));

    // Modal resonances of concrete steps
    modes = DynKlank.ar(
        `[
            [1, 2.3, 3.1, 4.7, 6.2],
            [1, 0.5, 0.3, 0.2, 0.1] * concrete,
            [0.3, 0.2, 0.15, 0.1, 0.08] * (1 + weight)
        ],
        impact,
        freq * 0.5,
        0,
        concrete.linlin(0, 1, 0.1, 0.4)
    );

    // Add continuous low rumble for drone compatibility
    sig = modes + (BrownNoise.ar(0.05) * weight);

    // Stairwell echo/delay
    delayedSig = CombL.ar(sig, 0.5, echo.linlin(0, 1, 0.05, 0.3), echo.linlin(0, 1, 0.5, 3));
    sig = sig + (delayedSig * echo * 0.4);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_gotham_stairs_descent loaded".postln;
