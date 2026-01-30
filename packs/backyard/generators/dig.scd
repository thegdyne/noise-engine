// backyard/dig — Lightweight end-stage generator
SynthDef(\forge_backyard_dig, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var spade, soil, stone, digDepth, effort;
    var spadeHit, soilMove, stoneClunk, earthThud, effortBreath;
    var digTrig, digRate, modIndex;

    spade = p[0];
    soil = p[1];
    stone = p[2];
    digDepth = p[3];
    effort = p[4];

    freq = In.kr(freqBus);

    // Digging rate
    digRate = effort.linexp(0, 1, 0.5, 3);
    digTrig = Dust.ar(digRate);

    // Spade hit - FM metallic clang
    modIndex = spade.linlin(0, 1, 2, 8);
    spadeHit = SinOsc.ar(
        freq * 2.5 + (SinOsc.ar(freq * 7.1, 0, freq * modIndex) * Decay.ar(digTrig, 0.1)),
        0,
        Decay2.ar(digTrig, 0.002, 0.08)
    );
    spadeHit = spadeHit * spade * 0.4;

    // Soil movement - granular texture
    soilMove = PinkNoise.ar(0.3) * Decay.ar(digTrig, soil.linlin(0, 1, 0.1, 0.3));
    soilMove = LPF.ar(soilMove, soil.linexp(0, 1, 800, 2500));
    soilMove = soilMove * soil * 0.4;

    // Stone clunk - occasional hard impact
    stoneClunk = Dust.ar(digRate * stone * 0.5);
    stoneClunk = SinOsc.ar(
        freq * 1.5 + (SinOsc.ar(freq * 3.2, 0, freq * 4) * Decay.ar(stoneClunk, 0.05)),
        0,
        Decay2.ar(stoneClunk, 0.001, 0.06)
    );
    stoneClunk = stoneClunk + (BrownNoise.ar(0.2) * Decay.ar(Dust.ar(digRate * stone * 0.5), 0.03));
    stoneClunk = stoneClunk * stone * 0.5;

    // Earth thud - low body of dig
    earthThud = BrownNoise.ar(0.4) * Decay.ar(digTrig, 0.12);
    earthThud = LPF.ar(earthThud, digDepth.linexp(0, 1, 150, 400));
    earthThud = earthThud * digDepth * 0.4;

    // Effort breath - exertion sounds
    effortBreath = PinkNoise.ar(0.15);
    effortBreath = BPF.ar(effortBreath, 800, 0.6);
    effortBreath = effortBreath * LFNoise1.kr(effort.linlin(0, 1, 0.5, 2)).range(0, 1);
    effortBreath = effortBreath * effort * 0.25;

    // Mix all components
    sig = spadeHit + soilMove + stoneClunk + earthThud + effortBreath;

    // Continuous bed for drone stability - earth/soil ambience
    sig = sig + (BrownNoise.ar(0.1) + PinkNoise.ar(0.06));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_backyard_dig loaded".postln;
