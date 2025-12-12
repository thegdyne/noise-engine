/*
CapSense Generator
Capacitive touch sensor inspired relaxation oscillator

Signal flow: Relaxation Osc → Waveshaping → Filter → ENV VCA → Output

Custom params:
  - P1 sensitivity: 0-1 (touch responsiveness)
  - P2 charge_rate: 0-1 (capacitor charge speed)
  - P3 discharge_curve: 0-1 (linear <-> exponential)
  - P4 body_effect: 0-1 (body capacitance simulation)
  - P5 noise_floor: 0-1 (sensor noise)
*/

SynthDef(\capsense, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var sensitivity, chargeRate, dischargeCurve, bodyEffect, noiseFloor;
    var osc, wobble, noise;
    
    // Standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Custom params
    sensitivity = In.kr(customBus0);
    chargeRate = In.kr(customBus1);
    dischargeCurve = In.kr(customBus2);
    bodyEffect = In.kr(customBus3);
    noiseFloor = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    wobble = LFNoise1.kr(chargeRate.linexp(0, 1, 0.5, 20)) * sensitivity * 0.1;
    
    osc = LFSaw.ar(freq * (1 + wobble), 0, 0.5);
    osc = osc + (LFPulse.ar(freq * 0.5 * (1 + wobble), 0, dischargeCurve.linlin(0, 1, 0.1, 0.9)) * 0.3);
    
    osc = (osc * (1 + (bodyEffect * 2))).tanh;
    
    noise = PinkNoise.ar * noiseFloor * 0.1;
    noise = noise * LFNoise2.kr(10).range(0.5, 1);
    
    sig = osc + noise;
    
    // === PROCESSING CHAIN ===
    sig = ~stereoSpread.(sig, 0.3, 0.25);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    
    Out.ar(out, sig);
}).add;

"  ✓ capsense loaded".postln;
