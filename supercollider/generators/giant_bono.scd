/*
Giant B0N0 Generator
NLC chaotic PLL + overdriven PT2399 delay
Based on Andrew F's Nonlinear Circuits design

Signal flow: P1-P5 → Chaotic PLL + Delay → Filter → ENVELOPE → Output

From the real circuit:
- CD4046 PLL with chaos in feedback
- PT2399 delay chip (severely overdriven)
- "nutty chunks or liquid baby green"
- "1V per Couric" tuning
- Double saw at 2x freq (dirty filthy sawtooth)
- Multiple outputs: VCO, Saw, PC1, PC2, Mix

Standard params:
  - frequency: base PLL pitch (20-8000 Hz)
  - cutoff: 1-16000 Hz
  - resonance: 0.001-1.0
  - attack/decay: final VCA envelope

Custom params:
  - custom[0] courics: PLL frequency (huge range)
  - custom[1] pll_to_delay: chaos/feedback interaction
  - custom[2] delay_feedback: PT2399 feedback (into runaway)
  - custom[3] delay_time: 1ms-500ms
  - custom[4] character: nutty chunks <-> liquid green

ENV OFF = drone (continuous chaotic output)
ENV ON = clock-synced envelope gates final output
*/

SynthDef(\giantBono, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                        filterTypeBus, envEnabledBus, clockRateBus, clockTrigBus,
                        customBus0, customBus1, customBus2, customBus3, customBus4|
    var sig, env, freq, filterFreq, rq, filterType, attack, decay, amp;
    var envEnabled, clockRate, allTrigs, clockTrig;
    var courics, pllToDelay, delayFeedback, delayTime, character;
    var pllFreq, pll, vco, doubleSaw, pc1, delayed, feedback;
    var chaos1, chaos2, chaos3, chaosMix;
    
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
    courics = In.kr(customBus0);       // 0-1 -> huge freq range
    pllToDelay = In.kr(customBus1);    // 0-1 -> chaos depth
    delayFeedback = In.kr(customBus2); // 0-1 -> into runaway
    delayTime = In.kr(customBus3);     // 0-1 -> 1ms-500ms
    character = In.kr(customBus4);     // 0-1 -> chunks vs liquid
    
    // === CHAOTIC PLL ===
    
    // PLL VCO frequency - HUGE range (0.02x to 50x base freq)
    pllFreq = freq * courics.linexp(0, 1, 0.02, 50);
    
    // Multiple chaos sources (like real PLL instability)
    chaos1 = LFNoise0.kr(pllFreq * 0.1);           // Fast random
    chaos2 = SinOsc.kr(pllFreq * 0.03) * 2;        // Slow wobble
    chaos3 = LFNoise1.ar(pllFreq * 0.5) * 0.5;     // Audio-rate drift
    
    // Chaos mix - pllToDelay controls how much chaos affects everything
    chaosMix = (chaos1 + chaos2) * pllToDelay;
    
    // Feedback from delay (creates the PLL chaos loop)
    feedback = LocalIn.ar(1);
    
    // VCO with heavy modulation from chaos AND delay feedback
    vco = Pulse.ar(
        pllFreq * (1 + (chaosMix * 0.5) + (feedback * pllToDelay * 2)),
        (0.5 + (chaos1 * 0.3 * pllToDelay)).clip(0.1, 0.9)  // PWM from chaos
    );
    
    // Double saw - "dirty filthy sawtooth" at ~2x freq
    doubleSaw = Saw.ar(pllFreq * (2.01 + (chaos2 * 0.2 * pllToDelay)));
    doubleSaw = (doubleSaw * (2 + (pllToDelay * 3))).tanh;  // Overdrive the saw
    
    // PC1 - phase comparator output (XOR-like behavior)
    pc1 = (vco * doubleSaw).sign;
    
    // Mix PLL sources
    pll = (vco * 0.5) + (doubleSaw * 0.3) + (pc1 * 0.2 * pllToDelay);
    pll = pll + chaos3;  // Add audio-rate instability
    
    // === PT2399 DELAY (severely overdriven) ===
    
    // Delay time: 1ms to 500ms (full PT2399 range)
    delayed = DelayC.ar(
        pll + (feedback * delayFeedback.linexp(0, 1, 0.1, 1.5)),  // Feedback into runaway
        0.5,
        delayTime.linexp(0, 1, 0.001, 0.5) * (1 + (chaos1 * 0.1 * pllToDelay))  // Modulated delay
    );
    
    // PT2399 overdrive character - variable intensity
    delayed = (delayed * (2 + (pllToDelay * 8))).tanh;  // 2x to 10x overdrive
    delayed = delayed + (delayed.squared * 0.3);         // Asymmetric clipping
    delayed = delayed + (delayed.cubed * 0.1 * pllToDelay);  // Extra harmonics
    
    // Feedback to PLL loop
    LocalOut.ar(delayed * pllToDelay.linexp(0, 1, 0.3, 1.2));
    
    // === OUTPUT MIX ===
    
    // Mix: character controls chunks (dry/bright) vs liquid (delay/dark)
    sig = SelectX.ar(character, [
        // Chunks: more VCO, less delay, HPF
        HPF.ar((pll * 0.7) + (delayed * 0.3), 150 + (pllToDelay * 500)),
        // Liquid: more delay, LPF
        LPF.ar((pll * 0.3) + (delayed * 0.7), 3000 - (pllToDelay * 1500))
    ]);
    
    // Add some of the PC1 "burst" character
    sig = sig + (pc1 * 0.15 * (1 - character) * pllToDelay);
    
    // Stereo spread from chaos
    sig = Pan2.ar(sig, (chaos1 * 0.6).clip(-0.8, 0.8));
    
    // === FILTER ===
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    
    // === ENVELOPE AS FINAL VCA ===
    allTrigs = In.ar(clockTrigBus, 12);
    clockTrig = Select.ar(clockRate, allTrigs);
    
    env = EnvGen.ar(Env.perc(attack, decay), clockTrig);
    sig = Select.ar(envEnabled, [sig, sig * env]);
    
    sig = sig * amp;
    
    Out.ar(out, sig);
}).add;

"  ✓ giantBono loaded (chaos edition)".postln;
