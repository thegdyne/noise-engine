// birth: Pod emergence - opening, wet release
SynthDef(\forge_scorn_birth, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var emerge, sac, fluid, strain, newborn;

    // Theme params
    emerge = In.kr(customBus0).linlin(0, 1, 0.3, 1);        // P1: Emergence level
    sac = In.kr(customBus1).linlin(0, 1, 0.2, 0.8);         // P2: Sac membrane
    fluid = In.kr(customBus2).linlin(0, 1, 5, 25);          // P3: Fluid sounds
    strain = In.kr(customBus3).linlin(0, 1, 0.1, 0.5);      // P4: Straining
    newborn = In.kr(customBus4).linlin(0, 1, 0.1, 0.6);     // P5: New life sounds

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

    // DSP: Sac membrane - stretching sounds
    sig = LPF.ar(PinkNoise.ar(sac * 0.4), 800 * LFNoise1.kr(0.2).range(0.5, 2));

    // Fluid release - wet drips and splashes
    sig = sig + (Ringz.ar(Dust.ar(fluid) * 0.2, freq * [1, 2, 3], 0.08) * emerge * 0.4);

    // Straining sounds - low groans
    sig = sig + (LPF.ar(Saw.ar(freq * 0.25 * LFNoise1.kr(0.3).range(0.9, 1.1)) * strain, 400) * 0.3);

    // Newborn presence - high soft tones
    sig = sig + (SinOsc.ar(freq * [2, 3] * LFNoise1.kr(0.1).range(0.98, 1.02)) * newborn * 0.2);

    // Continuous wet ambience
    sig = sig + (LPF.ar(BrownNoise.ar(emerge * 0.3), 500));

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_scorn_birth loaded".postln;
