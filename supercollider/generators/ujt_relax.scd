/*
UJT Relax Generator
Unijunction transistor relaxation oscillator

Signal flow: UJT Oscillator → Waveshaping → Filter → ENV VCA → Output

Custom params:
  - P1 peak_voltage: 0-1 (firing threshold)
  - P2 valley_voltage: 0-1 (reset threshold)
  - P3 capacitance: 0-1 (timing cap size)
  - P4 resistance: 0-1 (charge resistance)
  - P5 temperature: 0-1 (thermal drift simulation)
*/

SynthDef(\ujtRelax, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var peakV, valleyV, capacitance, resistance, temperature;
    var osc, drift, spike;
    
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
    peakV = In.kr(customBus0);
    valleyV = In.kr(customBus1);
    capacitance = In.kr(customBus2);
    resistance = In.kr(customBus3);
    temperature = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    drift = LFNoise1.kr(temperature.linexp(0, 1, 0.1, 5)) * temperature * 0.1;
    
    osc = LFSaw.ar(freq * capacitance.linexp(0, 1, 0.5, 2) * (1 + drift));
    osc = osc.linlin(-1, 1, valleyV, peakV);
    
    spike = Impulse.ar(freq * capacitance.linexp(0, 1, 0.5, 2)) * resistance * 0.5;
    spike = spike * EnvGen.ar(Env.perc(0.0001, 0.01));
    
    sig = osc + spike;
    sig = (sig * (1 + resistance)).tanh * 0.7;
    
    // === PROCESSING CHAIN ===
    sig = ~stereoSpread.(sig, 0.25, 0.3);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);  // SSOT: per-slot generator bus is 2ch
    Out.ar(out, sig);
}).add;

"  ✓ ujtRelax loaded".postln;
