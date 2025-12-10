/*
Test Synth Generator
Pulse + noise with clock sync

Selects trigger from master clock's 8 rate channels:
  0=x8, 1=x4, 2=x2, 3=CLK, 4=/2, 5=/4, 6=/8, 7=/16
*/

SynthDef(\testSynth, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus, 
                       filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp;
    var env, envEnabled, clockRate, allTrigs, trig;
    
    // Read params
    freq = In.kr(freqBus).linexp(0, 1, 50, 2000);
    filterFreq = In.kr(cutoffBus).linexp(0, 1, 80, 16000);
    rq = In.kr(resBus).linlin(0, 1, 1, 0.1);
    attack = In.kr(attackBus).linexp(0, 1, 0.001, 1);
    decay = In.kr(decayBus).linexp(0, 1, 0.001, 4);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read all 8 clock trigger channels
    allTrigs = In.ar(clockTrigBus, 8);
    
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
    sig = Select.ar(filterType, [
        RLPF.ar(sig, filterFreq, rq),
        RHPF.ar(sig, filterFreq, rq),
        BPF.ar(sig, filterFreq, rq)
    ]);
    
    sig = sig * env * amp * 0.15;
    
    Out.ar(out, sig ! 2);
}).add;

"  ✓ testSynth loaded".postln;
