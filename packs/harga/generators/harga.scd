// harga/harga — Lightweight end-stage generator
// Commune voices with cross-mod harmonics
//
// P1: Osc A elder tone      P2: Osc B youth voice
// P3: Cross-mod merge depth P4: Cross-mod echo return
// P5: Rungle communion

SynthDef(\forge_harga_harga, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var oscA, oscB, xmod, xret, rungle;
    var oscAMod, oscBMod, xmodMod, xretMod, rungleMod;
    var voiceA, voiceB, commune, unison;

    freq = In.kr(freqBus);

    // Read custom params
    oscA = p[0];      // P1: Osc A elder tone
    oscB = p[1];      // P2: Osc B youth voice
    xmod = p[2];      // P3: Cross-mod merge depth
    xret = p[3];      // P4: Cross-mod echo return
    rungle = p[4];    // P5: Rungle communion

    // BENJOLIN CROSS-MOD: Voices merging network
    oscAMod = oscA * (0.35 + (xret * 0.65)) * (1 + (rungle * 0.25));
    oscBMod = oscB * (0.4 + (rungle * 0.6)) * (1 + (xmod * 0.25));
    xmodMod = xmod * (1 + (oscA * oscB * 0.45));
    xretMod = xret * (1 + (oscB * rungle * 0.35));
    rungleMod = rungle * (1 + (xmod * xret * 0.4));

    // DSP: Commune voices with cross-mod harmonics

    // Voice A: Elder drone - harmonic stack
    voiceA = Mix.fill(6, { |i|
        var partial, drift, gain;
        partial = i + 1;
        drift = SinOsc.kr(oscAMod * 0.2 * (i + 1), i * 0.5).range(0.998, 1.002);
        gain = (1 / partial.sqrt) * (1 - (i * 0.1 * xretMod));
        SinOsc.ar(freq * partial * drift, 0, gain.max(0))
    }) * 0.2;

    // Voice B: Youth response - offset harmonics
    voiceB = Mix.fill(5, { |i|
        var partial, phase, gain;
        partial = i + 1.5;
        phase = voiceA * xmodMod * pi * 0.5;
        gain = (1 / (i + 2)) * oscBMod;
        SinOsc.ar(freq * partial * (1 + (rungleMod * 0.02)), phase, gain)
    }) * 0.25;

    // Cross-mod return: B shapes A's spectrum
    voiceA = voiceA * (1 + (voiceB * xretMod * 0.3));

    // Commune blend: voices merge
    commune = voiceA + voiceB;

    // Unison drift: everyone slightly different
    unison = DelayC.ar(commune, 0.05, LFNoise1.kr(rungleMod + 0.1).range(0.01, 0.04));
    unison = unison * xmodMod * 0.3;

    sig = commune + unison;

    // Communal breathing
    sig = sig * (1 + (SinOsc.kr(oscAMod * 0.1 + 0.05) * 0.15));

    // Rungle injection: collective unconscious
    sig = sig + (LFNoise1.ar(rungleMod * 30 + 5) * rungleMod * 0.08);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_harga_harga loaded".postln;
