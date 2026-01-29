// harga/tempel — Lightweight end-stage generator
// Yellow temple burning with wavefold cross-mod
//
// P1: Osc A flame core      P2: Osc B ember glow
// P3: Cross-mod burn depth  P4: Cross-mod smoke return
// P5: Rungle sacrifice chaos

SynthDef(\forge_harga_tempel, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var oscA, oscB, xmod, xret, rungle;
    var oscAMod, oscBMod, xmodMod, xretMod, rungleMod;
    var voiceA, voiceB, flame, ash, foldAmt;

    freq = In.kr(freqBus);

    // Read custom params
    oscA = p[0];      // P1: Osc A flame core
    oscB = p[1];      // P2: Osc B ember glow
    xmod = p[2];      // P3: Cross-mod burn depth
    xret = p[3];      // P4: Cross-mod smoke return
    rungle = p[4];    // P5: Rungle sacrifice chaos

    // BENJOLIN CROSS-MOD: Burning temple network
    oscAMod = oscA * (0.35 + (xret * 0.65)) * (1 + (rungle * 0.35));
    oscBMod = oscB * (0.4 + (rungle * 0.6)) * (1 + (xmod * 0.3));
    xmodMod = xmod * (1 + (oscA * oscB * 0.55));
    xretMod = xret * (1 + (oscB * rungle * 0.45));
    rungleMod = rungle * (1 + (xmod * xret * 0.4));

    // DSP: Yellow temple burning with wavefold cross-mod

    // Fold amount from cross-mod
    foldAmt = xmodMod.linlin(0, 1, 1, 4);

    // Voice A: Flame core - wavefolded saw
    voiceA = LFSaw.ar(freq * oscAMod.linlin(0, 1, 0.5, 2), 0, 0.8);
    voiceA = (voiceA * foldAmt).fold2(1) * 0.4;
    voiceA = voiceA + ((voiceA * xretMod * 2).tanh * 0.2);

    // Voice B: Ember glow - softer fold
    voiceB = SinOsc.ar(freq * oscBMod.linlin(0, 1, 1, 3), 0, 0.6);
    voiceB = voiceB + (LFTri.ar(freq * oscBMod.linlin(0, 1, 0.5, 1.5), 0, 0.3));
    voiceB = (voiceB * (1 + (rungleMod * 2))).fold2(1) * 0.35;

    // Cross-mod: Flames feed each other
    voiceA = voiceA * (1 + (voiceB * xmodMod * 0.4));
    voiceB = voiceB + (voiceA * xretMod * 0.3);

    // Additional fold cascade
    voiceA = (voiceA * (1 + xretMod)).fold2(1);

    // Flame: Crackling destruction
    flame = Crackle.ar(rungleMod.linlin(0, 1, 1.3, 1.8)) * 0.15;
    flame = RLPF.ar(flame, freq * xmodMod.linlin(0, 1, 2, 8), 0.4);

    // Ash: What remains
    ash = PinkNoise.ar(0.1) * rungleMod;
    ash = RLPF.ar(ash, freq * xretMod.linlin(0, 1, 0.5, 2), 0.5);

    sig = (voiceA * 0.35) + (voiceB * 0.3) + flame + ash;

    // Burning intensity modulation
    sig = sig * (1 + (LFNoise2.kr(rungleMod * 3 + 0.5) * xmodMod * 0.2));

    // Heat shimmer
    sig = sig + (DelayC.ar(sig, 0.03, SinOsc.kr(oscAMod * 2).range(0.01, 0.025)) * rungleMod * 0.15);

    // Temple resonance
    sig = sig + (CombL.ar(sig * 0.3, 0.2, xretMod.linlin(0, 1, 0.05, 0.15), rungleMod * 0.8) * 0.2);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_harga_tempel loaded".postln;
