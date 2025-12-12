/*
UJT Relax Generator
NPN/UJT/PUT relaxation oscillator
Based on Elektor Magazine July/August 2011 "NPN Relaxation Oscillators" - Burkhard Kainka

Signal flow: P1-P5 → Relaxation Oscillator → Filter → ENVELOPE → Output

Models classic negative-resistance relaxation oscillators:
- RC charges toward supply voltage
- At threshold, device fires (UJT/PUT/NPN with positive feedback)
- Rapid discharge creates pulse
- Cycle repeats

Standard params:
  - frequency: base oscillator rate (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] rc_time: 0-1 (timing RC, affects base period)
  - custom[1] device_threshold: 0.2-0.9 (trigger/peak voltage ratio)
  - custom[2] supply_voltage: 0.3-1.0 (charge target, affects period)
  - custom[3] feedback_network: 0-1 (pulse width/shape)
  - custom[4] neg_resistance: 0-1 (snap action sharpness)

ENV OFF = continuous relaxation oscillation
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\ujtRelax, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envSource, clockRate, allTrigs, clockTrig, allMidiTrigs, midiTrig, trig;
    var rcTime, threshold, vcc, feedback, negRes;
    var oscFreq, ramp, comparator, discharge, pulse, sawChar;
    
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
    rcTime = In.kr(customBus0);        // 0-1
    threshold = In.kr(customBus1);     // 0.2-0.9
    vcc = In.kr(customBus2);           // 0.3-1.0
    feedback = In.kr(customBus3);      // 0-1
    negRes = In.kr(customBus4);        // 0-1
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Oscillator frequency: f = 1 / (RC * ln(Vcc / (Vcc - Vp)))
    // Simplified: RC affects period, threshold affects duty
    oscFreq = freq * rcTime.linexp(0, 1, 0.25, 4) * vcc.linlin(0.3, 1.0, 0.7, 1.3);
    oscFreq = oscFreq.clip(1, 20000);
    
    // Capacitor charging ramp (exponential-ish approach to Vcc)
    // Using LFSaw with shaping for character
    ramp = LFSaw.ar(oscFreq, 0, 0.5, 0.5);  // 0 to 1 base
    
    // Shape ramp based on supply voltage (higher = more headroom before threshold)
    ramp = ramp * vcc;
    
    // Add slight RC curve character
    sawChar = ramp.pow(vcc.linlin(0.3, 1.0, 1.2, 0.9));
    
    // Comparator: device fires at threshold
    comparator = sawChar > threshold;
    
    // Discharge pulse (the "snap" action)
    // Negative resistance controls how sharp the transition is
    discharge = Trig.ar(comparator, feedback.linlin(0, 1, 0.0001, 0.005));
    
    // Pulse character: sharper with higher negRes
    pulse = discharge * (1 + (negRes * 4)).tanh;
    
    // Add the characteristic "ping" of the discharge
    pulse = pulse + (Ringz.ar(discharge, oscFreq * 2, negRes.linlin(0, 1, 0.001, 0.01)) * negRes);
    
    // Mix: ramp character + pulse transient
    sig = (sawChar * feedback * 0.3) + (pulse * 0.7);
    
    // UJT/PUT have characteristic "click" at firing
    sig = sig + (HPF.ar(discharge, 2000) * negRes * 0.3);
    
    // Slight instability/jitter (component tolerances)
    sig = sig * (1 + (LFNoise1.ar(oscFreq * 0.1) * 0.02));
    
    // Stereo spread
    sig = Pan2.ar(sig, LFNoise1.kr(0.3).range(-0.3, 0.3));
    
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

"  ✓ ujtRelax loaded".postln;
