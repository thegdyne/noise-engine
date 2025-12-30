SynthDef(\forge_oldwinch_iron, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                   filterTypeBus, envEnabledBus, envSourceBus=0,
                                   clockRateBus, clockTrigBus,
                                   midiTrigBus=0, slotIndex=0,
                                   customBus0, customBus1, customBus2, customBus3, customBus4,
                                   portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var forgeAmt, strike, blade, rust, tool;
    var trig, modes, exciter, ringTime, forgeHeat;

    // Theme params
    forgeAmt = In.kr(customBus0);
    strike = In.kr(customBus1);
    blade = In.kr(customBus2);
    rust = In.kr(customBus3);
    tool = In.kr(customBus4);

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

    // Strike trigger
    trig = Dust.ar(strike.linexp(0, 1, 1, 12));

    // Exciter - continuous + impacts
    exciter = PinkNoise.ar(0.15 * forgeAmt) + (trig * 0.5);

    // Ring time based on blade and rust
    ringTime = blade.linexp(0, 1, 0.1, 0.6) * (1 - (rust * 0.5));

    // Metal modal resonances - iron tool character
    modes = Ringz.ar(exciter, freq, ringTime, 0.3);
    modes = modes + Ringz.ar(exciter, freq * (1.5 + (tool * 0.5)), ringTime * 0.7, 0.25);
    modes = modes + Ringz.ar(exciter, freq * (2.2 + (tool * 0.8)), ringTime * 0.5, 0.2);
    modes = modes + Ringz.ar(exciter, freq * (3.1 + tool), ringTime * 0.4, 0.15 * blade);
    modes = modes + Ringz.ar(exciter, freq * (4.3 + (tool * 0.5)), ringTime * 0.3, 0.1 * blade);

    // Low resonance
    modes = modes + Ringz.ar(exciter, freq * 0.5, ringTime * 1.3, 0.2);

    sig = modes * 0.5;

    // Forge heat - crackling fire
    forgeHeat = Crackle.ar(1.5 + (forgeAmt * 0.4), 0.15 * forgeAmt);
    forgeHeat = BPF.ar(forgeHeat, 800 + (freq * 0.5), 0.4);
    sig = sig + forgeHeat;

    // Rust damping - filter and noise
    sig = LPF.ar(sig, rust.linexp(0, 1, 8000, 2000));
    sig = sig + (BPF.ar(BrownNoise.ar(0.1 * rust), freq, 0.3) * 2);

    // Continuous metal hum
    sig = sig + BPF.ar(PinkNoise.ar(0.15), freq, 0.25) * 2;

    // Continuous bed
    sig = sig + LPF.ar(BrownNoise.ar(0.08), 250);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_oldwinch_iron loaded".postln;
