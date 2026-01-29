// harga/cliff — Lightweight end-stage generator
// Ättestupa vertigo with chaos cross-mod
//
// P1: Osc A edge tone      P2: Osc B abyss drone
// P3: Cross-mod vertigo     P4: Cross-mod gravity return
// P5: Rungle falling chaos

SynthDef(\forge_harga_cliff, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var oscA, oscB, xmod, xret, rungle;
    var oscAMod, oscBMod, xmodMod, xretMod, rungleMod;
    var voiceA, voiceB, vertigo, fall;

    freq = In.kr(freqBus);

    // Read custom params
    oscA = p[0];      // P1: Osc A edge tone
    oscB = p[1];      // P2: Osc B abyss drone
    xmod = p[2];      // P3: Cross-mod vertigo depth
    xret = p[3];      // P4: Cross-mod gravity return
    rungle = p[4];    // P5: Rungle falling chaos

    // BENJOLIN CROSS-MOD: Vertigo feedback network
    oscAMod = oscA * (0.3 + (xret * 0.7)) * (1 + (rungle * 0.4));
    oscBMod = oscB * (0.35 + (rungle * 0.65)) * (1 + (xmod * 0.3));
    xmodMod = xmod * (1 + (oscA * oscB * 0.6));
    xretMod = xret * (1 + (oscB * rungle * 0.5));
    rungleMod = rungle * (1 + (xmod * xret * 0.45));

    // DSP: Ättestupa vertigo with chaos cross-mod

    // Falling rate from rungle
    fall = LFNoise2.kr(rungleMod * 3 + 0.2).range(0.5, 4);

    // Voice A: Edge chaos - Crackle-based instability
    voiceA = Crackle.ar(oscAMod.linlin(0, 1, 1.5, 1.95)) * 0.3;
    voiceA = voiceA + (LFNoise0.ar(freq * oscAMod.linlin(0, 1, 0.5, 2)) * 0.2);
    voiceA = RLPF.ar(voiceA, freq * xmodMod.linlin(0, 1, 1, 8), 0.3);

    // Voice B: Abyss - deep unstable tones
    voiceB = SinOsc.ar(
        freq * oscBMod.linlin(0, 1, 0.25, 1) * (1 + (voiceA * xmodMod * 0.5)),
        0,
        0.3
    );
    voiceB = voiceB + (LFTri.ar(freq * 0.5 * (1 + (rungleMod * 0.2))) * 0.15);

    // Cross-mod: A and B destabilize each other
    voiceA = voiceA * (1 + (voiceB * xretMod * 0.6));
    voiceB = voiceB * (1 + (voiceA * xmodMod * 0.4));

    // Vertigo: spinning disorientation
    vertigo = SinOsc.ar(freq * [1, 1.01, 0.99], LFSaw.kr(fall).range(0, 2pi), 0.15).sum;
    vertigo = vertigo * (1 + (SinOsc.kr(fall * 2) * xretMod * 0.3));

    sig = (voiceA * 0.35) + (voiceB * 0.35) + (vertigo * rungleMod);

    // Falling pitch drift
    sig = sig + (PitchShift.ar(sig, 0.1, LFNoise1.kr(fall).range(0.98, 1.02)) * rungleMod * 0.2);

    // Abyss reverb
    sig = sig + (CombL.ar(sig, 0.3, xretMod.linlin(0, 1, 0.1, 0.25), rungleMod * 1.5) * 0.2);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_harga_cliff loaded".postln;
