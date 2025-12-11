/*
CapSense Generator
Charge-time capacitive sensor relaxation oscillator
Based on Elektor Magazine July/August 2011 article

Signal flow: P1-P5 → Capacitive Oscillator → Filter → ENVELOPE → Output

Models the behavior of charge-time measurement where:
- iDAC charges a sensor capacitor through known current
- Comparator fires when voltage crosses threshold
- Discharge resets the cycle
- Larger capacitance = slower charge = lower frequency

Standard params:
  - frequency: base oscillator rate (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] sensor_cap: 0-1 (simulated sensor capacitance, affects ramp time)
  - custom[1] idac_current: 0-1 (charge current slope)
  - custom[2] threshold: 0.1-0.95 (comparator trigger point)
  - custom[3] measure_cycles: 1-16 discrete (resolution/averaging)
  - custom[4] noise_filter: 0-1 (environmental noise/filtering)

ENV OFF = continuous capacitive oscillation
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\capsense, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envEnabled, clockRate, allTrigs, clockTrig;
    var sensorCap, idacCurrent, threshold, cycles, noiseFilter;
    var rampFreq, ramp, comparator, pulseOut, averaged;
    var envNoise, capNoise;
    
    // Read standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params
    sensorCap = In.kr(customBus0);      // 0-1 (higher = slower)
    idacCurrent = In.kr(customBus1);    // 0-1 (higher = faster charge)
    threshold = In.kr(customBus2);      // 0.1-0.95
    cycles = In.kr(customBus3);         // 1-16 discrete
    noiseFilter = In.kr(customBus4);    // 0-1
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Effective frequency based on cap and current
    // f = I / (C * V_threshold) - simplified model
    // Higher cap = lower freq, higher current = higher freq
    rampFreq = freq * idacCurrent.linexp(0, 1, 0.25, 4) / sensorCap.linexp(0, 1, 1, 4);
    rampFreq = rampFreq.clip(1, 20000);
    
    // Capacitor voltage ramp (sawtooth represents charging)
    ramp = LFSaw.ar(rampFreq, 0, 0.5, 0.5);  // 0 to 1 ramp
    
    // Environmental noise on the "sensor" (touch noise, EMI, etc.)
    envNoise = LFNoise1.ar(100) * noiseFilter * 0.1;
    capNoise = LFNoise0.ar(rampFreq * 0.1) * noiseFilter * 0.05;
    ramp = ramp + envNoise + capNoise;
    
    // Comparator: fires when ramp crosses threshold
    comparator = (ramp > threshold);
    
    // Pulse output (the discharge transient)
    pulseOut = Trig.ar(comparator, 0.001) * 2 - 1;
    
    // Multiple measurement cycles (averaging for resolution)
    // Fixed 8 voices, use cycles param to control mix amount
    averaged = Mix.fill(8, { |i|
        var phaseShift = i / 8 * 0.1;
        var shiftedRamp = LFSaw.ar(rampFreq * (1 + (phaseShift * 0.01)), 0, 0.5, 0.5);
        (shiftedRamp > threshold).lag(0.0001) * (i < cycles)
    }) / cycles.max(1);
    
    // Mix pulse transients with filtered ramp character
    sig = (pulseOut * 0.5) + (averaged * 0.5);
    
    // Add some of the raw ramp for texture (charge curve character)
    sig = sig + (ramp * 0.2 * (1 - noiseFilter));
    
    // Noise filtering (smoothing like in real CapSense ICs)
    sig = LPF.ar(sig, noiseFilter.linexp(0, 1, 16000, 2000));
    
    // Stereo spread
    sig = Pan2.ar(sig, LFNoise1.kr(0.3).range(-0.3, 0.3));
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    allTrigs = In.ar(clockTrigBus, 12);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    env = EnvGen.ar(Env.perc(attack, decay), clockTrig);
    sig = Select.ar(envEnabled, [sig, sig * env]);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ capsense loaded".postln;
