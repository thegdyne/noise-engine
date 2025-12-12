/*
Test Synth Generator
Simple sine oscillator for testing signal flow - INLINE VERSION (no helpers)

Signal flow: Sine → Filter → ENV VCA → Output
*/

SynthDef(\testSynth, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
                        midiTrigBus=0, slotIndex=0,
                        customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate;
    var allTrigs, clockTrig, allMidiTrigs, midiTrig, trig, env;
    
    // Standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // === SOUND SOURCE ===
    sig = SinOsc.ar(freq) * 0.5;
    sig = Pan2.ar(sig, 0);
    
    // === FILTER (inline) ===
    sig = Select.ar(filterType, [
        RLPF.ar(sig, filterFreq, rq),
        RHPF.ar(sig, filterFreq, rq),
        BPF.ar(sig, filterFreq, rq, mul: rq.sqrt.reciprocal.min(15))
    ]);
    
    // === ENVELOPE AS FINAL VCA (inline) ===
    // Clock trigger
    allTrigs = In.ar(clockTrigBus, 13);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    // MIDI trigger
    allMidiTrigs = In.ar(midiTrigBus, 8);
    midiTrig = Select.ar(slotIndex, allMidiTrigs);
    
    // Select trigger based on envSource: 0=none, 1=clock, 2=midi
    trig = Select.ar(envSource, [
        DC.ar(0),      // 0: OFF - no triggers (drone)
        clockTrig,     // 1: CLK - clock triggers only
        midiTrig       // 2: MIDI - midi triggers only
    ]);
    
    // Envelope
    env = EnvGen.ar(Env.perc(attack, decay), trig);
    
    // Apply envelope only when envSource > 0, otherwise drone
    sig = sig * Select.kr(envSource > 0, [1.0, env]) * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ testSynth loaded (inline version)".postln;
