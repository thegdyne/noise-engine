/*
Giant B0N0 Generator
NLC chaotic PLL + overdriven PT2399 delay
Based on Andrew F's Nonlinear Circuits design

Signal flow: P1-P5 → Chaotic PLL + Delay → Filter → ENVELOPE → Output

Standard params:
  - frequency: base PLL pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack: 0.0001-0.5 s (final VCA attack)
  - decay: 0.0001-30 s (final VCA decay)

Custom params:
  - custom[0] courics: 0-1 (PLL frequency, "1V per Couric")
  - custom[1] pll_to_delay: 0-1 (chaos interaction)
  - custom[2] delay_feedback: 0-1 (PT2399 feedback)
  - custom[3] delay_time: 0-1 (delay time)
  - custom[4] character: 0-1 (nutty chunks <-> liquid green)

ENV OFF = drone (continuous chaotic output)
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\giantBono, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                        customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envEnabled, clockRate, allTrigs, clockTrig;
    var courics, pllToDelay, delayFeedback, delayTime, character;
    var pllFreq, pll, delayed, feedback, chaos;
    
    // Read standard params
    freq = In.kr(freqBus);
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envEnabled = In.kr(envEnabledBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);
    
    // Read custom params
    courics = In.kr(customBus0);       // 0-1 (PLL freq mult)
    pllToDelay = In.kr(customBus1);    // 0-1 (chaos interaction)
    delayFeedback = In.kr(customBus2); // 0-1 (PT2399 feedback)
    delayTime = In.kr(customBus3);     // 0-1 (delay time)
    character = In.kr(customBus4);     // 0-1 (chunks vs liquid)
    
    // === SOUND SOURCE (runs continuously) ===
    
    // PLL VCO frequency ("1V per Couric")
    pllFreq = freq * courics.linexp(0, 1, 0.25, 4);
    
    // Chaotic modulation source
    chaos = LFNoise0.kr(pllFreq * 0.1) + SinOsc.kr(pllFreq * 0.01);
    
    // PLL VCO with instability
    pll = Pulse.ar(pllFreq * (1 + (chaos * 0.1 * pllToDelay)), 0.5);
    pll = pll + (Saw.ar(pllFreq * 2.01) * 0.3); // "dirty sawtooth" output
    
    // Feedback from delay
    feedback = LocalIn.ar(1);
    
    // Overdriven PT2399-style delay
    delayed = DelayC.ar(
        pll + (feedback * delayFeedback),
        0.5,
        delayTime.linexp(0, 1, 0.01, 0.3)
    );
    
    // PT2399 overdrive character
    delayed = (delayed * 3).tanh;
    delayed = delayed + (delayed.squared * 0.2); // Asymmetric clipping
    
    // Feedback to PLL
    LocalOut.ar(delayed * pllToDelay);
    
    // Mix output (PLL + delay)
    sig = (pll * (1 - character)) + (delayed * character);
    
    // Character filter ("nutty chunks" vs "liquid green")
    sig = SelectX.ar(character, [
        HPF.ar(sig, 200),  // Chunks: more highs
        LPF.ar(sig, 2000)  // Liquid: more lows
    ]);
    
    // Stereo spread
    sig = Pan2.ar(sig, LFNoise1.kr(0.5).range(-0.4, 0.4));
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    // Clock trigger
    allTrigs = In.ar(clockTrigBus, 12);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    // ENV OFF = pass through (drone), ENV ON = envelope gates output
    env = EnvGen.ar(Env.perc(attack, decay), clockTrig);
    sig = Select.ar(envEnabled, [sig, sig * env]);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ giantBono loaded".postln;
