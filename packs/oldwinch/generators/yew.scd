// oldwinch/yew — Lightweight end-stage generator
SynthDef(\forge_oldwinch_yew, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var bow, twist, ancient, resin, hollow;
    var bowNoise, bowedSig, twistMod, hollowRes, friction;

    bow = p[0];
    twist = p[1];
    ancient = p[2];
    resin = p[3];
    hollow = p[4];

    freq = In.kr(freqBus);

    // Twist modulation - gnarled trunk
    twistMod = LFNoise2.kr(0.1 + (twist * 0.3)).range(0.96, 1.04);
    freq = freq * twistMod;

    // Bow friction noise
    friction = resin.linexp(0, 1, 0.3, 0.8);
    bowNoise = BPF.ar(PinkNoise.ar(0.5), freq * 3, 0.2) * 3;
    bowNoise = bowNoise * LFNoise2.kr(5 + (resin * 10)).range(friction, 1.0);
    bowNoise = bowNoise * bow;

    // Bowed string simulation - filtered sawtooth with resonance
    bowedSig = LFSaw.ar(freq, 0, 0.3 * bow);
    bowedSig = bowedSig + LFSaw.ar(freq * 1.001, 0.5, 0.25 * bow);
    bowedSig = bowedSig + (SinOsc.ar(freq, 0, 0.2));

    // Add harmonics
    bowedSig = bowedSig + SinOsc.ar(freq * 2, 0, 0.15 * (1 - ancient));
    bowedSig = bowedSig + SinOsc.ar(freq * 3, 0, 0.1 * (1 - ancient));
    bowedSig = bowedSig + SinOsc.ar(freq * 0.5, 0, 0.2 * ancient);

    // Resonant body - comb filter
    bowedSig = bowedSig + CombL.ar(bowedSig, 0.1, freq.reciprocal.clip(0.002, 0.1), 0.2 + (hollow * 0.4), 0.3);

    sig = bowedSig + (bowNoise * 0.4);

    // Hollow trunk resonance
    hollowRes = BPF.ar(sig, freq * 0.5, 0.2 + (hollow * 0.3)) * 3;
    sig = sig + (hollowRes * hollow);

    // Ancient darkness - low pass
    sig = LPF.ar(sig, ancient.linexp(0, 1, 6000, 1500));

    // Wood body
    sig = sig + BPF.ar(BrownNoise.ar(0.1), freq, 0.3) * 2;

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.06), 300);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_oldwinch_yew loaded".postln;
