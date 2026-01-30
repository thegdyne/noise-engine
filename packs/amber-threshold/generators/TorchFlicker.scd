// amber-threshold/TorchFlicker — Lightweight end-stage generator
/*
TORCHFLICKER Generator
Fire crackling, warm flame sounds

Features:
  - Flickering flame noise
  - Wood crackling
  - Fire roar/rush
  - Warm tonal undertone

Custom params:
  - P1 flame: Flame intensity
  - P2 crackle: Wood pops
  - P3 roar: Fire rush
  - P4 warmth: Warm tone
  - P5 gust: Wind variation
*/

SynthDef(\torchflicker, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var flame, crackle, roar, warmth, gust;
    var trig, flameSig, crackleSig, roarSig, warmSig;
    var flickerMod, gustMod;

    freq = In.kr(freqBus);

    flame = p[0];
    flame = Lag.kr(flame, 0.1);
    crackle = p[1];
    crackle = Lag.kr(crackle, 0.05);
    roar = p[2];
    roar = Lag.kr(roar, 0.1);
    warmth = p[3];
    warmth = Lag.kr(warmth, 0.1);
    gust = p[4];
    gust = Lag.kr(gust, 0.1);

    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // Flicker modulation
    flickerMod = LFNoise2.kr(8 + (flame * 10)).range(0.5, 1.2);
    // Gust modulation
    gustMod = LFNoise1.kr(0.5 + gust).range(1 - (gust * 0.3), 1 + (gust * 0.5));

    // === FLAME (flickering noise) ===
    flameSig = BPF.ar(PinkNoise.ar, 800 * flickerMod, 0.4);
    flameSig = flameSig + (BPF.ar(WhiteNoise.ar, 2000 * flickerMod, 0.3) * 0.5);
    flameSig = flameSig * flickerMod * gustMod;
    flameSig = flameSig * flame * 0.4;

    // === CRACKLE (wood pops) ===
    crackleSig = Dust.ar(crackle * 30) * WhiteNoise.ar;
    crackleSig = BPF.ar(crackleSig, 1500 + TRand.ar(0, 1000, Dust.ar(crackle * 30)), 0.2);
    // Sharp pops
    crackleSig = crackleSig + (
        Dust.ar(crackle * 15) *
        EnvGen.ar(Env.perc(0.001, 0.02), Dust.ar(crackle * 15)) * 2
    );
    crackleSig = crackleSig * crackle * 0.5;

    // === ROAR (fire rush) ===
    roarSig = BrownNoise.ar;
    roarSig = BPF.ar(roarSig, 300 * gustMod, 0.5);
    roarSig = roarSig + (LPF.ar(PinkNoise.ar, 400) * 0.3);
    roarSig = roarSig * LFNoise1.kr(2 + roar).range(0.6, 1);
    roarSig = roarSig * roar * 0.3;

    // === WARMTH (tonal) ===
    warmSig = SinOsc.ar(freq * LFNoise2.kr(0.5).range(0.98, 1.02));
    warmSig = warmSig + (SinOsc.ar(freq * 2) * 0.3);
    warmSig = LPF.ar(warmSig, 600);
    warmSig = warmSig * flickerMod * warmth * 0.3;

    // === MIX ===
    sig = flameSig + crackleSig + roarSig + warmSig;
    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.3, 0.2);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] torchflicker loaded".postln;
