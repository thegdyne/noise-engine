// amber-threshold/ColdShadow — Lightweight end-stage generator
/*
COLDSHADOW Generator
Icy blue undertones, contrasting darkness

Features:
  - Cold high-frequency shimmer
  - Deep shadow resonance
  - Slow creeping movement
  - Void-like emptiness

Custom params:
  - P1 chill: Icy texture
  - P2 dark: Shadow depth
  - P3 creep: Movement rate
  - P4 breath: Air movement
  - P5 void: Emptiness
*/

SynthDef(\coldshadow, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var chill, dark, creep, breath, void;
    var trig, chillSig, darkSig, breathSig, voidSig;
    var creepMod;

    freq = In.kr(freqBus);

    chill = p[0];
    chill = Lag.kr(chill, 0.1);
    dark = p[1];
    dark = Lag.kr(dark, 0.2);
    creep = p[2];
    creep = Lag.kr(creep, 0.2);
    breath = p[3];
    breath = Lag.kr(breath, 0.1);
    void = p[4];
    void = Lag.kr(void, 0.2);

    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // Creeping modulation
    creepMod = LFNoise2.kr(0.1 + (creep * 0.3)).range(0.9, 1.1);

    // === CHILL (icy high frequencies) ===
    chillSig = SinOsc.ar(freq * 3 * creepMod);
    chillSig = chillSig + (SinOsc.ar(freq * 4.01 * creepMod) * 0.5);
    chillSig = chillSig * LFNoise1.kr(2 + (chill * 5)).range(0.2, 1);
    chillSig = HPF.ar(chillSig, 1500);
    // Icy shimmer
    chillSig = chillSig + (Resonz.ar(PinkNoise.ar, 4000, 0.02) * chill * 0.3);
    chillSig = chillSig * chill * 0.3;

    // === DARK (low shadow) ===
    darkSig = SinOsc.ar(freq * 0.5 * creepMod);
    darkSig = darkSig + (SinOsc.ar(freq * 0.75) * 0.4);  // Minor 3rd
    darkSig = LPF.ar(darkSig, 300);
    darkSig = darkSig * LFTri.kr(0.08).range(0.5, 1);
    darkSig = darkSig * dark * 0.4;

    // === BREATH (cold air) ===
    breathSig = BPF.ar(PinkNoise.ar, 600 * LFNoise2.kr(0.3).range(0.7, 1.4), 0.3);
    breathSig = breathSig * LFNoise1.kr(0.5 + breath).range(0.2, 1);
    breathSig = breathSig * breath * 0.3;

    // === VOID (empty resonance) ===
    voidSig = Resonz.ar(BrownNoise.ar * 0.5, freq, 0.01);
    voidSig = CombL.ar(voidSig, 1, 0.7, void * 5);
    voidSig = voidSig * void * 0.4;

    // === MIX ===
    sig = chillSig + darkSig + breathSig + voidSig;
    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.4, 0.15);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] coldshadow loaded".postln;
