SynthDef(\forge_block_walk_kid_shout, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                         filterTypeBus, envEnabledBus, envSourceBus=0,
                                         clockRateBus, clockTrigBus,
                                         midiTrigBus=0, slotIndex=0,
                                         customBus0, customBus1, customBus2, customBus3, customBus4,
                                         portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var joy, young, snap, echo, bounce;
    var mod1, mod2, carrier, pitchEnv, snapEnv, envTrig, formantFreq, feedback;

    // Standard bus reads
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
    amp = In.kr(~params[\amplitude]);

    // Theme params
    joy = In.kr(customBus0);        // Brightness/FM index
    young = In.kr(customBus1);      // Higher formants
    snap = In.kr(customBus2);       // Attack transient
    echo = In.kr(customBus3);       // Internal feedback
    bounce = In.kr(customBus4);     // Pitch bend

    // Trigger for envelopes
    envTrig = Select.ar(envSource, [
        DC.ar(0),
        Select.ar(clockRate.round, In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex, In.ar(midiTrigBus, 8))
    ]);

    // Pitch envelope for bounce/playful feel
    pitchEnv = EnvGen.ar(Env.perc(0.001, 0.1), envTrig) * bounce.linlin(0, 1, 0, 0.3);
    freq = freq * (1 + pitchEnv);

    // Snap transient - noise burst
    snapEnv = EnvGen.ar(Env.perc(0.001, 0.02), envTrig);
    
    // Formant frequency - young = higher
    formantFreq = freq * young.linexp(0, 1, 2, 5);

    // FM synthesis - two modulators for vocal-like quality
    mod1 = SinOsc.ar(formantFreq) * joy.linexp(0, 1, 1, 6);
    mod2 = SinOsc.ar(freq * 3.5) * joy.linexp(0, 1, 0.5, 3);
    carrier = SinOsc.ar(freq + mod1 + mod2);

    // Add snap transient
    sig = carrier + (HPF.ar(WhiteNoise.ar, 2000) * snapEnv * snap.linlin(0, 1, 0, 0.4));

    // Internal echo/feedback - short comb delay
    feedback = CombL.ar(sig * 0.3, 0.05, 0.02, echo.linlin(0, 1, 0.01, 0.2));
    sig = sig + (feedback * echo.linlin(0, 1, 0, 0.5));

    sig = sig * 0.5;
    sig = sig.tanh;

    // Output chain
    sig = ~stereoSpread.(sig, 0.3, 0.3);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_block_walk_kid_shout loaded".postln;
