// moss_root/canopy_tone — Lightweight end-stage generator
SynthDef(\forge_moss_root_canopy_tone, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var glow, flutter, gaps, hue, air;
    var fmCarrier, fmMod, tremolo, gapMod, airNoise, warmth;

    freq = In.kr(freqBus);

    glow = p[0];
    flutter = p[1];
    gaps = p[2];
    hue = p[3];
    air = p[4];

    // FM synthesis for shimmering tones
    fmMod = SinOsc.ar(freq * 2) * glow.linlin(0, 1, 0.5, 3);
    fmCarrier = SinOsc.ar(freq + fmMod) * 0.5;

    // Add harmonics via additional FM layer
    fmCarrier = fmCarrier + (SinOsc.ar(freq * 1.5 + (SinOsc.ar(freq * 3) * glow)) * 0.2 * glow);

    // Flutter: tremolo from leaves
    tremolo = LFTri.kr(flutter.linexp(0, 1, 2, 12)).range(
        1 - (flutter * 0.4),
        1
    );

    // Gaps: irregular amplitude modulation
    gapMod = LFNoise1.kr(gaps.linexp(0, 1, 0.5, 4)).range(
        1 - gaps,
        1
    );

    sig = fmCarrier * tremolo * gapMod;

    // Air: high frequency breath
    airNoise = HPF.ar(PinkNoise.ar, 6000) * air * 0.15;
    airNoise = airNoise * LFNoise2.kr(3).range(0.5, 1);
    sig = sig + airNoise;

    // Hue: warmth filtering (low hue = cooler, high = warmer golden)
    warmth = hue.linexp(0, 1, 6000, 2500);
    sig = LPF.ar(sig, warmth);
    // Add subtle warmth harmonics
    sig = sig + (SinOsc.ar(freq * 0.5) * hue * 0.1);

    // Gentle stereo spread
    sig = Pan2.ar(Mix(sig), SinOsc.kr(flutter.linexp(0, 1, 0.1, 0.4).max(0.001)) * 0.4);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_moss_root_canopy_tone loaded".postln;
