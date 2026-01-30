// oldwinch/mist — Lightweight end-stage generator
SynthDef(\forge_oldwinch_mist, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var rise, valley, dawn, drift, chill;
    var grains, grainRate, trig1, trig2, trig3, trig4;
    var driftMod, valleyLow, dawnBright, chillHigh;

    rise = p[0];
    valley = p[1];
    dawn = p[2];
    drift = p[3];
    chill = p[4];

    freq = In.kr(freqBus);

    // Drift modulation
    driftMod = LFNoise2.kr(drift.linexp(0, 1, 0.1, 0.5)).range(0.95, 1.05);

    // Grain rate based on rising mist
    grainRate = rise.linexp(0, 1, 8, 50);

    // Multiple grain streams
    trig1 = Dust.ar(grainRate);
    trig2 = Dust.ar(grainRate * 0.7);
    trig3 = Dust.ar(grainRate * 1.3);
    trig4 = Dust.ar(grainRate * 0.5);

    // Grains as soft resonances - misty quality
    grains = Ringz.ar(trig1, freq * driftMod, 0.08 + (rise * 0.1), 0.2);
    grains = grains + Ringz.ar(trig2, freq * 1.5 * driftMod, 0.06 + (rise * 0.08), 0.15);
    grains = grains + Ringz.ar(trig3, freq * 0.75 * driftMod, 0.1 + (rise * 0.12), 0.18);
    grains = grains + Ringz.ar(trig4, freq * 2 * driftMod, 0.05, 0.12 * dawn);

    // Soften the grains
    grains = LPF.ar(grains, dawn.linexp(0, 1, 2000, 5000));

    sig = grains * 0.5;

    // Valley low frequency bed
    valleyLow = LPF.ar(BrownNoise.ar(0.35), 200 + (freq * 0.3));
    valleyLow = valleyLow * LFNoise2.kr(0.2).range(0.6, 1.0);
    sig = sig + (valleyLow * (0.3 + (valley * 0.7)));

    // Dawn brightness - subtle high partials
    dawnBright = HPF.ar(PinkNoise.ar(0.15), 3000);
    dawnBright = dawnBright * LFNoise2.kr(1 + (dawn * 2)).range(0.3, 1.0);
    sig = sig + (dawnBright * dawn * 0.5);

    // Morning chill - high frequency shimmer
    chillHigh = BPF.ar(WhiteNoise.ar(0.15), freq * 4, 0.3) * 2;
    chillHigh = chillHigh * LFNoise2.kr(2).range(0.4, 1.0);
    sig = sig + (chillHigh * chill);

    // Pitched mist tone
    sig = sig + BPF.ar(PinkNoise.ar(0.2), freq, 0.4) * 2;

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.1), 400);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_oldwinch_mist loaded".postln;
