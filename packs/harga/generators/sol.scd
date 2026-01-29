// harga/sol — Lightweight end-stage generator
// Midnight sun with cross-mod noise drones
//
// P1: Osc A corona glow       P2: Osc B horizon shimmer
// P3: Cross-mod radiance      P4: Cross-mod heat return
// P5: Rungle eternal chaos

SynthDef(\forge_harga_sol, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var oscA, oscB, xmod, xret, rungle;
    var oscAMod, oscBMod, xmodMod, xretMod, rungleMod;
    var voiceA, voiceB, glare, endless;

    freq = In.kr(freqBus);

    // Read custom params
    oscA = p[0];      // P1: Osc A corona glow
    oscB = p[1];      // P2: Osc B horizon shimmer
    xmod = p[2];      // P3: Cross-mod radiance depth
    xret = p[3];      // P4: Cross-mod heat return
    rungle = p[4];    // P5: Rungle eternal chaos

    // BENJOLIN CROSS-MOD: Endless sun network
    oscAMod = oscA * (0.35 + (xret * 0.65)) * (1 + (rungle * 0.25));
    oscBMod = oscB * (0.4 + (rungle * 0.6)) * (1 + (xmod * 0.2));
    xmodMod = xmod * (1 + (oscA * oscB * 0.35));
    xretMod = xret * (1 + (oscB * rungle * 0.3));
    rungleMod = rungle * (1 + (xmod * xret * 0.35));

    // DSP: Midnight sun with cross-mod noise drones

    // Voice A: Corona - warm filtered noise
    voiceA = PinkNoise.ar(0.3) + (BrownNoise.ar(0.2) * oscAMod);
    voiceA = RLPF.ar(voiceA, freq * oscAMod.linlin(0, 1, 1, 4), 0.3 + (xretMod * 0.3));
    voiceA = voiceA * oscAMod.linlin(0, 1, 0.4, 0.9);

    // Voice B: Horizon shimmer - high frequency haze
    voiceB = WhiteNoise.ar(0.15) * Resonz.ar(
        PinkNoise.ar(0.4),
        freq * oscBMod.linlin(0, 1, 4, 12) * [1, 1.02],
        0.08
    ).sum;
    voiceB = voiceB * oscBMod.linlin(0, 1, 0.2, 0.6);

    // Cross-mod: Corona and shimmer intertwine
    voiceA = voiceA * (1 + (voiceB * xmodMod * 0.4));
    voiceB = voiceB + (voiceA * xretMod * 0.3);

    // Glare: sustained bright tones
    glare = SinOsc.ar(freq * [1, 2, 3], 0, [0.15, 0.08, 0.04]).sum;
    glare = glare * (1 + (SinOsc.kr(rungleMod * 0.2) * xmodMod * 0.2));

    // Endless: never-setting quality
    endless = LFTri.ar(freq * 0.5, 0, 0.1);
    endless = endless * (1 + (LFNoise1.kr(xretMod * 0.3) * 0.15));

    sig = voiceA + voiceB + (glare * (1 - (rungleMod * 0.3))) + (endless * rungleMod);

    // Heat haze wavering
    sig = sig + (DelayC.ar(sig, 0.02, SinOsc.kr(oscBMod * 1.5).range(0.005, 0.015)) * xmodMod * 0.2);

    // Rungle: eternal brightness instability
    sig = sig * (1 + (LFNoise2.kr(rungleMod * 2 + 0.1) * rungleMod * 0.15));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_harga_sol loaded".postln;
