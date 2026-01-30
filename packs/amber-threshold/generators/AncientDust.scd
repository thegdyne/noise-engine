// amber-threshold/AncientDust — Lightweight end-stage generator
/*
ANCIENTDUST Generator
Particles dancing in light beams

Features:
  - Granular particle texture
  - Sparkle when catching light
  - Swirling movement
  - Settling density

Custom params:
  - P1 swirl: Movement pattern
  - P2 sparkle: Light reflections
  - P3 thick: Particle density
  - P4 settle: Falling/settling
  - P5 age: Ancient texture
*/

SynthDef(\ancientdust, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var swirl, sparkle, thick, settle, age;
    var trig, dustSig, sparkleSig, settleSig, ageSig;
    var swirlMod;

    freq = In.kr(freqBus);

    swirl = p[0];
    swirl = Lag.kr(swirl, 0.1);
    sparkle = p[1];
    sparkle = Lag.kr(sparkle, 0.05);
    thick = p[2];
    thick = Lag.kr(thick, 0.1);
    settle = p[3];
    settle = Lag.kr(settle, 0.1);
    age = p[4];
    age = Lag.kr(age, 0.2);

    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // Swirling modulation
    swirlMod = LFNoise2.kr(0.5 + (swirl * 2)).range(0.5, 1.5);

    // === DUST (granular base) ===
    dustSig = Dust.ar(thick * 200 + 50);
    dustSig = BPF.ar(dustSig, 2000 * swirlMod, 0.3);
    dustSig = dustSig + (Dust.ar(thick * 100) * BPF.ar(PinkNoise.ar, 3000, 0.2) * 0.5);
    dustSig = dustSig * thick * 0.4;

    // === SPARKLE (light catching) ===
    sparkleSig = Dust.ar(sparkle * 30);
    sparkleSig = sparkleSig * SinOsc.ar(freq * 4 * TRand.ar(0.9, 1.5, Dust.ar(sparkle * 30)));
    sparkleSig = HPF.ar(sparkleSig, 3000);
    sparkleSig = sparkleSig + (
        Resonz.ar(Dust.ar(sparkle * 50), 5000, 0.02) * 3
    );
    sparkleSig = sparkleSig * sparkle * 0.3;

    // === SETTLE (falling particles) ===
    settleSig = Dust.ar(settle * 40) * BrownNoise.ar;
    settleSig = LPF.ar(settleSig, 1000);
    settleSig = settleSig * LFNoise1.kr(settle + 0.5).range(0.3, 1);
    settleSig = settleSig * settle * 0.3;

    // === AGE (ancient texture) ===
    ageSig = Crackle.ar(1.5 + (age * 0.4)) * age * 0.05;
    ageSig = ageSig + (BPF.ar(PinkNoise.ar, 400, 0.2) * age * 0.1);

    // === MIX ===
    sig = dustSig + sparkleSig + settleSig + ageSig;

    // Swirl spatial movement
    sig = sig + (DelayL.ar(sig, 0.1, LFNoise2.kr(swirl + 0.5).range(0.01, 0.05)) * swirl * 0.3);

    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.5, 0.3);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] ancientdust loaded".postln;
