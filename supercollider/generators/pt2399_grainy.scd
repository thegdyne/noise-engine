/*
PT2399 Grainy Generator
Granular noise bursts with clock sync

Receives real parameter values from Python:
  - frequency: 0.5-80 Hz (trigger rate)
  - cutoff: 80-16000 Hz
  - resonance: 0.1-1.0 (rq, lower = more resonant)
  - attack: 0.001-0.5 s
  - decay: 0.01-2.0 s

Selects trigger from master clock's 8 rate channels:
  0=x8, 1=x4, 2=x2, 3=CLK, 4=/2, 5=/4, 6=/8, 7=/16
*/

SynthDef(\pt2399Grainy, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus|
    var sig, grain, env, trig, freeRate, filterFreq, rq, filterType, attack, decay, amp;
    var panPos, envEnabled, clockRate, allTrigs, clockTrig, freeTrig;
    
    // Read params - now receiving real values directly
    freeRate = In.kr(freqBus);       // Already 0.5-80 Hz
    filterFreq = In.kr(cutoffBus);   // Already 80-16000 Hz
    rq = In.kr(resBus);              // Already 0.1-1.0
    attack = In.kr(attackBus);       // Already 0.001-0.5 s
    decay = In.kr(decayBus);         // Already 0.01-2.0 s
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Free-running trigger
    freeTrig = Impulse.ar(freeRate);
    
    // Read all 8 clock trigger channels, select one
    allTrigs = In.ar(clockTrigBus, 8);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    // Select trigger source
    trig = Select.ar(envEnabled, [
        freeTrig,   // ENV OFF: free-running
        clockTrig   // ENV ON: clock-synced
    ]);
    
    // Envelope
    env = EnvGen.ar(Env.perc(attack, decay), trig);
    
    // Noise source
    grain = WhiteNoise.ar(0.7);
    sig = grain * env;
    
    // Filter
    sig = Select.ar(filterType, [
        RLPF.ar(sig, filterFreq, rq),
        RHPF.ar(sig, filterFreq, rq),
        BPF.ar(sig, filterFreq, rq)
    ]);
    
    // Saturation
    sig = (sig * 2).tanh * 0.6;
    
    // Random pan per grain
    panPos = TRand.ar(-1.0, 1.0, trig);
    sig = Pan2.ar(sig, panPos);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ pt2399Grainy loaded".postln;
