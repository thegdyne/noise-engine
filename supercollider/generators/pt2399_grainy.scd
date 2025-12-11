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
  - custom[1] feedback: 0.0-0.95 (goes into self-oscillation at high values)
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
    var fbSig, fbDistort, chaosAmt, pitchWobble;
    
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
    effectiveRate = freeRate / delayTime.linexp(0.005, 5.0, 1, 50);
    
    // Degradation amount based on delay time
    degradeAmt = delayTime.linexp(0.005, 5.0, 0.01, 1);
    
    // Chaos amount from feedback - exponential curve for extreme high end
    chaosAmt = feedback.linexp(0, 0.95, 0.01, 1);
    
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
    env = EnvGen.ar(Env.perc(attack, decay * (1 + (degradeAmt * 4))), trig);
    
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
    
    // === FEEDBACK PATH WITH CHAOS ===
    fbSig = LocalIn.ar(2);
    
    // Pitch wobble on feedback (like tape wow/flutter, increases with feedback)
    pitchWobble = LFNoise2.kr(0.5 + (chaosAmt * 3)).range(
        1 - (chaosAmt * 0.1),
        1 + (chaosAmt * 0.1)
    );
    
    // Main delay with modulated time
    delayed = DelayC.ar(dry + (fbSig * feedback.linexp(0, 0.95, 0.3, 1.5)), 5.0, 
        (delayTime * pitchWobble).clip(0.001, 5.0));
    
    // === DEGRADATION CHAIN ===
    // Sample rate reduction - more extreme
    degraded = Latch.ar(delayed, Impulse.ar(48000 / (1 + (degradeAmt * 30) + (chaosAmt * 20))));
    
    // Bit crushing - more aggressive
    degraded = degraded.round(0.005 * (1 + (degradeAmt * 2) + (chaosAmt * 3)));
    
    // Distortion in feedback path - goes crazy at high feedback
    fbDistort = (degraded * (1 + (chaosAmt * 8))).tanh;
    fbDistort = fbDistort + ((fbDistort * chaosAmt * 4).fold(-1, 1) * chaosAmt);
    
    // Ring mod chaos at high feedback
    fbDistort = fbDistort * (1 + (SinOsc.ar(delayTime.reciprocal * chaosAmt * 50) * chaosAmt * 0.5));
    
    // Crunchy filtering that shifts with feedback
    fbDistort = RLPF.ar(fbDistort, 
        (2000 + (chaosAmt * 6000) + (LFNoise1.kr(2) * chaosAmt * 3000)).clip(100, 16000),
        0.5 + (chaosAmt * 0.4)
    );
    
    // Add gritty noise and crackle
    fbDistort = fbDistort + (Dust.ar(50 * chaosAmt) * 0.3 * chaosAmt);
    fbDistort = fbDistort + (Crackle.ar(1.5 + (chaosAmt * 0.4)) * 0.1 * chaosAmt);
    fbDistort = fbDistort + (PinkNoise.ar(0.05) * degradeAmt * (1 + chaosAmt));
    
    // Bandwidth reduction
    degraded = LPF.ar(fbDistort, 12000 / (1 + (degradeAmt * 4) + (chaosAmt * 4)));
    degraded = HPF.ar(degraded, 20 + (chaosAmt * 100));
    
    // Mix original delay with degraded version
    delayed = (delayed * (1 - degradeAmt.sqrt)) + (degraded * degradeAmt.sqrt);
    
    // Soft clip the output to tame extreme feedback
    delayed = (delayed * 1.5).tanh;
    
    // Send to feedback loop
    LocalOut.ar(delayed);
    
    // Wet/dry mix
    sig = (dry * (1 - wetDry)) + (delayed * wetDry);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ pt2399Grainy loaded".postln;
