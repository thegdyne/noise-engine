/*
PT2399 Grainy Generator
Granular noise bursts with clock sync and delay

Standard params (from Python config):
  - frequency: 0.5-80 Hz (trigger rate)
  - cutoff: 80-16000 Hz
  - resonance: 0.1-1.0 (rq, lower = more resonant)
  - attack: 0.001-0.5 s
  - decay: 0.01-2.0 s

Custom params (from pt2399_grainy.json):
  - custom[0] delay_time: 0.01-0.5 s
  - custom[1] feedback: 0.0-0.95
  - custom[2] wet_dry: 0.0-1.0

Selects trigger from master clock's 8 rate channels:
  0=x8, 1=x4, 2=x2, 3=CLK, 4=/2, 5=/4, 6=/8, 7=/16
*/

SynthDef(\pt2399Grainy, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                          customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, grain, env, trig, freeRate, filterFreq, rq, filterType, attack, decay, amp;
    var panPos, envEnabled, clockRate, allTrigs, clockTrig, freeTrig;
    var delayTime, feedback, wetDry, delayed, dry;
    
    // Read standard params - receiving real values directly
    freeRate = In.kr(freqBus);       // Already 0.5-80 Hz
    filterFreq = In.kr(cutoffBus);   // Already 80-16000 Hz
    rq = In.kr(resBus);              // Already 0.1-1.0
    attack = In.kr(attackBus);       // Already 0.001-0.5 s
    decay = In.kr(decayBus);         // Already 0.01-2.0 s
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params - real values from JSON config
    delayTime = In.kr(customBus0);   // 0.01-0.5 s
    feedback = In.kr(customBus1);    // 0.0-0.95
    wetDry = In.kr(customBus2);      // 0.0-1.0
    
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
    dry = Pan2.ar(sig, panPos);
    
    // PT2399-style delay with feedback
    delayed = CombL.ar(dry, 0.5, delayTime, feedback * 4);
    
    // Wet/dry mix
    sig = (dry * (1 - wetDry)) + (delayed * wetDry);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ pt2399Grainy loaded".postln;
