/*
PT2399 Grainy Generator
Noise with delay/chaos, envelope as final VCA

Signal flow: P1-P5 → Noise → Delay/Chaos → Filter → ENVELOPE → Output

Standard params:
  - frequency: disabled (pitch_target = DLY)
  - cutoff: 80-16000 Hz
  - resonance: 0.1-1.0
  - attack: 0.001-0.5 s (final VCA attack)
  - decay: 0.01-2.0 s (final VCA decay)

Custom params:
  - custom[0] delay_time: 0.005-5.0 s (also affects degradation)
  - custom[1] feedback: 0.0-0.95 (goes crazy at high values)
  - custom[2] wet_dry: 0.0-1.0

ENV OFF = drone (continuous output)
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\pt2399Grainy, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                          filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                          customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, grain, env, filterFreq, rq, filterType, attack, decay, amp;
    var panPos, envEnabled, clockRate, allTrigs, clockTrig;
    var delayTime, feedback, wetDry, delayed, dry;
    var degradeAmt, degraded;
    var fbSig, fbDistort, chaosAmt, pitchWobble;
    
    // Read standard params
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params
    delayTime = In.kr(customBus0);   // 0.005-5.0 s
    feedback = In.kr(customBus1);    // 0.0-0.95
    wetDry = In.kr(customBus2);      // 0.0-1.0
    
    // Degradation amount based on delay time
    degradeAmt = delayTime.linexp(0.005, 5.0, 0.01, 1);
    
    // Chaos amount from feedback
    chaosAmt = feedback.linexp(0, 0.95, 0.01, 1);
    
    // === SOUND SOURCE (runs continuously) ===
    grain = WhiteNoise.ar(0.7);
    
    // Saturation
    sig = (grain * 2).tanh * 0.6;
    
    // Random pan
    panPos = LFNoise1.kr(0.5).range(-0.5, 0.5);
    dry = Pan2.ar(sig, panPos);
    
    // === FEEDBACK PATH WITH CHAOS ===
    fbSig = LocalIn.ar(2);
    
    // Pitch wobble on feedback
    pitchWobble = LFNoise2.kr(0.5 + (chaosAmt * 3)).range(
        1 - (chaosAmt * 0.1),
        1 + (chaosAmt * 0.1)
    );
    
    // Main delay with modulated time
    delayed = DelayC.ar(dry + (fbSig * feedback.linexp(0, 0.95, 0.3, 1.5)), 5.0, 
        (delayTime * pitchWobble).clip(0.001, 5.0));
    
    // === DEGRADATION CHAIN ===
    degraded = Latch.ar(delayed, Impulse.ar(48000 / (1 + (degradeAmt * 30) + (chaosAmt * 20))));
    degraded = degraded.round(0.005 * (1 + (degradeAmt * 2) + (chaosAmt * 3)));
    
    // Distortion
    fbDistort = (degraded * (1 + (chaosAmt * 8))).tanh;
    fbDistort = fbDistort + ((fbDistort * chaosAmt * 4).fold(-1, 1) * chaosAmt);
    
    // Ring mod chaos
    fbDistort = fbDistort * (1 + (SinOsc.ar(delayTime.reciprocal * chaosAmt * 50) * chaosAmt * 0.5));
    
    // Crunchy filtering
    fbDistort = RLPF.ar(fbDistort, 
        (2000 + (chaosAmt * 6000) + (LFNoise1.kr(2) * chaosAmt * 3000)).clip(100, 16000),
        0.5 + (chaosAmt * 0.4)
    );
    
    // Noise and crackle
    fbDistort = fbDistort + (Dust.ar(50 * chaosAmt) * 0.3 * chaosAmt);
    fbDistort = fbDistort + (Crackle.ar(1.5 + (chaosAmt * 0.4)) * 0.1 * chaosAmt);
    fbDistort = fbDistort + (PinkNoise.ar(0.05) * degradeAmt * (1 + chaosAmt));
    
    // Bandwidth reduction
    degraded = LPF.ar(fbDistort, 12000 / (1 + (degradeAmt * 4) + (chaosAmt * 4)));
    degraded = HPF.ar(degraded, 20 + (chaosAmt * 100));
    
    // Mix delay with degraded
    delayed = (delayed * (1 - degradeAmt.sqrt)) + (degraded * degradeAmt.sqrt);
    delayed = (delayed * 1.5).tanh;
    
    // Send to feedback loop
    LocalOut.ar(delayed);
    
    // === WET/DRY MIX ===
    sig = (dry * (1 - wetDry)) + (delayed * wetDry);
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    // Clock trigger
    allTrigs = In.ar(clockTrigBus, 8);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    // ENV OFF = pass through (drone), ENV ON = envelope gates output
    env = EnvGen.ar(Env.perc(attack, decay), clockTrig);
    sig = Select.ar(envEnabled, [sig, sig * env]);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ pt2399Grainy loaded".postln;
