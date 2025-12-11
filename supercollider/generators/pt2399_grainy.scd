/*
PT2399 Grainy Generator
Granular noise bursts with clock sync and delay

Standard params (from Python config):
  - frequency: base trigger rate (scaled by delay time)
  - cutoff: 80-16000 Hz
  - resonance: 0.1-1.0 (rq, lower = more resonant)
  - attack: 0.001-0.5 s
  - decay: 0.01-2.0 s

Custom params (from pt2399_grainy.json):
  - custom[0] delay_time: 0.005-5.0 s (also slows rate + adds degradation)
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
    var effectiveRate, degradeAmt, degraded;
    
    // Read standard params - receiving real values directly
    freeRate = In.kr(freqBus);       // Base rate (will be scaled by delay)
    filterFreq = In.kr(cutoffBus);   // Already 80-16000 Hz
    rq = In.kr(resBus);              // Already 0.1-1.0
    attack = In.kr(attackBus);       // Already 0.001-0.5 s
    decay = In.kr(decayBus);         // Already 0.01-2.0 s
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params - real values from JSON config
    delayTime = In.kr(customBus0);   // 0.005-5.0 s
    feedback = In.kr(customBus1);    // 0.0-0.95
    wetDry = In.kr(customBus2);      // 0.0-1.0
    
    // Longer delay = slower rate (like real PT2399 clock)
    // At 5ms delay: full rate, at 5s delay: rate/100
    effectiveRate = freeRate / delayTime.linexp(0.005, 5.0, 1, 100);
    
    // Degradation amount based on delay time
    // Longer delay = more aliasing/noise (like overclocked PT2399)
    degradeAmt = delayTime.linlin(0.005, 5.0, 0, 1);
    
    // Free-running trigger (scaled by delay time)
    freeTrig = Impulse.ar(effectiveRate);
    
    // Read all 8 clock trigger channels, select one
    allTrigs = In.ar(clockTrigBus, 8);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    // Select trigger source
    trig = Select.ar(envEnabled, [
        freeTrig,   // ENV OFF: free-running (affected by delay time)
        clockTrig   // ENV ON: clock-synced
    ]);
    
    // Envelope - longer decay at longer delays
    env = EnvGen.ar(Env.perc(attack, decay * (1 + (degradeAmt * 3))), trig);
    
    // Noise source
    grain = WhiteNoise.ar(0.7);
    sig = grain * env;
    
    // Filter
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // Saturation
    sig = (sig * 2).tanh * 0.6;
    
    // Random pan per grain
    panPos = TRand.ar(-1.0, 1.0, trig);
    dry = Pan2.ar(sig, panPos);
    
    // PT2399-style delay with feedback
    delayed = CombL.ar(dry, 5.0, delayTime, feedback * 4);
    
    // Degradation: sample rate reduction + bit crushing at long delays
    degraded = Latch.ar(delayed, Impulse.ar(48000 / (1 + (degradeAmt * 15))));
    degraded = degraded.round(0.01 * (1 + (degradeAmt * 0.5)));
    
    // Add some gritty noise at long delays
    degraded = degraded + (PinkNoise.ar(0.02) * degradeAmt * feedback);
    
    // Lowpass to simulate bandwidth reduction
    degraded = LPF.ar(degraded, 16000 / (1 + (degradeAmt * 6)));
    
    // Mix original delay with degraded version based on delay time
    delayed = (delayed * (1 - degradeAmt)) + (degraded * degradeAmt);
    
    // Wet/dry mix
    sig = (dry * (1 - wetDry)) + (delayed * wetDry);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ pt2399Grainy loaded".postln;
