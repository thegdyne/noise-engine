// core/capsense — Lightweight end-stage generator
/*
CapSense Generator
Capacitive touch sensor inspired relaxation oscillator

Signal flow: Relaxation Osc -> Waveshaping -> Filter -> ENV VCA -> Output

Custom params:
  - P1 sensitivity: 0-1 (touch responsiveness)
  - P2 charge_rate: 0-1 (capacitor charge speed)
  - P3 discharge_curve: 0-1 (linear <-> exponential)
  - P4 body_effect: 0-1 (body capacitance simulation)
  - P5 noise_floor: 0-1 (sensor noise)
*/

SynthDef(\capsense, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var sensitivity, chargeRate, dischargeCurve, bodyEffect, noiseFloor;
    var osc, wobble, noise;

    freq = In.kr(freqBus);

    sensitivity = p[0];
    chargeRate = p[1];
    dischargeCurve = p[2];
    bodyEffect = p[3];
    noiseFloor = p[4];

    // === SOUND SOURCE ===
    wobble = LFNoise1.kr(chargeRate.linexp(0, 1, 0.5, 20)) * sensitivity * 0.1;

    osc = LFSaw.ar(freq * (1 + wobble), 0, 0.5);
    osc = osc + (LFPulse.ar(freq * 0.5 * (1 + wobble), 0, dischargeCurve.linlin(0, 1, 0.1, 0.9)) * 0.3);

    osc = (osc * (1 + (bodyEffect * 2))).tanh;

    noise = PinkNoise.ar * noiseFloor * 0.1;
    noise = noise * LFNoise2.kr(10).range(0.5, 1);

    sig = osc + noise;

    sig = ~stereoSpread.(sig, 0.3, 0.25);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] capsense loaded".postln;
