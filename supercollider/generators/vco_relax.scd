/*
VCO Relax Generator
XR2206/MAX038 style relaxation oscillator

Signal flow: P1-P5 → Oscillator → Filter → ENVELOPE → Output

Standard params:
  - frequency: base oscillator pitch (20-8000 Hz)
  - cutoff: 80-16000 Hz
  - resonance: 0.1-1.0
  - attack: 0.0001-0.5 s (final VCA attack)
  - decay: 0.0001-30 s (final VCA decay)

Custom params:
  - custom[0] timing_current: 0-1 (charge rate, affects freq)
  - custom[1] timing_capacitance: 0-1 (frequency range multiplier)
  - custom[2] vco_control: 0-1 (FM/vibrato depth)
  - custom[3] waveform_select: 0-2 (tri/saw/pulse)
  - custom[4] symmetry: 0-1 (pulse duty cycle)

ENV OFF = drone (continuous output)
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\vcoRelax, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                       filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                       midiTrigBus=0, slotIndex=0,
                       customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envSource, clockRate, allTrigs, clockTrig, allMidiTrigs, midiTrig, trig;
    var timingCurrent, timingCap, vcoControl, waveform, symmetry;
    var baseFreq, tri, saw, pulse;
    
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
    timingCurrent = In.kr(customBus0);   // 0-1
    timingCap = In.kr(customBus1);       // 0-1
    vcoControl = In.kr(customBus2);      // 0-1 (FM depth)
    waveform = In.kr(customBus3);        // 0-2 (tri/saw/pulse)
    symmetry = In.kr(customBus4);        // 0-1 (duty cycle)
    
    // === SOUND SOURCE (runs continuously) ===
    
    // Frequency from base freq + current source + capacitor
    baseFreq = freq * timingCurrent.linexp(0, 1, 0.25, 4) * timingCap.linexp(0, 1, 0.5, 2);
    
    // VCO modulation (vibrato/FM)
    baseFreq = baseFreq * (1 + (SinOsc.kr(5) * vcoControl * 0.3));
    
    // Core waveforms (relaxation oscillator outputs)
    tri = LFTri.ar(baseFreq);
    saw = LFSaw.ar(baseFreq);
    pulse = LFPulse.ar(baseFreq, 0, symmetry.linlin(0, 1, 0.1, 0.9)) * 2 - 1;
    
    // Waveform crossfade (0=tri, 1=saw, 2=pulse)
    sig = SelectX.ar(waveform, [tri, saw, pulse]);
    
    // Relaxation character - slight instability/jitter
    sig = sig + (LFNoise1.ar(baseFreq * 0.1) * 0.02);
    
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

"  ✓ vcoRelax loaded".postln;
