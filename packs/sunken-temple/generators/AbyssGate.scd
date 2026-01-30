// sunken-temple/AbyssGate — Lightweight end-stage generator
/*
ABYSSGATE Generator
Sub-bass rumble - something awakens below

Features:
  - Massive sub-bass foundation
  - Seismic rumble
  - Awakening presence
  - Crushing depth pressure

Custom params:
  - P1 depth: Sub frequency
  - P2 rumble: Seismic activity
  - P3 awaken: Stirring presence
  - P4 pressure: Weight/compression
  - P5 void: Empty resonance
*/

SynthDef(\abyssgate, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var depth, rumble, awaken, pressure, void;
    var subSig, rumbleSig, awakenSig, pressureSig, voidSig;
    var subOsc, driftLFO;

    freq = In.kr(freqBus);

    depth = p[0];
    depth = Lag.kr(depth, 0.3);
    rumble = p[1];
    rumble = Lag.kr(rumble, 0.1);
    awaken = p[2];
    awaken = Lag.kr(awaken, 0.2);
    pressure = p[3];
    pressure = Lag.kr(pressure, 0.2);
    void = p[4];
    void = Lag.kr(void, 0.2);

    // Glacial drift
    driftLFO = LFNoise2.kr(0.05).range(0.98, 1.02);

    // === DEPTH (sub bass) ===
    subOsc = SinOsc.ar(freq * 0.25 * driftLFO);
    subOsc = subOsc + (SinOsc.ar(freq * 0.251 * driftLFO) * 0.7);  // Slow beating
    subOsc = subOsc + (SinOsc.ar(freq * 0.125) * depth * 0.5);  // Sub-sub
    subSig = LPF.ar(subOsc, 80 + (depth * 120));
    subSig = subSig * depth * 0.6;

    // === RUMBLE (seismic) ===
    rumbleSig = LFNoise1.ar(5 + (rumble * 20));
    rumbleSig = LPF.ar(rumbleSig, 60);
    rumbleSig = rumbleSig * LFNoise1.kr(0.3).range(0.3, 1);
    // Occasional larger movement
    rumbleSig = rumbleSig + (
        LPF.ar(BrownNoise.ar, 40) *
        EnvGen.ar(Env.perc(0.5, 2), Dust.ar(rumble * 0.3)) * 2
    );
    rumbleSig = rumbleSig * rumble * 0.5;

    // === AWAKEN (presence) ===
    awakenSig = SinOsc.ar(freq * 0.5 * LFNoise2.kr(0.1).range(0.95, 1.05));
    awakenSig = awakenSig + (SinOsc.ar(freq * 0.667) * 0.4);  // Dissonant 5th
    awakenSig = awakenSig * LFPulse.kr(0.1 + (awaken * 0.2), 0, 0.3 + (awaken * 0.4)).lag(0.5);
    awakenSig = LPF.ar(awakenSig, 200 + (awaken * 300));
    awakenSig = awakenSig * awaken * 0.4;

    // === PRESSURE (compression feel) ===
    pressureSig = BrownNoise.ar;
    pressureSig = LPF.ar(pressureSig, 100);
    pressureSig = pressureSig * LFTri.kr(0.08).range(0.5, 1);
    pressureSig = pressureSig * pressure * 0.3;

    // === VOID (empty resonance) ===
    voidSig = Resonz.ar(PinkNoise.ar * 0.5, freq * 0.75, 0.01);
    voidSig = voidSig + Resonz.ar(PinkNoise.ar * 0.3, freq * 1.5, 0.01);
    voidSig = voidSig * void * 0.5;
    voidSig = CombL.ar(voidSig, 1, 0.5, void * 4);  // Long decay

    // === MIX ===
    sig = subSig + rumbleSig + awakenSig + pressureSig + voidSig;
    sig = sig.tanh;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] abyssgate loaded".postln;
