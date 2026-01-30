// core/diode_ring — Lightweight end-stage generator
/*
Diode Ring Generator
Classic diode ring modulator based on Elektor Formant series

Signal flow: Carrier x Modulator -> Diode nonlinearity -> Filter -> ENV VCA -> Output

Custom params:
  - P1 carrier_freq: 20-2000 Hz (carrier oscillator frequency)
  - P2 modulator_freq: 0.1-1000 Hz (modulator frequency - sideband spacing)
  - P3 input_level: 0-1 (input level trim - sideband strength)
  - P4 balance: 0-1 (bridge symmetry - carrier suppression)
  - P5 carrier_leak: 0-1 (carrier leak - suppression vs bleed)
*/

SynthDef(\diodeRing, { |out, freqBus, customBus0|
    var sig;
    var p = In.kr(customBus0, 5);
    var carrierFreq, modulatorFreq, inputLevel, balance, carrierLeak;
    var carrier, modulator, ring;


    // Custom params from JSON
    carrierFreq = p[0];  // 20-2000 Hz
    modulatorFreq = p[1];  // 0.1-1000 Hz
    inputLevel = p[2];  // 0-1
    balance = p[3];  // 0-1 (bridge symmetry)
    carrierLeak = p[4];  // 0-1

    // === SOUND SOURCE ===
    // Classic ring modulator: carrier * modulator
    carrier = SinOsc.ar(carrierFreq);
    modulator = SinOsc.ar(modulatorFreq);

    // Ring modulation with balance control (carrier suppression)
    ring = carrier * modulator * inputLevel;

    // Balance controls how much carrier bleeds through (bridge asymmetry)
    // At balance=0.5, carrier is fully suppressed (perfect ring mod)
    // Away from 0.5, carrier leaks through
    sig = ring * (1 - (balance - 0.5).abs.linlin(0, 0.5, 0, 0.5));

    // Carrier leak adds direct carrier back in
    sig = sig + (carrier * carrierLeak * 0.5);

    // Soft saturation for diode character
    sig = (sig * 2).tanh * 0.7;


    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] diodeRing loaded".postln;
