SynthDef(\forge_moss_root_branch_snap, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var crack, wood, echo, size, dry;
    var noise, crackEnv, woodBody, bodyFreq, delayedSig;

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
    amp = In.kr(~params[\amplitude]);

    // Custom params
    crack = In.kr(customBus0);
    wood = In.kr(customBus1);
    echo = In.kr(customBus2);
    size = In.kr(customBus3);
    dry = In.kr(customBus4);

    // Base frequency scaled by size (bigger branch = lower)
    bodyFreq = freq * size.linexp(0, 1, 2, 0.5);

    // Crack: bright noise burst with fast envelope
    crackEnv = EnvGen.ar(Env.perc(0.001, dry.linexp(0, 1, 0.08, 0.02)));
    noise = HPF.ar(WhiteNoise.ar, crack.linexp(0, 1, 2000, 8000)) * crackEnv * crack;

    // Wood body resonance: multiple modes
    woodBody = Mix([
        Ringz.ar(noise * 0.5, bodyFreq, dry.linexp(0, 1, 0.3, 0.08)) * 0.4,
        Ringz.ar(noise * 0.3, bodyFreq * 1.6, dry.linexp(0, 1, 0.25, 0.05)) * 0.3,
        Ringz.ar(noise * 0.2, bodyFreq * 2.4, dry.linexp(0, 1, 0.2, 0.04)) * 0.2
    ]) * wood;

    // Pitch bend for snap character
    sig = (noise * 0.6) + woodBody;

    // Add subtle pitched click
    sig = sig + (SinOsc.ar(bodyFreq * EnvGen.ar(Env.perc(0.001, 0.02))) * EnvGen.ar(Env.perc(0.001, 0.03)) * 0.3);

    // Forest echo: short delay with feedback
    delayedSig = CombL.ar(sig, 0.3, size.linlin(0, 1, 0.08, 0.2), echo.linlin(0, 1, 0.1, 1.5));
    sig = sig + (delayedSig * echo * 0.5);

    // Stereo spread based on echo
    sig = ~stereoSpread.(sig, 0.1, echo.linlin(0, 1, 0.2, 0.6));

    // MANDATORY output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_moss_root_branch_snap loaded".postln;
