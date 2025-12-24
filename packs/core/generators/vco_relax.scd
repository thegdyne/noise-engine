/*
VCO Relax Generator
Relaxation oscillator inspired by Elektor circuits

Signal flow: Relaxation Osc → Waveshaping → Filter → ENV VCA → Output

Custom params:
  - P1 charge_rate: 0-1 (capacitor charge speed)
  - P2 threshold: 0-1 (trigger threshold)
  - P3 hysteresis: 0-1 (schmitt trigger width)
  - P4 waveshape: 0-1 (triangle <-> pulse)
  - P5 sync_amount: 0-1 (hard sync depth)
*/

SynthDef(\vcoRelax, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                       customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var chargeRate, threshold, hysteresis, waveshape, syncAmount;
    var tri, pulse, syncOsc;
    
    // Standard params
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Custom params
    chargeRate = In.kr(customBus0);
    threshold = In.kr(customBus1);
    hysteresis = In.kr(customBus2);
    waveshape = In.kr(customBus3);
    syncAmount = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    tri = LFTri.ar(freq * chargeRate.linexp(0, 1, 0.5, 2));
    pulse = LFPulse.ar(freq, 0, threshold.linlin(0, 1, 0.1, 0.9));
    
    sig = SelectX.ar(waveshape, [tri, pulse]);
    
    syncOsc = SyncSaw.ar(freq, freq * syncAmount.linexp(0, 1, 1, 4)) * syncAmount;
    sig = sig + (syncOsc * 0.3);
    
    sig = (sig * (1 + (hysteresis * 2))).tanh * 0.7;
    
    // === PROCESSING CHAIN ===
    sig = ~stereoSpread.(sig, 0.3, 0.3);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);  // SSOT: per-slot generator bus is 2ch
    Out.ar(out, sig);
}).add;

"  ✓ vcoRelax loaded".postln;
