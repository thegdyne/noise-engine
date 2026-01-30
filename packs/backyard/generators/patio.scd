// backyard/patio — Lightweight end-stage generator
SynthDef(\forge_backyard_patio, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var roll, groove, wheel, rattle, grit;
    var wheelRumble, grooveBump, boardRattle, surfaceGrit, bumpRate;

    roll = p[0];
    groove = p[1];
    wheel = p[2];
    rattle = p[3];
    grit = p[4];

    freq = In.kr(freqBus);

    // Continuous wheel rumble - low filtered noise
    wheelRumble = BrownNoise.ar(0.4) + PinkNoise.ar(0.2);
    wheelRumble = LPF.ar(wheelRumble, wheel.linexp(0, 1, 80, 400));
    wheelRumble = wheelRumble * roll.linlin(0, 1, 0.3, 1);

    // Groove bumps - rhythmic impacts as wheels hit grouting
    bumpRate = roll.linexp(0, 1, 2, 12);
    grooveBump = Impulse.ar(bumpRate) + Dust.ar(bumpRate * 0.5);
    grooveBump = Ringz.ar(grooveBump * groove * 0.5, freq * [1, 1.5, 2], 0.05).sum;
    grooveBump = grooveBump + (BPF.ar(WhiteNoise.ar(1), freq * 2, 0.3) * Decay.ar(Impulse.ar(bumpRate), 0.03) * groove * 0.3);

    // Board rattle - higher frequency wood resonance
    boardRattle = WhiteNoise.ar(0.3) * LFNoise1.kr(roll.linlin(0, 1, 5, 20)).range(0.2, 1);
    boardRattle = BPF.ar(boardRattle, [800, 1200, 1800], 0.2).sum;
    boardRattle = boardRattle * rattle * roll * 0.4;

    // Surface grit - textured high frequency
    surfaceGrit = PinkNoise.ar(0.2);
    surfaceGrit = HPF.ar(surfaceGrit, 2000);
    surfaceGrit = surfaceGrit * grit * roll * 0.3;

    // Mix all components
    sig = wheelRumble + grooveBump + boardRattle + surfaceGrit;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_backyard_patio loaded".postln;
