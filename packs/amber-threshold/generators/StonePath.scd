// amber-threshold/StonePath — Lightweight end-stage generator
/*
STONEPATH Generator
Dry footsteps on ancient flagstones

Features:
  - Hard stone impacts
  - Grit and gravel texture
  - Chamber reverb
  - Variable weight/pace

Custom params:
  - P1 steps: Step rate
  - P2 stone: Surface hardness
  - P3 grit: Loose material
  - P4 hall: Echo space
  - P5 weight: Impact heaviness
*/

SynthDef(\stonepath, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var steps, stone, grit, hall, weight;
    var stepTrig, stepSig, gritSig, stoneSig;
    var stepEnv, stepRate;

    freq = In.kr(freqBus);

    steps = p[0];
    steps = Lag.kr(steps, 0.1);
    stone = p[1];
    stone = Lag.kr(stone, 0.1);
    grit = p[2];
    grit = Lag.kr(grit, 0.05);
    hall = p[3];
    hall = Lag.kr(hall, 0.1);
    weight = p[4];
    weight = Lag.kr(weight, 0.1);

    // Step rhythm
    stepRate = 1 + (steps * 2);
    stepTrig = Impulse.ar(stepRate * LFNoise1.kr(0.5).range(0.85, 1.15));

    // === STONE (hard impact) ===
    stepEnv = EnvGen.ar(Env.perc(0.001, 0.08 + (weight * 0.05)), stepTrig);
    stoneSig = WhiteNoise.ar * stepEnv;
    stoneSig = BPF.ar(stoneSig, 800 + (stone * 600), 0.3);
    // Hard click
    stoneSig = stoneSig + (
        HPF.ar(WhiteNoise.ar, 2000) *
        EnvGen.ar(Env.perc(0.001, 0.01), stepTrig) * stone
    );
    stoneSig = stoneSig * stone * 0.5;

    // === WEIGHT (low thud) ===
    stepSig = SinOsc.ar(freq * 0.5 * TRand.ar(0.9, 1.1, stepTrig));
    stepSig = stepSig * EnvGen.ar(Env.perc(0.01, 0.1 + (weight * 0.1)), stepTrig);
    stepSig = LPF.ar(stepSig, 200);
    stepSig = stepSig * weight * 0.4;

    // === GRIT (loose material) ===
    gritSig = Dust.ar(grit * 100 * EnvGen.ar(Env.perc(0.01, 0.15), stepTrig));
    gritSig = BPF.ar(gritSig + (PinkNoise.ar * 0.3), 2500, 0.4);
    gritSig = gritSig * grit * 0.3;

    // === MIX ===
    sig = stoneSig + stepSig + gritSig;

    // === HALL (chamber echo) ===
    sig = sig + (CombL.ar(sig, 0.3, 0.12, hall * 2) * hall * 0.4);
    sig = sig + (CombL.ar(sig, 0.3, 0.19, hall * 1.5) * hall * 0.3);
    sig = sig + (CombL.ar(sig, 0.3, 0.07, hall * 1) * hall * 0.2);

    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.25, 0.2);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] stonepath loaded".postln;
