/*
Test Synth Generator
Pulse + noise with clock sync

NOTE: Current GENERATOR_PARAMS config is optimized for pt2399-style trigger rates.
Test synth interprets frequency as oscillator pitch, so low values (0.5-80 Hz) 
will produce very low bass tones. This is a known limitation - future work will
add per-generator parameter overrides.

Receives real parameter values from Python:
  - frequency: 0.5-80 Hz (used as oscillator pitch - will be low!)
  - cutoff: 80-16000 Hz  
  - resonance: 0.1-1.0 (rq, lower = more resonant)
  - attack: 0.001-0.5 s
  - decay: 0.01-2.0 s

Custom params: none (test_synth.json has empty custom_params)

Selects trigger from master clock's 8 rate channels:
  0=x8, 1=x4, 2=x2, 3=CLK, 4=/2, 5=/4, 6=/8, 7=/16
*/

SynthDef(\testSynth, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus, 
                       filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp;
    var env, envEnabled, clockRate, allTrigs, trig;
    
    // Read params - now receiving real values directly
    freq = In.kr(freqBus);           // Already in Hz (0.5-80)
    filterFreq = In.kr(cutoffBus);   // Already 80-16000 Hz
    rq = In.kr(resBus);              // Already 0.1-1.0
    attack = In.kr(attackBus);       // Already 0.001-0.5 s
    decay = In.kr(decayBus);         // Already 0.01-2.0 s
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read all 8 clock trigger channels
    allTrigs = In.ar(clockTrigBus, 13);
    
    // Select the trigger for our rate
    trig = Select.ar(clockRate, allTrigs);
    
    // Envelope
    env = Select.ar(envEnabled, [
        DC.ar(1.0),  // ENV OFF: drone
        EnvGen.ar(Env.perc(attack, decay), trig)  // ENV ON: triggered
    ]);
    
    // Sound source
    sig = Pulse.ar(freq, 0.5, 0.3) + PinkNoise.ar(0.2);
    
    // Filter
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    sig = sig * env * amp * 0.15;
    
    Out.ar(out, sig ! 2);
}).add;

"  ✓ testSynth loaded".postln;
