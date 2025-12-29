SynthDef(\forge_oldwinch_rampart, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                      filterTypeBus, envEnabledBus, envSourceBus=0,
                                      clockRateBus, clockTrigBus,
                                      midiTrigBus=0, slotIndex=0,
                                      customBus0, customBus1, customBus2, customBus3, customBus4,
                                      portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var ditch, bank, windAmt, age, curveAmt;
    var exciter, comb1, comb2, comb3, delayTime, feedback, curveMod;

    // Theme params
    ditch = In.kr(customBus0);
    bank = In.kr(customBus1);
    windAmt = In.kr(customBus2);
    age = In.kr(customBus3);
    curveAmt = In.kr(customBus4);

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

    // Curve modulation - rampart contour
    curveMod = LFNoise2.kr(0.1 + (curveAmt * 0.2)).range(0.97, 1.03);
    freq = freq * curveMod;

    // Wind exciter across earthworks
    exciter = PinkNoise.ar(0.3) + BrownNoise.ar(0.2);
    exciter = exciter * LFNoise2.kr(0.3 + (windAmt * 0.5)).range(0.5, 1.0);
    exciter = exciter * (0.4 + (windAmt * 0.6));

    // Delay time from frequency and ditch depth
    delayTime = freq.reciprocal * (1 + (ditch * 0.5));
    feedback = bank.linlin(0, 1, 0.3, 0.75);

    // Ditch resonances - multiple comb delays
    comb1 = CombL.ar(exciter, 0.2, delayTime.clip(0.002, 0.2), 0.5 + (age * 1.0), 0.4);
    comb2 = CombL.ar(exciter, 0.2, (delayTime * 1.5).clip(0.002, 0.2), 0.4 + (age * 0.8), 0.3);
    comb3 = CombL.ar(exciter, 0.2, (delayTime * 0.67).clip(0.002, 0.2), 0.6 + (age * 0.6), 0.35);

    sig = (comb1 + comb2 + comb3) * 0.4;

    // Bank resonance feedback
    sig = sig + CombC.ar(sig, 0.2, delayTime.clip(0.002, 0.2), feedback * 2, bank * 0.3);

    // Age weathering - filtering
    sig = LPF.ar(sig, age.linexp(0, 1, 4000, 1500));

    // Pitched earth tone
    sig = sig + BPF.ar(BrownNoise.ar(0.2), freq, 0.3) * 2;

    // Continuous bed
    sig = sig + LPF.ar(BrownNoise.ar(0.1), 200);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_oldwinch_rampart loaded".postln;
