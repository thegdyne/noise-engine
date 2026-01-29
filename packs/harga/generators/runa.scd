// harga/runa — Lightweight end-stage generator
// Runic patterns with hard sync cross-mod
//
// P1: Osc A master stroke   P2: Osc B slave angle
// P3: Cross-mod carve depth P4: Cross-mod stone return
// P5: Rungle ancient chaos

SynthDef(\forge_harga_runa, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var oscA, oscB, xmod, xret, rungle;
    var oscAMod, oscBMod, xmodMod, xretMod, rungleMod;
    var voiceA, voiceB, carve, stone, syncRatio;

    freq = In.kr(freqBus);

    // Read custom params
    oscA = p[0];      // P1: Osc A master stroke
    oscB = p[1];      // P2: Osc B slave angle
    xmod = p[2];      // P3: Cross-mod carve depth
    xret = p[3];      // P4: Cross-mod stone return
    rungle = p[4];    // P5: Rungle ancient chaos

    // BENJOLIN CROSS-MOD: Angular rune network
    oscAMod = oscA * (0.4 + (xret * 0.6)) * (1 + (rungle * 0.3));
    oscBMod = oscB * (0.35 + (rungle * 0.65)) * (1 + (xmod * 0.25));
    xmodMod = xmod * (1 + (oscA * oscB * 0.5));
    xretMod = xret * (1 + (oscB * rungle * 0.4));
    rungleMod = rungle * (1 + (xmod * xret * 0.35));

    // DSP: Runic patterns with hard sync cross-mod

    // Sync ratio from cross-mod
    syncRatio = xmodMod.linlin(0, 1, 1.5, 4);

    // Voice A: Master oscillator - angular saw
    voiceA = LFSaw.ar(freq * oscAMod.linlin(0, 1, 0.5, 2), 0, 0.3);

    // Voice B: Slave oscillator - synced to A
    voiceB = SyncSaw.ar(
        freq * oscAMod.linlin(0, 1, 0.5, 2),
        freq * oscBMod.linlin(0, 1, 1, 3) * syncRatio,
        0.3
    );

    // Cross-mod: Sync ratio influenced by both voices
    voiceB = voiceB * (1 + (voiceA * xmodMod * 0.3));
    voiceA = voiceA * (1 + (voiceB * xretMod * 0.25));

    // Carve: Additional sync layers
    carve = SyncSaw.ar(
        freq * 2,
        freq * xmodMod.linlin(0, 1, 3, 8),
        0.15
    );
    carve = carve * rungleMod;

    // Stone: Angular pulse undertone
    stone = Pulse.ar(
        freq * oscBMod.linlin(0, 1, 0.5, 1),
        xretMod.linlin(0, 1, 0.2, 0.8),
        0.15
    );
    stone = stone * (1 + (LFNoise0.kr(rungleMod * 3 + 0.5) * 0.2));

    sig = (voiceA * 0.3) + (voiceB * 0.3) + carve + (stone * (1 - (rungleMod * 0.5)));

    // Angular modulation
    sig = sig * (1 + (LFPulse.kr(oscAMod * 2 + 0.5, 0, 0.5) * xretMod * 0.15));

    // Rune resonance
    sig = sig + (Ringz.ar(sig * 0.1, freq * [2.3, 3.7], xmodMod.linlin(0, 1, 0.02, 0.08)).sum * 0.2);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_harga_runa loaded".postln;
