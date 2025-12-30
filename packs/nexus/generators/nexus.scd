SynthDef(\forge_nexus_nexus, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var op1, op2, op3, fbk, drf;
    var carrier, mod1, mod2, mod3, feedback;

    // Read custom params - 3-op cascade topology
    op1 = In.kr(customBus0);       // P1: First operator intensity (feeds OP2)
    op2 = In.kr(customBus1);       // P2: Second operator (modulates OP3, scaled by OP1)
    op3 = In.kr(customBus2);       // P3: Third operator output (feeds back to OP1)
    fbk = In.kr(customBus3);       // P4: Feedback amount OP3→OP1
    drf = In.kr(customBus4);       // P5: Drift in all operator ratios

    // Standard reads
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    ampVal = In.kr(~params[\amplitude]);

    // DSP: 3-operator cascade with feedback
    // OP1 → OP2 → OP3 with internal feedback
    
    // Ratio drift for each operator
    mod1 = 1 + (LFNoise1.kr(drf * 2 + 0.1) * drf * 0.1);
    mod2 = 2 + (LFNoise1.kr(drf * 1.7 + 0.1) * drf * 0.2);
    mod3 = 3 + (LFNoise1.kr(drf * 1.3 + 0.1) * drf * 0.3);
    
    // OP1: First modulator with self-feedback
    carrier = SinOscFB.ar(
        freq * mod1,
        fbk.linlin(0, 1, 0.1, 1.2) * op1
    ) * op1.linexp(0, 1, 0.3, 1);
    
    // OP2: Modulated by OP1, intensity scaled by op1*op2
    feedback = SinOsc.ar(
        freq * mod2,
        carrier * op1 * op2 * 4 * pi,
        op2.linexp(0, 1, 0.3, 1)
    );
    
    // OP3: Final carrier with feedback FM, modulated by OP2
    sig = SinOscFB.ar(
        freq * mod3 * [1, 1.003],
        fbk.linlin(0, 1, 0.05, 0.6) * op3
    ) * op3.linlin(0, 1, 0.3, 0.6);
    sig = sig * (1 + (feedback * op2 * 0.5));
    
    // Add fundamental for stability
    sig = sig + (SinOsc.ar(freq, carrier * op1 * pi * 0.5, 0.25));
    
    // Identity fracture: slight chorus
    sig = sig + (DelayC.ar(sig, 0.03, LFNoise1.kr(drf + 0.2).range(0.01, 0.025)) * drf * 0.3);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_nexus_nexus loaded".postln;
