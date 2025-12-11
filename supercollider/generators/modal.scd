/*
Modal Generator
Resonant body physical model (bells, plates, strings, tubes)

Signal flow: P1-P5 → Exciter → Modal Resonators → Filter → ENVELOPE → Output

Standard params:
  - frequency: fundamental pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] material: 0-4 discrete (bell/plate/string/tube/custom)
  - custom[1] brightness: 0-1 (high mode amplitudes)
  - custom[2] decay_shape: 0-1 (mode decay ratios)
  - custom[3] density: 2-16 discrete (number of modes)
  - custom[4] retrig_rate: 0.1-50 Hz (excitation rate)

ENV OFF = continuous modal resonance (retriggered internally)
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\modal, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                    filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                    customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envEnabled, clockRate, allTrigs, clockTrig;
    var material, brightness, decayShape, density, retrigRate;
    var exciter, modes, modeRatios, internalTrig;
    
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
    material = In.kr(customBus0);     // 0-4 discrete
    brightness = In.kr(customBus1);   // 0-1
    decayShape = In.kr(customBus2);   // 0-1
    density = In.kr(customBus3);      // 2-16
    retrigRate = In.kr(customBus4);   // 0.1-50 Hz
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Internal trigger for continuous excitation
    internalTrig = Impulse.ar(retrigRate);
    
    // Exciter (noise burst)
    exciter = WhiteNoise.ar * EnvGen.ar(Env.perc(0.0001, 0.01), internalTrig);
    
    // === MODAL RESONATORS ===
    // Generate up to 16 resonant modes
    modes = Mix.fill(16, { |i|
        var modeNum = i + 1;
        var modeFreq, modeAmp, modeDecay, modeQ;
        var baseRatio;
        
        // Material-dependent mode ratios
        // 0=bell (inharmonic), 1=plate, 2=string, 3=tube, 4=custom
        // Using formulas instead of array lookup for SC compatibility
        baseRatio = Select.kr(material.round, [
            // Bell: approximate inharmonic series (based on circular membrane)
            (modeNum ** 1.85) * 0.8,
            // Plate: slightly inharmonic
            (modeNum ** 1.15),
            // String: harmonic 1, 2, 3, 4...
            (modeNum),
            // Tube: odd harmonics 1, 3, 5, 7...
            (modeNum * 2 - 1),
            // Custom: slightly stretched
            (modeNum ** 1.02)
        ]);
        
        // Mode frequency
        modeFreq = freq * baseRatio;
        modeFreq = modeFreq.clip(20, 18000);
        
        // Mode amplitude (higher modes quieter, brightness boosts them)
        modeAmp = (1 / (modeNum ** (1.5 - brightness))) * brightness.linlin(0, 1, 0.5, 1.2);
        
        // Mode decay (higher modes decay faster, decayShape controls ratio)
        modeDecay = 0.5 / (modeNum ** decayShape.linlin(0, 1, 0.3, 1.5));
        modeDecay = modeDecay.clip(0.01, 2);
        
        // Mode Q (resonance sharpness)
        modeQ = 100 + (brightness * 400);
        
        // Resonant bandpass for each mode
        Ringz.ar(
            exciter,
            modeFreq,
            modeDecay,
            modeAmp
        ) * (modeNum <= density) * 0.1
    });
    
    sig = modes;
    
    // Slight saturation for body warmth
    sig = (sig * 1.5).tanh;
    
    // Stereo spread
    sig = Pan2.ar(sig, LFNoise1.kr(0.2).range(-0.4, 0.4));
    
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

"  ✓ modal loaded".postln;
