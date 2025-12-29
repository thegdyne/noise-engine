SynthDef(\forge_robotjox_armor, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var plate, stress, dent, rust, flex;
    var exciter, modes, flexMod, rustNoise, ringTime;

    // Theme params
    plate = In.kr(customBus0);
    stress = In.kr(customBus1);
    dent = In.kr(customBus2);
    rust = In.kr(customBus3);
    flex = In.kr(customBus4);

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

    // Flex modulation - hull bending
    flexMod = LFNoise2.kr(0.3 + (flex * 0.5)).range(0.97, 1.03);
    freq = freq * flexMod;

    // Exciter - impacts and continuous vibration
    exciter = PinkNoise.ar(0.2) + (Dust.ar(dent.linexp(0, 1, 1, 15)) * 0.5);

    // Ring time based on plate thickness
    ringTime = plate.linexp(0, 1, 0.1, 0.6);

    // Metal plate modal resonances
    modes = Ringz.ar(exciter, freq, ringTime, 0.3 * stress);
    modes = modes + Ringz.ar(exciter, freq * 1.6, ringTime * 0.7, 0.25 * stress);
    modes = modes + Ringz.ar(exciter, freq * 2.3, ringTime * 0.5, 0.2 * stress);
    modes = modes + Ringz.ar(exciter, freq * 3.1, ringTime * 0.35, 0.15 * stress * plate);
    modes = modes + Ringz.ar(exciter, freq * 4.2, ringTime * 0.25, 0.1 * stress * plate);

    // Low structural resonance
    modes = modes + Ringz.ar(exciter, freq * 0.5, ringTime * 1.5, 0.25);

    sig = modes * 0.5;

    // Rust texture - surface degradation
    rustNoise = Crackle.ar(1.6 + (rust * 0.3), 0.15 * rust);
    rustNoise = BPF.ar(rustNoise, freq * 2, 0.4);
    sig = sig + rustNoise;

    // Hull vibration continuous
    sig = sig + BPF.ar(BrownNoise.ar(0.15), freq, 0.2) * 2;

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.08), 400);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_robotjox_armor loaded".postln;
