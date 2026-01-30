// backyard/climb — Lightweight end-stage generator
SynthDef(\forge_backyard_climb, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var strike, ringTime, ladder, hollow, rust;
    var exciter, barModes, ladderStep, hollowRes, rustNoise;
    var modeFreqs, modeAmps, modeDecays;

    strike = p[0];
    ringTime = p[1];
    ladder = p[2];
    hollow = p[3];
    rust = p[4];

    freq = In.kr(freqBus);

    // Excitation - hand grabs, feet on bars
    exciter = Dust.ar(strike.linexp(0, 1, 1, 8)) * 0.5;
    exciter = exciter + (PinkNoise.ar(0.02) * strike);

    // Modal bar resonances - hollow metal tube frequencies
    modeFreqs = [1, 2.76, 5.40, 8.93, 13.34] * freq;
    modeAmps = [1, 0.6, 0.4, 0.25, 0.15];
    modeDecays = [1, 0.8, 0.6, 0.4, 0.3] * ringTime.linlin(0, 1, 0.3, 2);

    barModes = DynKlank.ar(
        `[modeFreqs, modeAmps, modeDecays],
        exciter,
        freq,
        0,
        ringTime.linlin(0, 1, 0.5, 3)
    ) * 0.15;

    // Ladder stepping - rhythmic metallic footsteps
    ladderStep = Dust.ar(ladder.linexp(0, 1, 0.5, 4));
    ladderStep = Ringz.ar(ladderStep * 0.4, freq * [1.5, 2.2, 3.1], ringTime.linlin(0, 1, 0.1, 0.4)).sum;
    ladderStep = ladderStep * ladder * 0.4;

    // Hollow body resonance - deep tube sound
    hollowRes = Resonz.ar(exciter + (BrownNoise.ar(0.1) * hollow), freq * 0.5, 0.1) * 4;
    hollowRes = hollowRes * hollow * 0.3;

    // Rust texture - gritty high frequency content
    rustNoise = HPF.ar(PinkNoise.ar(0.15), 3000) * rust;
    rustNoise = rustNoise * Decay.ar(Dust.ar(3), 0.1);

    // Mix all components
    sig = barModes + ladderStep + hollowRes + rustNoise;

    // Add continuous bed
    sig = sig + (BrownNoise.ar(0.015) * hollow);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_backyard_climb loaded".postln;
