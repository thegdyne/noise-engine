// Giant B0N0 - NLC chaotic PLL + overdriven delay
// Based on Andrew F's Nonlinear Circuits design
SynthDef(\giantBono, {
    |out=0, amp=0.5, gate=1,
    freq=220, cutoff=2000, res=0.5, atk=0.01, dec=0.3,
    courics=0.5, pll_to_delay=0.5, delay_feedback=0.6, delay_time=0.4, character=0.5|
    
    var pllFreq, pll, delayed, feedback, sig, env, chaos;
    
    // PLL VCO frequency ("1V per Couric")
    pllFreq = freq * courics.linexp(0, 1, 0.25, 4);
    
    // Chaotic modulation source
    chaos = LFNoise0.kr(pllFreq * 0.1) + SinOsc.kr(pllFreq * 0.01);
    
    // PLL VCO with instability
    pll = Pulse.ar(pllFreq * (1 + (chaos * 0.1 * pll_to_delay)), 0.5);
    pll = pll + (Saw.ar(pllFreq * 2.01) * 0.3); // "dirty sawtooth" output
    
    // Feedback from delay
    feedback = LocalIn.ar(1);
    
    // Overdriven PT2399-style delay
    delayed = DelayC.ar(
        pll + (feedback * delay_feedback),
        0.5,
        delay_time.linexp(0, 1, 0.01, 0.3)
    );
    
    // PT2399 overdrive character
    delayed = (delayed * 3).tanh;
    delayed = delayed + (delayed.squared * 0.2); // Asymmetric clipping
    
    // Feedback to PLL
    LocalOut.ar(delayed * pll_to_delay);
    
    // Mix output (PLL + delay)
    sig = (pll * (1 - character)) + (delayed * character);
    
    // Character filter ("nutty chunks" vs "liquid green")
    sig = SelectX.ar(character, [
        HPF.ar(sig, 200),  // Chunks: more highs
        LPF.ar(sig, 2000)  // Liquid: more lows
    ]);
    
    // Output filter
    sig = RLPF.ar(sig, cutoff, res);
    
    // Envelope
    env = EnvGen.kr(Env.asr(atk, 1, dec), gate, doneAction: 2);
    
    Out.ar(out, (sig * amp * env) ! 2);
}).add;
