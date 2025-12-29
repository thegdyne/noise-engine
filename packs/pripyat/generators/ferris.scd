SynthDef(\forge_pripyat_ferris, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var rust, spin, mass, groan, sway;
    var exciter, modes, groanSig, creakRate, swayMod;

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
    rust = In.kr(customBus0);
    spin = In.kr(customBus1);
    mass = In.kr(customBus2);
    groan = In.kr(customBus3);
    sway = In.kr(customBus4);

    // Rotation-based creak rate
    creakRate = spin.linexp(0, 1, 0.1, 2);
    swayMod = LFNoise2.kr(0.2) * sway * 0.1;

    // Modal exciter - continuous dust triggers for creaks
    exciter = Dust.ar(creakRate * 3) * 0.3;
    exciter = exciter + (LFNoise2.ar(creakRate) * 0.02); // Continuous friction

    // Modal resonances - rusted metal frequencies
    modes = DynKlank.ar(
        `[
            [1, 2.3, 4.5, 6.7, 8.2, 11.3] * (1 + (rust * 0.15)),  // Rust detunes
            [1, 0.6, 0.3, 0.2, 0.15, 0.1] * (1 - (rust * 0.3)),   // Rust dampens
            [1.2, 0.9, 0.7, 0.5, 0.4, 0.3] * mass.linlin(0, 1, 0.5, 2)  // Mass affects decay
        ],
        exciter,
        freq * (1 + swayMod),
        0,
        mass.linexp(0, 1, 0.5, 3)
    );

    // Low groan - structural stress
    groanSig = SinOsc.ar(freq * 0.25 * (1 + (LFNoise2.kr(0.3) * 0.05)));
    groanSig = groanSig * LFNoise2.kr(spin.linlin(0, 1, 0.05, 0.3)).range(0, 1);
    groanSig = groanSig * groan * 0.3;

    // Mix
    sig = modes + groanSig;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_pripyat_ferris loaded".postln;
