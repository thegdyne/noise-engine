// sunken-temple/VoidChant — Lightweight end-stage generator
/*
VOIDCHANT Generator
Ghostly spectral vocals echoing through ruins

Features:
  - Formant-based vocal tones
  - Hollow resonant harmonics
  - Drifting pitch
  - Ethereal chorus

Custom params:
  - P1 choir: Voice count/blend
  - P2 hollow: Formant depth
  - P3 drift: Pitch wandering
  - P4 ghost: Spectral doubling
  - P5 prayer: Ritual pulse
*/

SynthDef(\voidchant, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var choir, hollow, drift, ghost, prayer;
    var voiceSig, formants, driftMod, ghostSig, prayerMod;

    freq = In.kr(freqBus);

    choir = p[0];
    choir = Lag.kr(choir, 0.1);
    hollow = p[1];
    hollow = Lag.kr(hollow, 0.1);
    drift = p[2];
    drift = Lag.kr(drift, 0.2);
    ghost = p[3];
    ghost = Lag.kr(ghost, 0.1);
    prayer = p[4];
    prayer = Lag.kr(prayer, 0.1);

    // Pitch drift
    driftMod = LFNoise2.kr(0.3 + (drift * 0.5)).range(1 - (drift * 0.03), 1 + (drift * 0.03));

    // Prayer rhythm modulation
    prayerMod = LFTri.kr(0.5 + (prayer * 0.5)).range(0.6, 1) * (1 - prayer) + prayer;

    // === VOICE SOURCE ===
    // Pulse wave for vocal-like harmonics
    voiceSig = Pulse.ar(freq * driftMod, 0.3 + (LFNoise1.kr(2).range(0, 0.2)));
    voiceSig = voiceSig + (Pulse.ar(freq * 1.002 * driftMod, 0.35) * choir * 0.5);
    voiceSig = voiceSig + (Pulse.ar(freq * 0.998 * driftMod, 0.25) * choir * 0.5);

    // === FORMANTS (vowel-like) ===
    // "Ah" / "Oh" formants
    formants = BPF.ar(voiceSig, 600 * (1 + (hollow * 0.5)), 0.15) * 2;
    formants = formants + (BPF.ar(voiceSig, 1000, 0.2) * (1 - hollow));
    formants = formants + (BPF.ar(voiceSig, 2500, 0.3) * 0.5);

    // Hollow depth - shifts formants down
    formants = formants + (BPF.ar(voiceSig, 300, 0.1) * hollow * 2);

    voiceSig = formants * 0.5;

    // === GHOST (ethereal doubling) ===
    ghostSig = DelayL.ar(voiceSig, 0.1, LFNoise2.kr(0.5).range(0.02, 0.05));
    ghostSig = ghostSig + DelayL.ar(voiceSig, 0.1, LFNoise2.kr(0.4).range(0.03, 0.07));
    ghostSig = HPF.ar(ghostSig, 400);
    voiceSig = voiceSig + (ghostSig * ghost * 0.5);

    // === REVERB (spectral space) ===
    voiceSig = voiceSig + (CombL.ar(voiceSig, 0.5, 0.13, 3) * 0.3);
    voiceSig = voiceSig + (CombL.ar(voiceSig, 0.5, 0.19, 2.5) * 0.25);

    // Prayer modulation
    voiceSig = voiceSig * prayerMod;

    sig = voiceSig * 0.4;
    sig = sig.tanh;

    sig = ~stereoSpread.(sig, 0.35, 0.15);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] voidchant loaded".postln;
