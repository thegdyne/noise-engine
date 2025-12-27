// mucus: Wet surfaces - slime, drip
SynthDef(\forge_scorn_mucus, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var slime, drip, viscous, pool, stretch;

    // Theme params
    slime = In.kr(customBus0).linlin(0, 1, 0.3, 0.9);       // P1: Slime amount
    drip = In.kr(customBus1).linlin(0, 1, 3, 20);           // P2: Drip rate
    viscous = In.kr(customBus2).linlin(0, 1, 100, 800);     // P3: Viscosity filter
    pool = In.kr(customBus3).linlin(0, 1, 0.1, 0.5);        // P4: Pool depth
    stretch = In.kr(customBus4).linlin(0, 1, 0.1, 0.6);     // P5: Stretch sounds

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

    // DSP: Slime texture - thick filtered noise
    sig = LPF.ar(BrownNoise.ar(slime * 0.5), viscous);

    // Drip sounds
    sig = sig + (Ringz.ar(Dust.ar(drip) * 0.2, freq * [2, 3, 5], 0.1) * slime * 0.4);

    // Pool - low resonance
    sig = sig + (LPF.ar(PinkNoise.ar(pool * 0.3), 300));

    // Stretch sounds - slow modulated
    sig = sig + (BPF.ar(PinkNoise.ar(stretch * 0.3), freq * LFNoise1.kr(0.3).range(1, 3), 0.2) * stretch);

    // Continuous wet presence
    sig = sig + (SinOsc.ar(freq * [0.5, 1]) * pool * 0.2);

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_scorn_mucus loaded".postln;
