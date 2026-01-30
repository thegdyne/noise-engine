// amber-threshold/ThresholdHum — Lightweight end-stage generator
/*
THRESHOLDHUM Generator
Liminal doorway resonance, standing waves

Features:
  - Standing wave harmonics
  - Portal-like resonance
  - Liminal between-space feel
  - Pulsing energy

Custom params:
  - P1 standing: Standing wave
  - P2 portal: Doorway resonance
  - P3 liminal: Between-space
  - P4 pulse: Energy pulsing
  - P5 ancient: Mystery/age
*/

SynthDef(\thresholdhum, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var standing, portal, liminal, pulse, ancient;
    var standingSig, portalSig, liminalSig, pulseMod;

    freq = In.kr(freqBus);

    standing = p[0];
    standing = Lag.kr(standing, 0.1);
    portal = p[1];
    portal = Lag.kr(portal, 0.1);
    liminal = p[2];
    liminal = Lag.kr(liminal, 0.2);
    pulse = p[3];
    pulse = Lag.kr(pulse, 0.1);
    ancient = p[4];
    ancient = Lag.kr(ancient, 0.2);

    // Pulse modulation
    pulseMod = LFTri.kr(0.3 + (pulse * 0.5)).range(0.7, 1) * (1 - pulse) + (
        LFPulse.kr(0.5 + (pulse * 1), 0, 0.5).lag(0.1) * pulse
    );

    // === STANDING WAVE ===
    standingSig = SinOsc.ar(freq);
    standingSig = standingSig + (SinOsc.ar(freq * 2) * 0.5);
    standingSig = standingSig + (SinOsc.ar(freq * 3) * 0.33);
    standingSig = standingSig + (SinOsc.ar(freq * 4) * 0.25);
    // Slight detuning for standing wave effect
    standingSig = standingSig + (SinOsc.ar(freq * 1.003) * 0.3);
    standingSig = standingSig * standing * 0.3 * pulseMod;

    // === PORTAL (doorway resonance) ===
    portalSig = Resonz.ar(PinkNoise.ar, freq * 1.5, 0.02) * 5;
    portalSig = portalSig + Resonz.ar(PinkNoise.ar, freq * 2.5, 0.03) * 3;
    portalSig = portalSig + Resonz.ar(BrownNoise.ar, freq * 0.5, 0.02) * 4;
    portalSig = portalSig * portal * 0.4;

    // === LIMINAL (between-space) ===
    liminalSig = SinOsc.ar(freq * 0.5 * LFNoise2.kr(0.1).range(0.98, 1.02));
    liminalSig = liminalSig + (SinOsc.ar(freq * 0.749) * 0.5);  // Slightly off 5th
    liminalSig = liminalSig * LFNoise1.kr(0.3).range(0.5, 1);
    liminalSig = LPF.ar(liminalSig, 500);
    liminalSig = liminalSig * liminal * 0.3;

    // === ANCIENT (mystery) ===
    sig = standingSig + portalSig + liminalSig;
    sig = sig + (BPF.ar(BrownNoise.ar, 150, 0.2) * ancient * 0.15);
    sig = LPF.ar(sig, 5000 - (ancient * 2000));

    // Spatial resonance
    sig = sig + (CombL.ar(sig, 0.5, 0.23, portal * 2) * portal * 0.2);

    sig = sig.tanh;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] thresholdhum loaded".postln;
