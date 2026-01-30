// sunken-temple/DarkWater — Lightweight end-stage generator
/*
DARKWATER Generator
Murky flooded depths with tidal movement

Features:
  - Undulating bass tides
  - Murky filtered textures
  - Dripping from above
  - Underwater currents

Custom params:
  - P1 tide: Tidal bass movement
  - P2 murk: Sediment texture
  - P3 drip: Water drops
  - P4 current: Flow movement
  - P5 cold: Icy undertone
*/

SynthDef(\darkwater, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var tide, murk, drip, current, cold;
    var tideSig, murkSig, dripSig, currentSig, coldSig;
    var tideOsc;

    freq = In.kr(freqBus);

    tide = p[0];
    tide = Lag.kr(tide, 0.2);
    murk = p[1];
    murk = Lag.kr(murk, 0.1);
    drip = p[2];
    drip = Lag.kr(drip, 0.05);
    current = p[3];
    current = Lag.kr(current, 0.1);
    cold = p[4];
    cold = Lag.kr(cold, 0.2);

    // === TIDE (undulating bass) ===
    tideOsc = LFTri.kr(0.15 + (tide * 0.1)).range(0.7, 1.3);
    tideSig = SinOsc.ar(freq * 0.5 * tideOsc);
    tideSig = tideSig + (SinOsc.ar(freq * 0.75 * tideOsc) * 0.5);
    tideSig = LPF.ar(tideSig, 300);
    tideSig = tideSig * LFTri.kr(0.08).range(0.5, 1);
    tideSig = tideSig * tide * 0.5;

    // === MURK (sediment) ===
    murkSig = BrownNoise.ar;
    murkSig = LPF.ar(murkSig, 200 + (murk * 300));
    murkSig = murkSig * LFNoise1.kr(0.5 + (murk * 2)).range(0.3, 1);
    murkSig = murkSig * murk * 0.4;

    // === DRIP (water drops) ===
    dripSig = SinOsc.ar(
        freq * 4 * TRand.kr(0.8, 1.5, Dust.kr(drip * 8)),
        0,
        EnvGen.ar(Env.perc(0.001, 0.1), Dust.ar(drip * 8))
    );
    // Splash ripple
    dripSig = dripSig + (
        BPF.ar(WhiteNoise.ar, 2000, 0.3) *
        EnvGen.ar(Env.perc(0.001, 0.05), Dust.ar(drip * 6)) * 0.3
    );
    dripSig = CombL.ar(dripSig, 0.2, 0.08, 0.5);  // Ripple echo
    dripSig = dripSig * drip * 0.5;

    // === CURRENT (flow) ===
    currentSig = PinkNoise.ar;
    currentSig = BPF.ar(currentSig, 400 * LFNoise2.kr(0.3).range(0.5, 2), 0.3);
    currentSig = currentSig * LFNoise1.kr(current * 3 + 0.5).range(0, 1);
    currentSig = currentSig * current * 0.3;

    // === COLD (icy tone) ===
    coldSig = SinOsc.ar(freq * 2 * LFNoise2.kr(0.2).range(0.99, 1.01));
    coldSig = coldSig + (SinOsc.ar(freq * 3.01) * 0.3);
    coldSig = HPF.ar(coldSig, 500);
    coldSig = coldSig * LFTri.kr(0.1).range(0.2, 0.8);
    coldSig = coldSig * cold * 0.2;

    // === MIX ===
    sig = tideSig + murkSig + dripSig + currentSig + coldSig;
    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.25, 0.2);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] darkwater loaded".postln;
