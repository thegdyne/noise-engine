/*
FM Generator
Frequency modulation synthesis with multiple algorithms

Signal flow: P1-P5 → Operators → Algorithm → Filter → ENVELOPE → Output

Standard params:
  - frequency: carrier pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] ratio: 0.5-8.0 (modulator:carrier ratio)
  - custom[1] index: 0-20 (modulation depth)
  - custom[2] index_env: 0-1 (index envelope amount - decay)
  - custom[3] algorithm: 0-7 discrete (operator routing)
  - custom[4] feedback: 0-1 (operator self-feedback)

ENV OFF = drone (continuous FM output)
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\fm, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                 filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                 customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envSource, clockRate, allTrigs, clockTrig, allMidiTrigs, midiTrig, trig;
    var ratio, index, indexEnv, algorithm, feedback;
    var modFreq, car, mod1, mod2, fb, indexMod;
    var alg0, alg1, alg2, alg3, alg4, alg5, alg6, alg7;
    
    // Read standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);  // 0=OFF, 1=CLK, 2=MIDI
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params
    ratio = In.kr(customBus0);        // 0.5-8.0
    index = In.kr(customBus1);        // 0-20
    indexEnv = In.kr(customBus2);     // 0-1
    algorithm = In.kr(customBus3);    // 0-7 discrete
    feedback = In.kr(customBus4);     // 0-1
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Modulator frequency
    modFreq = freq * ratio;
    
    // Index modulation (envelope that decays)
    // Use a free-running decay for continuous modulation character
    indexMod = LFSaw.kr(0.5, 1).range(0, 1).pow(2);
    indexMod = (indexMod * indexEnv) + (1 - indexEnv);  // Blend with static
    
    // Feedback path
    fb = LocalIn.ar(1) * feedback * 2pi;
    
    // Modulator with feedback
    mod1 = SinOsc.ar(modFreq + fb) * modFreq * index * indexMod;
    
    // Second modulator (for complex algorithms)
    mod2 = SinOsc.ar(modFreq * 2) * modFreq * index * 0.5 * indexMod;
    
    // === ALGORITHMS ===
    
    // Alg 0: Simple 2-op (mod -> car)
    alg0 = SinOsc.ar(freq + mod1);
    
    // Alg 1: Parallel carriers
    alg1 = (SinOsc.ar(freq + mod1) + SinOsc.ar(freq * 1.5)) * 0.5;
    
    // Alg 2: Stacked mods (mod2 -> mod1 -> car)
    alg2 = SinOsc.ar(freq + SinOsc.ar(modFreq + mod2) * modFreq * index * indexMod);
    
    // Alg 3: Y-split (mod1 -> car1, mod1 -> car2)
    alg3 = (SinOsc.ar(freq + mod1) + SinOsc.ar(freq * 2 + mod1)) * 0.5;
    
    // Alg 4: Dual independent
    alg4 = (SinOsc.ar(freq + mod1) + SinOsc.ar(freq * 0.5 + mod2)) * 0.5;
    
    // Alg 5: Feedback carrier
    alg5 = SinOsc.ar(freq + mod1 + (fb * freq * 0.5));
    
    // Alg 6: Ring mod blend
    alg6 = SinOsc.ar(freq + mod1) * SinOsc.ar(freq * ratio * 0.5).range(0.5, 1);
    
    // Alg 7: Additive + FM hybrid
    alg7 = (SinOsc.ar(freq) + SinOsc.ar(freq * 2) * 0.5 + SinOsc.ar(freq + mod1 * 0.5) * 0.3) * 0.5;
    
    // Select algorithm
    sig = SelectX.ar(algorithm, [alg0, alg1, alg2, alg3, alg4, alg5, alg6, alg7]);
    
    // Send to feedback
    LocalOut.ar(sig);
    
    // Stereo spread
    sig = Pan2.ar(sig, SinOsc.kr(0.1).range(-0.3, 0.3));
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    // Clock trigger
    allTrigs = In.ar(clockTrigBus, ~clockRates.size);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    // MIDI trigger - read all 8 channels and select by slotIndex
    allMidiTrigs = In.ar(midiTrigBus, 8);
    midiTrig = Select.ar(slotIndex, allMidiTrigs);
    
    // Select trigger based on envSource: 0=none, 1=clock, 2=midi
    trig = Select.ar(envSource, [
        DC.ar(0),      // 0: OFF - no triggers
        clockTrig,     // 1: CLK - clock triggers only  
        midiTrig       // 2: MIDI - midi triggers only
    ]);
    
    // Envelope
    env = EnvGen.ar(Env.perc(attack, decay), trig);
    
    // Apply envelope only when envSource > 0, otherwise drone
    sig = sig * Select.kr(envSource > 0, [1.0, env]) * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ fm loaded".postln;
