SynthDef(\forge_kaiju_beats_mecha, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var mass, hydraulic, armor, groan, rust;
    var exciter, modes, metalBody, hydraulicHiss;

    // Theme params
    mass = In.kr(customBus0);         // P1: Body mass - shifts modal frequencies
    hydraulic = In.kr(customBus1);    // P2: Hydraulic hiss amount
    armor = In.kr(customBus2);        // P3: Armor thickness - dampening
    groan = In.kr(customBus3);        // P4: Metal groan/stress
    rust = In.kr(customBus4);         // P5: Rust - adds noise/grit

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
    ampVal = 0.2;

    // Exciter - metallic impulse with rust noise
    exciter = Dust.ar(1 + (groan * 3)) * 0.5;
    exciter = exciter + (PinkNoise.ar(0.02) * rust);

    // Modal resonator - giant robot body
    modes = DynKlank.ar(
        `[
            [1, 2.1, 3.5, 4.8, 6.2, 8.1] * (1 + (mass.neg * 0.3)),
            [1, 0.7, 0.5, 0.3, 0.2, 0.1],
            [2, 1.8, 1.5, 1.2, 1.0, 0.8] * (1 + (armor * 2))
        ],
        exciter,
        freq,
        0,
        (2 + (armor * 4)).reciprocal
    );

    // Metal stress/groan - slow LFO modulated resonance
    metalBody = SinOsc.ar(freq * 0.5 * (1 + (LFNoise1.kr(0.2) * groan * 0.1)));
    metalBody = metalBody * LFNoise2.kr(0.5 + (groan * 2)).range(0.3, 1) * groan * 0.3;

    // Hydraulic hiss
    hydraulicHiss = BPF.ar(WhiteNoise.ar(0.5), 3000 + (LFNoise1.kr(2) * 1000), 0.3);
    hydraulicHiss = hydraulicHiss * hydraulic * 0.2;

    // Mix
    sig = (modes * 0.6) + metalBody + hydraulicHiss;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_kaiju_beats_mecha loaded".postln;
