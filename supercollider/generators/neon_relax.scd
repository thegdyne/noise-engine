/*
Neon Generator
RC neon bulb relaxation oscillator
Based on Elektor Magazine November 2014 neon bulb article

Signal flow: P1-P5 → Neon Oscillator → Filter → ENVELOPE → Output

Models neon bulb behavior:
- RC charges capacitor toward supply
- At breakdown voltage (Vb), neon ionizes and conducts
- Capacitor discharges rapidly through glowing gas
- At extinguish voltage (Vd), discharge stops
- Cycle repeats with characteristic hysteresis

Standard params:
  - frequency: base oscillator rate (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] rc_time: 0-1 (timing RC constant)
  - custom[1] breakdown_v: 0.5-0.95 (ionization threshold)
  - custom[2] extinguish_v: 0.1-0.6 (de-ionization threshold)
  - custom[3] supply_voltage: 0.5-1.0 (charge headroom)
  - custom[4] hysteresis: 0-1 (Vb-Vd gap, affects pulse character)

ENV OFF = continuous neon oscillation
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\neonRelax, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envSource, clockRate, allTrigs, clockTrig, allMidiTrigs, midiTrig, trig;
    var rcTime, breakdownV, extinguishV, supplyV, hysteresis;
    var oscFreq, charge, ionized, pulse, glow, popClick;
    var hystGap, dutyApprox;
    
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
    rcTime = In.kr(customBus0);         // 0-1
    breakdownV = In.kr(customBus1);     // 0.5-0.95
    extinguishV = In.kr(customBus2);    // 0.1-0.6
    supplyV = In.kr(customBus3);        // 0.5-1.0
    hysteresis = In.kr(customBus4);     // 0-1
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Hysteresis gap affects duty cycle and character
    hystGap = (breakdownV - extinguishV).max(0.1);
    
    // Approximate duty cycle from hysteresis
    dutyApprox = 1 - (hystGap / supplyV.max(0.1)).clip(0.1, 0.9);
    
    // Oscillator frequency: period = RC * ln((V0 - Vd)/(V0 - Vb))
    // Simplified model: RC and supply affect period
    oscFreq = freq * rcTime.linexp(0, 1, 0.25, 4) * supplyV.linlin(0.5, 1.0, 0.8, 1.2);
    oscFreq = oscFreq.clip(1, 20000);
    
    // Capacitor charge/discharge cycle
    // Use pulse with variable duty for the glow period
    charge = LFSaw.ar(oscFreq, 0, 0.5, 0.5);  // Charging ramp
    
    // Ionization state (Schmidt trigger behavior with hysteresis)
    // High when voltage exceeds breakdown, low when drops below extinguish
    ionized = Lag.ar(
        (charge > breakdownV) + ((charge > extinguishV) * Delay1.ar(charge > breakdownV)),
        hystGap * 0.01 * hysteresis
    );
    
    // The "glow" - neon conducts and emits light during ionized phase
    glow = ionized * (charge.linlin(extinguishV, breakdownV, 0.5, 1));
    
    // Pulse on breakdown (the "flash")
    pulse = Trig.ar(ionized > 0.5, 0.0005 + (hysteresis * 0.002));
    
    // Characteristic neon "pop" at ionization (gas discharge transient)
    popClick = pulse * WhiteNoise.ar * EnvGen.ar(Env.perc(0.0001, 0.002));
    popClick = HPF.ar(popClick, 2000);
    
    // Mix components
    sig = (glow * 0.4) + (pulse * 0.4) + (popClick * 0.3 * hysteresis);
    
    // Add subtle ionization noise (plasma instability)
    sig = sig + (PinkNoise.ar * ionized * hysteresis * 0.05);
    
    // Warm color from neon orange glow (slight lowpass character)
    sig = LPF.ar(sig, hysteresis.linexp(0, 1, 12000, 4000));
    
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

"  ✓ neonRelax loaded".postln;
