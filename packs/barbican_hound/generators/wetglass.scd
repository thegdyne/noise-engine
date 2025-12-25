// WETGLASS - Rain drops on glass and metal
// Family: physical (karplus)
// Role: accent

SynthDef(\forge_barbican_hound_wetglass, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                            portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var drop, pane, bead, tint, pool;
    var exciter, pluck, glass, trig;

    // Standard bus reads
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
    drop = In.kr(customBus0);   // Impact sharpness
    pane = In.kr(customBus1);   // Surface resonance
    bead = In.kr(customBus2);   // Decay time
    tint = In.kr(customBus3);   // Brightness
    pool = In.kr(customBus4);   // Density

    // Trigger selection
    trig = Select.ar(envSource.round.clip(0, 2), [
        Impulse.ar(pool.linexp(0, 1, 1, 15)),  // OFF: internal density trigger
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // Drop exciter - sharp noise burst
    exciter = WhiteNoise.ar(1) * EnvGen.ar(Env.perc(0.001, drop.linexp(0, 1, 0.005, 0.05)), trig);

    // Karplus-Strong plucked string - main drop sound
    pluck = Pluck.ar(
        exciter,
        trig,
        0.2,
        freq.reciprocal,
        bead.linexp(0, 1, 0.2, 3),
        pane.linlin(0, 1, 0.7, 0.3)  // Coef: higher = duller
    );

    // Glass resonances - higher partials
    glass = Ringz.ar(exciter * 0.3, freq * [2.3, 3.7, 5.1], bead.linexp(0, 1, 0.1, 0.5)).sum;

    // Combine with glass surface
    sig = pluck + (glass * pane * 0.5);

    // Tint filter
    sig = LPF.ar(sig, tint.linexp(0, 1, 2000, 12000));

    // Stereo placement with subtle randomness
    sig = Pan2.ar(sig, TRand.kr(-0.7, 0.7, trig));

    // Post-chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_barbican_hound_wetglass loaded".postln;
