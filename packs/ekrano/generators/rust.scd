// ekrano/rust — Lightweight end-stage generator
SynthDef(\forge_ekrano_rust, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var dustParam, creak, peel, grit, voidParam;
    var dustTrig, creakSig, gritSig, resSig, voidSig;

    freq = In.kr(freqBus);

    dustParam = p[0].linexp(0, 1, 1, 30);
    creak = p[1].linexp(0, 1, 0.5, 4);
    peel = p[2].linexp(0, 1, 0.1, 2);
    grit = p[3];
    voidParam = p[4];

    // Dust triggers
    dustTrig = Dust.ar(dustParam);

    // Creaking resonator - metal stress sounds
    creakSig = Ringz.ar(
        dustTrig,
        freq * creak * LFNoise1.kr(0.5).range(0.9, 1.1),
        peel
    ) * 0.3;

    // Secondary resonance at different pitch
    resSig = Ringz.ar(
        dustTrig,
        freq * creak * 1.7,
        peel * 0.7
    ) * 0.2;

    // Grit noise layer
    gritSig = BPF.ar(
        GrayNoise.ar(0.3) * Decay.ar(dustTrig, 0.05),
        freq * 2,
        0.8
    ) * grit;

    // Void - sparse reverberant space
    voidSig = CombL.ar(creakSig + resSig, 0.5, 0.3, 3) * voidParam * 0.3;

    sig = creakSig + resSig + gritSig + voidSig;

    // Add subtle continuous noise bed for drone mode
    sig = sig + (BrownNoise.ar(0.02) * (1 - grit));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ekrano_rust loaded".postln;
