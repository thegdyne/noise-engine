// patch: Patch cable connections and contact noise
SynthDef(\forge_mod_caf_patch, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var crackle, hum, insert, oxidation, ground;

    // Theme params
    crackle = In.kr(customBus0).linlin(0, 1, 10, 50);       // P1: Contact crackle rate (boosted)
    hum = In.kr(customBus1).linlin(0, 1, 0.2, 0.6);         // P2: Ground hum (boosted)
    insert = In.kr(customBus2).linlin(0, 1, 1, 6);          // P3: Jack insert rate
    oxidation = In.kr(customBus3).linlin(0, 1, 0.1, 0.5);   // P4: Dirty contact
    ground = In.kr(customBus4).linlin(0, 1, 50, 62);        // P5: Ground frequency

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

    // DSP: Continuous cable capacitance hiss (always present)
    sig = LPF.ar(PinkNoise.ar(0.35), 2500);

    // Ground hum - continuous 50/60Hz
    sig = sig + (SinOsc.ar(ground * [1, 2, 3]) * hum * [0.4, 0.2, 0.1]).sum;

    // Contact crackle - high frequency pops (boosted rate)
    sig = sig + (HPF.ar(Dust2.ar(crackle) * 0.35, 800));

    // Jack insert clicks - low thunks
    sig = sig + (Ringz.ar(Dust.ar(insert) * 0.3, 150, 0.03));

    // Oxidation noise - dirty contact texture (continuous Crackle)
    sig = sig + (Crackle.ar(1.5 + (oxidation * 0.4)) * oxidation * 0.25);

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_mod_caf_patch loaded".postln;
