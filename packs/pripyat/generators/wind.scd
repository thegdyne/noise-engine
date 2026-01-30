// pripyat/wind — Lightweight end-stage generator
SynthDef(\forge_pripyat_wind, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var gust, cold, tree, howl, dead;
    var windBase, gustMod, coldSig, howlSig, treeSig, leafSig;

    freq = In.kr(freqBus);

    gust = p[0];
    cold = p[1];
    tree = p[2];
    howl = p[3];
    dead = p[4];

    // Gust modulation - slow irregular intensity changes
    gustMod = LFNoise2.kr(gust.linexp(0, 1, 0.05, 0.5)).range(0.3, 1);
    gustMod = gustMod * LFNoise2.kr(0.1).range(0.7, 1);

    // Base wind - filtered noise
    windBase = PinkNoise.ar(1);
    windBase = LPF.ar(windBase, freq * 4);
    windBase = HPF.ar(windBase, freq * 0.25);
    windBase = windBase * gustMod * 0.4;

    // Cold high frequencies
    coldSig = HPF.ar(WhiteNoise.ar(1), 3000);
    coldSig = coldSig * LFNoise2.kr(2).range(0, 1) * cold * gustMod * 0.15;

    // Low howling moan
    howlSig = BPF.ar(BrownNoise.ar(1), freq * 0.5 * LFNoise2.kr(0.2).range(0.8, 1.2), 0.1);
    howlSig = howlSig * LFNoise2.kr(0.3).range(0, 1) * howl * gustMod * 2;

    // Tree branch resonance
    treeSig = Resonz.ar(windBase, freq * LFNoise2.kr(0.5).range(1, 3), 0.1);
    treeSig = treeSig * tree * 4;

    // Dead leaf rustle - high crinkly texture
    leafSig = HPF.ar(GrayNoise.ar(1), 2000);
    leafSig = leafSig * Dust.kr(dead.linexp(0, 1, 1, 20)).lag(0.05);
    leafSig = leafSig * dead * gustMod * 0.2;

    // Mix all components
    sig = windBase + coldSig + howlSig + treeSig + leafSig;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_pripyat_wind loaded".postln;
