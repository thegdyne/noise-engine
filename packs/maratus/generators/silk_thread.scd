// Silk Thread - Thin, precise, plucky like spider silk
// Karplus-Strong variant with delicate, airy character

SynthDef(\forge_maratus_silk_thread, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var tension, thinness, pluck, spin, shine;
    var exciter, delayTime, feedback, spinLFO;

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

    // Theme params
    tension = In.kr(customBus0);  // Affects damping and brightness
    thinness = In.kr(customBus1);  // Filter narrowness
    pluck = In.kr(customBus2);  // Attack transient
    spin = In.kr(customBus3).linlin(0, 1, 0, 0.008);  // Vibrato depth
    shine = In.kr(customBus4);  // High frequency content

    // Spin vibrato
    spinLFO = SinOsc.kr(4 + (spin * 100)) * spin;
    freq = freq * (1 + spinLFO);

    // Karplus-Strong delay time
    delayTime = 1 / freq;

    // Exciter - mix of impulse and noise based on pluck amount
    exciter = (Impulse.ar(0) * pluck) + (WhiteNoise.ar * (1 - pluck) * 0.5);
    exciter = exciter * EnvGen.ar(Env.perc(0.001, 0.01));

    // Add high frequency transient click for shine
    exciter = exciter + (HPF.ar(Impulse.ar(0) * shine, 4000) * 0.3);

    // Feedback amount based on tension (higher tension = longer sustain, brighter)
    feedback = tension.linlin(0, 1, 0.95, 0.995);

    // The string itself - comb filter with damping
    sig = CombL.ar(
        exciter,
        0.05,
        delayTime,
        tension.linexp(0, 1, 0.5, 4)  // Decay time
    );

    // Damping filter in feedback path simulation
    sig = LPF.ar(sig, tension.linexp(0, 1, 2000, 12000));

    // Thinness - narrow bandpass around fundamental
    sig = sig + (BPF.ar(sig, freq, thinness.linexp(0, 1, 0.5, 0.05)) * thinness);

    // Add shimmer harmonics for shine
    sig = sig + (HPF.ar(sig * shine, 3000) * 0.3);

    // Light stereo spread
    sig = ~stereoSpread.(sig, 0.3, 0.3);

    // Mandatory output chain
    sig = sig * 4;  // gain boost
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_maratus_silk_thread loaded".postln;
