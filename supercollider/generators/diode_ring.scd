/*
Diode Ring Generator
Classic diode ring modulator based on Elektor Formant series

Signal flow: Carrier × Modulator → Diode nonlinearity → Filter → ENV VCA → Output

Custom params:
  - P1 carrier_freq: 20-2000 Hz (carrier oscillator frequency)
  - P2 modulator_freq: 0.1-1000 Hz (modulator frequency - sideband spacing)
  - P3 input_level: 0-1 (input level trim - sideband strength)
  - P4 balance: 0-1 (bridge symmetry - carrier suppression)
  - P5 carrier_leak: 0-1 (carrier leak - suppression vs bleed)
*/

SynthDef(\diodeRing, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                        midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var carrierFreq, modulatorFreq, inputLevel, balance, carrierLeak;
    var carrier, modulator, ring;
    
    // Standard params
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Custom params from JSON
    carrierFreq = In.kr(customBus0);      // 20-2000 Hz
    modulatorFreq = In.kr(customBus1);    // 0.1-1000 Hz
    inputLevel = In.kr(customBus2);       // 0-1
    balance = In.kr(customBus3);          // 0-1 (bridge symmetry)
    carrierLeak = In.kr(customBus4);      // 0-1
    
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
    
    // === PROCESSING CHAIN ===
    sig = sig ! 2;  // Dual mono for channel strip panning
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  ✓ diodeRing loaded".postln;
