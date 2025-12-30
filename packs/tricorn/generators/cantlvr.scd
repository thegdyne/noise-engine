SynthDef(\forge_tricorn_cantlvr, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var overhang, tension, steel, sway, creak;
    var exciter, modes, swayMod, creakNoise, ringTime;

    // Theme params
    overhang = In.kr(customBus0);
    tension = In.kr(customBus1);
    steel = In.kr(customBus2);
    sway = In.kr(customBus3);
    creak = In.kr(customBus4);

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

    // Sway modulation
    swayMod = SinOsc.kr(0.15 + (sway * 0.4)).range(0.97, 1.03);
    freq = freq * swayMod;

    // Exciter - continuous with dust impacts
    exciter = PinkNoise.ar(0.15) + (Dust.ar(2 + (creak * 8)) * 0.3);

    // Creak noise layer
    creakNoise = BPF.ar(
        Crackle.ar(1.5 + (creak * 0.4), 0.2),
        freq * LFNoise1.kr(2).range(1.8, 2.2),
        0.1
    ) * creak;

    exciter = exciter + creakNoise;

    // Ring time based on tension
    ringTime = tension.linexp(0, 1, 0.3, 2.0);

    // Modal resonances - cantilever beam modes
    // Mode ratios for beam: 1, 2.76, 5.4, 8.93 (approximate)
    modes = Ringz.ar(exciter, freq, ringTime, 0.3);
    modes = modes + Ringz.ar(exciter, freq * (1 + (overhang * 1.76)), ringTime * 0.7, 0.2);
    modes = modes + Ringz.ar(exciter, freq * (1 + (overhang * 4.4)), ringTime * 0.4, 0.15 * steel);
    modes = modes + Ringz.ar(exciter, freq * (1 + (overhang * 7.93)), ringTime * 0.25, 0.1 * steel);

    // Steel brightness - high frequency modes
    modes = modes + Ringz.ar(exciter, freq * 5, ringTime * 0.15, 0.08 * steel);
    modes = modes + Ringz.ar(exciter, freq * 7, ringTime * 0.1, 0.05 * steel);

    sig = modes * 0.4;

    // Add low rumble for mass
    sig = sig + (LPF.ar(BrownNoise.ar(0.1), freq * 0.5) * (1 - steel) * 0.5);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_tricorn_cantlvr loaded".postln;
