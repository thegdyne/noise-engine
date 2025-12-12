/*
Karplus-Strong Generator
Plucked string physical model synthesis

Signal flow: P1-P5 → Exciter → Delay Loop → Filter → ENVELOPE → Output

Standard params:
  - frequency: string pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] excitation_color: 0-1 (dark noise <-> bright impulse)
  - custom[1] lowpass_coeff: 0-1 (loop filter, controls brightness/decay)
  - custom[2] feedback_gain: 0.9-0.999 (decay time)
  - custom[3] stretch_factor: 0-1 (inharmonicity, string stiffness)
  - custom[4] retrig_rate: 0.1-50 Hz (excitation rate)

ENV OFF = continuous plucked string (retriggered by internal impulse)
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\karplusStrong, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                            filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                            customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envSource, clockRate, allTrigs, clockTrig, allMidiTrigs, midiTrig, trig;
    var excColor, lpfCoeff, fbGain, stretch, retrigRate;
    var exciter, delayTime, delayed, loopSig, loopFilter;
    var internalTrig;
    
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
    excColor = In.kr(customBus0);     // 0-1
    lpfCoeff = In.kr(customBus1);     // 0-1
    fbGain = In.kr(customBus2);       // 0.9-0.999
    stretch = In.kr(customBus3);      // 0-1
    retrigRate = In.kr(customBus4);   // 0.1-50 Hz
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Internal trigger for continuous plucking
    internalTrig = Impulse.ar(retrigRate);
    
    // Delay time for pitch (with stretch for inharmonicity)
    delayTime = (1 / freq.clip(20, 8000)) * stretch.linlin(0, 1, 1, 1.02);
    delayTime = delayTime.clip(0.00005, 0.05);  // Clamp for safety
    
    // === EXCITER ===
    // Mix between filtered noise (dark) and impulse+noise (bright)
    exciter = SelectX.ar(excColor, [
        // Dark: Pink noise burst
        PinkNoise.ar * EnvGen.ar(Env.perc(0.001, 0.02), internalTrig),
        // Bright: Impulse + white noise
        (Impulse.ar(0) + (WhiteNoise.ar * 0.7)) * EnvGen.ar(Env.perc(0.0001, 0.01), internalTrig)
    ]);
    
    // === DELAY LOOP (Karplus-Strong) ===
    loopSig = LocalIn.ar(1);
    
    // Delay line
    delayed = DelayC.ar(
        exciter + loopSig,
        0.05,
        delayTime
    );
    
    // Loop filter (string damping) - lowpass in feedback
    loopFilter = LPF.ar(delayed, lpfCoeff.linexp(0, 1, 500, 12000));
    
    // Apply feedback gain (controls decay)
    loopFilter = loopFilter * fbGain;
    
    // Feed back into loop
    LocalOut.ar(loopFilter);
    
    // Use delayed signal as output
    sig = delayed;
    
    // Slight stereo spread
    sig = Pan2.ar(sig, LFNoise1.kr(0.3).range(-0.2, 0.2));
    
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
    sig = sig * Select.kr(envSource > 0, [1.0, env]) * amp * 2;  // Boost because KS can be quiet
    
    Out.ar(out, sig);
}).add;

"  ✓ karplusStrong loaded".postln;
