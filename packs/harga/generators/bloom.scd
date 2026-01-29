// harga/bloom — Lightweight end-stage generator
// Twin oscillator bloom with Benjolin cross-modulation
//
// P1: Osc A petal unfurl    P2: Osc B pollen drift
// P3: Cross-mod A→B depth   P4: Cross-mod B→A return
// P5: Rungle chaos

SynthDef(\forge_harga_bloom, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var oscA, oscB, xmod, xret, rungle;
    var oscAMod, oscBMod, xmodMod, xretMod, rungleMod;
    var voiceA, voiceB, breathRate, petalPhase;

    freq = In.kr(freqBus);

    // Read custom params
    oscA = p[0];      // P1: Osc A petal unfurl
    oscB = p[1];      // P2: Osc B pollen drift
    xmod = p[2];      // P3: Cross-mod A→B depth
    xret = p[3];      // P4: Cross-mod B→A return
    rungle = p[4];    // P5: Rungle chaos

    // BENJOLIN CROSS-MOD: Mutual influence network
    oscAMod = oscA * (0.4 + (xret * 0.6)) * (1 + (rungle * 0.3));
    oscBMod = oscB * (0.3 + (rungle * 0.7)) * (1 + (xmod * 0.2));
    xmodMod = xmod * (1 + (oscA * oscB * 0.5));
    xretMod = xret * (1 + (oscB * rungle * 0.4));
    rungleMod = rungle * (1 + (xmod * xret * 0.3));

    // DSP: Twin oscillator bloom with cross-modulation

    // Breathing rate from rungle chaos
    breathRate = LFNoise1.kr(rungleMod * 2 + 0.1).range(0.3, 2);

    // Oscillator A: Petal unfurl - feedback FM
    voiceA = SinOscFB.ar(
        freq * oscAMod.linlin(0, 1, 0.5, 2),
        xmodMod.linlin(0, 1, 0.1, 1.2)
    );

    // Petal phase modulation from voice B feedback
    petalPhase = LFTri.kr(breathRate * xretMod.linlin(0, 1, 0.5, 3));
    voiceA = voiceA * (0.5 + (petalPhase * 0.3));

    // Oscillator B: Pollen drift - modulated by voice A
    voiceB = SinOsc.ar(
        freq * oscBMod.linlin(0, 1, 1, 4) * (1 + (voiceA * xmodMod * 0.3)),
        voiceA * xmodMod * pi
    );

    // Return path: B modulates A's amplitude
    voiceA = voiceA * (1 + (voiceB * xretMod * 0.4));

    // Bloom harmonics
    voiceA = voiceA + (SinOsc.ar(freq * [2.01, 3.02], 0, 0.1 * oscAMod).sum);
    voiceB = voiceB + (SinOsc.ar(freq * [1.5, 2.5], 0, 0.08 * oscBMod).sum);

    // Rungle injection: chaotic modulation
    sig = (voiceA * 0.4) + (voiceB * 0.3);
    sig = sig * (1 + (LFNoise2.ar(rungleMod * 50 + 1) * rungleMod * 0.3));

    // Stereo bloom
    sig = sig + (DelayC.ar(sig, 0.03, SinOsc.kr(breathRate).range(0.01, 0.025)) * 0.2);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_harga_bloom loaded".postln;
