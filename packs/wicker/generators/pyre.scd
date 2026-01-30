// wicker/pyre — Lightweight end-stage generator
SynthDef(\forge_wicker_pyre, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var kindle, blaze, ember, smoke, ash;
    var kindleMod, blazeMod, emberMod, smokeMod, ashMod;
    var crackle, roar, glow, sparks;

    // Read custom params
    kindle = p[0];  // P1: Kindle intensity - scaled by ember
    blaze = p[1];  // P2: Blaze height - curve set by ash
    ember = p[2];  // P3: Ember glow - modulates kindle AND smoke
    smoke = p[3];  // P4: Smoke density - feeds back to blaze
    ash = p[4];  // P5: Ash accumulation - master decay reshaper

    // BUTTERFLY EFFECT: Cross-modulation network
    kindleMod = kindle * (0.4 + (ember * 0.6));
    blazeMod = blaze.linexp(0, 1, 0.5, 8) * (1 + (smoke * ash * 1.5));
    emberMod = ember * (1 + (ash.squared * 0.4));
    smokeMod = smoke * (0.3 + (kindle * blaze * 0.7));
    ashMod = ash * (1 + (ember * smoke * 0.5));

    freq = In.kr(freqBus);

    // DSP: Fire crackling and roar

    // Crackle: rhythmic pops and snaps
    crackle = Dust.ar(kindleMod.linexp(0, 1, 5, 80) * [1, 1.2]);
    crackle = Ringz.ar(crackle, [2200, 3500, 5800, 8200] * emberMod.linlin(0, 1, 0.5, 1.5), 0.01).sum * 0.4;
    crackle = crackle * (1 + (LFNoise1.kr(blazeMod) * 0.5));

    // Roar: low rumble of flames
    roar = BrownNoise.ar(0.3) + (PinkNoise.ar(0.2) * smokeMod);
    roar = RLPF.ar(roar, freq * blazeMod.linlin(0, 1, 1, 4), 0.3 + (ashMod * 0.4));
    roar = roar * kindleMod.linlin(0, 1, 0.3, 1);

    // Glow: warm sustained tone
    glow = SinOsc.ar(freq * [1, 2.01, 3.02], 0, [0.3, 0.15, 0.08]).sum;
    glow = glow * emberMod.linlin(0, 1, 0.2, 0.8);
    glow = glow * (1 + (SinOsc.kr(blazeMod * 2) * smokeMod * 0.3));

    // Sparks: occasional bright transients
    sparks = Dust.ar(ashMod.linexp(0, 1, 0.5, 8) * [1, 0.8]);
    sparks = Ringz.ar(sparks, freq * [4, 6, 8], smokeMod.linlin(0, 1, 0.05, 0.2)).sum * 0.2;

    // Mix based on ash (chaos axis)
    sig = (roar * 0.4) + (crackle * (0.3 + (ashMod * 0.3))) + (glow * (1 - (ashMod * 0.5))) + sparks;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_wicker_pyre loaded".postln;
