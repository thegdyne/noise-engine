// amber-threshold/RainVeil — Lightweight end-stage generator
/*
RAINVEIL Generator
Gentle rain curtain, soft atmospheric

Features:
  - Soft filtered rain noise
  - Distant diffusion
  - Trickling water
  - Misty atmosphere

Custom params:
  - P1 density: Rain amount
  - P2 soft: Gentleness
  - P3 distant: Spatial depth
  - P4 trickle: Water trickle
  - P5 mist: Atmospheric haze
*/

SynthDef(\rainveil, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var density, soft, distant, trickle, mist;
    var rainSig, trickleSig, mistSig;

    freq = In.kr(freqBus);

    density = p[0];
    density = Lag.kr(density, 0.1);
    soft = p[1];
    soft = Lag.kr(soft, 0.1);
    distant = p[2];
    distant = Lag.kr(distant, 0.2);
    trickle = p[3];
    trickle = Lag.kr(trickle, 0.1);
    mist = p[4];
    mist = Lag.kr(mist, 0.2);

    // === RAIN (soft noise) ===
    rainSig = PinkNoise.ar;
    rainSig = BPF.ar(rainSig, 2000 + (LFNoise1.kr(1).range(-300, 300)), 0.5);
    // Soft filtering
    rainSig = LPF.ar(rainSig, 4000 - (soft * 2000));
    // Intensity variation
    rainSig = rainSig * (1 + (LFNoise1.kr(0.3).range(-0.2, 0.2)));
    rainSig = rainSig * density * 0.4;

    // Distance filtering
    rainSig = LPF.ar(rainSig, LinExp.kr(distant, 0, 1, 6000, 1500));

    // === TRICKLE (water running) ===
    trickleSig = BPF.ar(PinkNoise.ar, 1200 * LFNoise2.kr(2 + trickle).range(0.7, 1.4), 0.2);
    trickleSig = trickleSig * LFNoise1.kr(3 + (trickle * 5)).range(0, 1);
    // Drip accents
    trickleSig = trickleSig + (
        SinOsc.ar(freq * 3 * TRand.ar(0.9, 1.2, Dust.ar(trickle * 10))) *
        EnvGen.ar(Env.perc(0.001, 0.05), Dust.ar(trickle * 10)) * 0.3
    );
    trickleSig = trickleSig * trickle * 0.3;

    // === MIST (atmospheric) ===
    mistSig = LPF.ar(PinkNoise.ar, 400);
    mistSig = mistSig + (BPF.ar(BrownNoise.ar, 200, 0.3) * 0.5);
    mistSig = mistSig * LFTri.kr(0.05).range(0.6, 1);
    mistSig = mistSig * mist * 0.2;

    // === MIX ===
    sig = rainSig + trickleSig + mistSig;

    // Distant reverb
    sig = sig + (CombL.ar(sig, 0.3, 0.15, distant * 2) * distant * 0.3);

    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.5, 0.25);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] rainveil loaded".postln;
