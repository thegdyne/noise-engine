/*
Neon Relax Generator
Neon bulb relaxation oscillator inspired by Elektor

Signal flow: Neon Oscillator -> Glow simulation -> Filter -> ENV VCA -> Output

Custom params:
  - P1 strike_voltage: 0-1 (ionization threshold)
  - P2 maintain_voltage: 0-1 (sustain threshold)
  - P3 gas_pressure: 0-1 (affects frequency stability)
  - P4 glow_character: 0-1 (soft <-> harsh glow)
  - P5 flicker: 0-1 (instability/randomness)
*/

SynthDef(\neonRelax, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                        midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4, portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var strikeV, maintainV, pressure, glowChar, flicker;
    var osc, glow, noise, instability;
    
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
    strikeV = In.kr(customBus0);
    maintainV = In.kr(customBus1);
    pressure = In.kr(customBus2);
    glowChar = In.kr(customBus3);
    flicker = In.kr(customBus4);
    
    // === SOUND SOURCE ===
    instability = LFNoise1.kr(pressure.linexp(0, 1, 2, 20)) * flicker * 0.15;
    
    osc = LFPulse.ar(freq * (1 + instability), 0, strikeV.linlin(0, 1, 0.1, 0.5));
    glow = SinOsc.ar(freq * 0.5) * maintainV * 0.3;
    
    sig = osc + glow;
    sig = (sig * glowChar.linexp(0, 1, 1, 4)).softclip;
    
    noise = PinkNoise.ar * flicker * 0.1 * LFNoise2.kr(20).range(0, 1);
    sig = sig + noise;
    
    // === PROCESSING CHAIN ===
    sig = ~stereoSpread.(sig, 0.2, 0.35);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);  // SSOT: per-slot generator bus is 2ch
    Out.ar(out, sig);
}).add;

"  [x] neonRelax loaded".postln;
