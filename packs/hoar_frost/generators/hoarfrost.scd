// hoarfrost: Frost crackling - granular texture
SynthDef(\forge_hoar_frost_hoarfrost, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var grainRate, grainSize, scatter, tonal, texture;

    // Theme params
    grainRate = In.kr(customBus0).linexp(0, 1, 5, 80);     // P1: Grain rate
    grainSize = In.kr(customBus1).linlin(0, 1, 0.005, 0.05); // P2: Grain size
    scatter = In.kr(customBus2).linlin(0, 1, 0, 1);        // P3: Pitch scatter
    tonal = In.kr(customBus3).linlin(0, 1, 0, 1);          // P4: Tonal vs noise
    texture = In.kr(customBus4).linlin(0, 1, 0.1, 0.9);    // P5: Texture density

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

    // DSP: Granular with tonal/noise blend
    sig = GrainSin.ar(
        2,
        Dust.ar(grainRate * texture),
        grainSize,
        freq * (1 + (TRand.ar(scatter.neg, scatter, Dust.ar(grainRate)))),
        0,
        -1
    ) * tonal;

    // Add noise grains
    sig = sig + (GrainBuf.ar(
        2,
        Dust.ar(grainRate * texture * 0.5),
        grainSize * 2,
        LocalBuf(512).set(Array.fill(512, { |i| (i / 512 * 2 - 1).rand })),
        1,
        TRand.ar(0, 1, Dust.ar(grainRate)),
        2
    ) * (1 - tonal) * 0.3);

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_hoar_frost_hoarfrost loaded".postln;
