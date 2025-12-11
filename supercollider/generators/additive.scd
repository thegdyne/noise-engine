/*
Additive Generator
Harmonic partial synthesis with spectral shaping

Signal flow: P1-P5 → Partials → Mix → Filter → ENVELOPE → Output

Standard params:
  - frequency: fundamental pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] partial_ratio: 0.5-4.0 (harmonic spacing multiplier)
  - custom[1] partial_curve: -2 to +2 (spectral shape/rolloff)
  - custom[2] num_partials: 2-16 discrete (number of harmonics)
  - custom[3] amp_env_depth: 0-1 (per-partial envelope modulation)
  - custom[4] spectral_tilt: -1 to +1 (dark <-> bright)

ENV OFF = drone (continuous additive output)
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\additive, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envEnabled, clockRate, allTrigs, clockTrig;
    var partialRatio, partialCurve, numPartials, envDepth, tilt;
    var partials;
    
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
    partialRatio = In.kr(customBus0);   // 0.5-4.0
    partialCurve = In.kr(customBus1);   // -2 to +2
    numPartials = In.kr(customBus2);    // 2-16
    envDepth = In.kr(customBus3);       // 0-1
    tilt = In.kr(customBus4);           // -1 to +1
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Generate up to 16 partials
    partials = Mix.fill(16, { |i|
        var harmonic = i + 1;
        var partialFreq, partialAmp, partialPhase;
        
        // Frequency: fundamental * harmonic * ratio spread
        partialFreq = (freq * harmonic * partialRatio.linlin(0.5, 4.0, 0.98, 1.02)).clip(20, 20000);
        
        // Amplitude: always roll off higher partials, curve controls steepness
        // partialCurve 0 = gentle 1/n rolloff, positive = steeper, negative = flatter
        partialAmp = 1 / (harmonic ** (1.5 + partialCurve));
        
        // Apply tilt (dark <-> bright bias)
        partialAmp = partialAmp * (1 + (tilt * (harmonic - 1) * 0.1));
        
        // Slight detuning per partial for richness
        partialPhase = LFNoise1.kr(0.1 + (i * 0.02)).range(-0.003, 0.003);
        
        // Per-partial amplitude modulation (envelope depth)
        partialAmp = partialAmp * (1 - (envDepth * LFNoise1.kr(0.5 + (i * 0.1)).range(0, 0.3)));
        
        // Only output if within numPartials
        SinOsc.ar(partialFreq * (1 + partialPhase)) * partialAmp * (harmonic <= numPartials)
    });
    
    // Normalize by number of partials to prevent loudness explosion
    sig = partials / numPartials.sqrt * 0.5;
    
    // Stereo spread
    sig = Pan2.ar(sig, LFNoise1.kr(0.2).range(-0.3, 0.3));
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    allTrigs = In.ar(clockTrigBus, ~clockRates.size);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    env = EnvGen.ar(Env.perc(attack, decay), clockTrig);
    sig = Select.ar(envEnabled, [sig, sig * env]);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ additive loaded".postln;
