// wicker/sun — Lightweight end-stage generator
SynthDef(\forge_wicker_sun, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var golden, heat, zenith, haze, scorch;
    var goldenMod, heatMod, zenithMod, hazeMod, scorchMod;
    var warmth, shimmer, oppression, pulse;

    // Read custom params
    golden = p[0];  // P1: Golden intensity - scaled by zenith
    heat = p[1];  // P2: Heat intensity - curve set by scorch
    zenith = p[2];  // P3: Zenith height - modulates golden AND haze
    haze = p[3];  // P4: Haze thickness - feeds back to heat
    scorch = p[4];  // P5: Scorch severity - master oppression axis

    // BUTTERFLY EFFECT: Cross-modulation network
    goldenMod = golden * (0.35 + (zenith * 0.65));
    heatMod = heat.linexp(0, 1, 0.2, 4) * (1 + (haze * scorch * 1.4));
    zenithMod = zenith * (1 + (scorch.squared * 0.55));
    hazeMod = haze * (0.4 + (golden * heat * 0.6));
    scorchMod = scorch * (1 + (zenith * haze * 0.45));

    freq = In.kr(freqBus);

    // DSP: Oppressive summer sun

    // Warmth: rich filtered noise bed
    warmth = PinkNoise.ar(0.3) + (BrownNoise.ar(0.2) * goldenMod);
    warmth = RLPF.ar(warmth, freq * heatMod.linlin(0, 1, 1, 4), 0.3 + (hazeMod * 0.3));
    warmth = warmth * goldenMod.linlin(0, 1, 0.3, 0.8);

    // Shimmer: high frequency heat distortion
    shimmer = WhiteNoise.ar(0.1) * Resonz.ar(
        PinkNoise.ar(0.5),
        freq * zenithMod.linlin(0, 1, 4, 12) * [1, 1.02, 1.05],
        0.05
    ).sum;
    shimmer = shimmer * zenithMod.linlin(0, 1, 0.1, 0.5);
    shimmer = shimmer * (1 + (SinOsc.kr(heatMod * 0.5) * 0.2));

    // Oppression: slow heavy modulation
    oppression = SinOsc.ar(freq * [0.5, 1, 1.5], 0, [0.2, 0.15, 0.08]).sum;
    oppression = oppression * (1 + (SinOsc.kr(scorchMod * 0.1) * hazeMod * 0.4));
    oppression = oppression + (LFTri.ar(freq * 2) * 0.05 * scorchMod);

    // Pulse: heartbeat of the unrelenting
    pulse = SinOsc.ar(freq * 0.25, 0, 0.1);
    pulse = pulse * (1 + (SinOsc.kr(0.3 * scorchMod) * 0.5));
    pulse = pulse * scorchMod.linlin(0, 1, 0.2, 1);

    // Mix based on scorch (oppression axis)
    sig = warmth + shimmer + (oppression * (1 - (scorchMod * 0.3))) + pulse;

    // Heat haze wavering
    sig = sig + (DelayC.ar(sig, 0.02, SinOsc.kr(hazeMod * 2).range(0.005, 0.015)) * hazeMod * 0.2);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_wicker_sun loaded".postln;
