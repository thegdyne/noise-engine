SynthDef(\forge_gotham_stairs_smile, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var grin, teeth, strain, fake, crack;
    var exciter, formants, f1, f2, f3, strainMod, crackBurst;

    // Theme params
    grin = In.kr(customBus0);
    teeth = In.kr(customBus1);
    strain = In.kr(customBus2);
    fake = In.kr(customBus3);
    crack = In.kr(customBus4);

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

    // Strain modulation - tension tremolo
    strainMod = 1 + (strain * SinOsc.kr(strain.linlin(0, 1, 2, 12)).range(0, 0.2));

    // Vocal exciter - pulse wave with strain
    exciter = Pulse.ar(freq * strainMod, 0.3 + (strain * 0.2)) * 0.3;
    exciter = exciter + (PinkNoise.ar(0.1) * teeth);

    // Formant frequencies - grin widens the mouth shape
    // Base vowel "EE" (smile) shifting based on grin
    f1 = grin.linlin(0, 1, 300, 450) * (1 + (fake * LFNoise1.kr(3).range(0, 0.1)));
    f2 = grin.linlin(0, 1, 2200, 2800) * (1 + (fake * LFNoise1.kr(2.5).range(0, 0.1)));
    f3 = grin.linlin(0, 1, 2800, 3500) * (1 + (teeth * 0.3));

    // Formant filters with gain boost
    formants = Resonz.ar(exciter, f1, 0.1) * 5;
    formants = formants + (Resonz.ar(exciter, f2, 0.15) * 4 * grin);
    formants = formants + (Resonz.ar(exciter, f3, 0.2) * 3 * teeth);

    // Crack moments - sudden breaks in the facade
    crackBurst = Dust.ar(crack.linlin(0, 1, 0.5, 4));
    crackBurst = Ringz.ar(crackBurst, freq * [3, 5], 0.1).sum * crack * 0.4;

    sig = formants + crackBurst;

    // Fake happiness warble
    sig = sig * (1 + (fake * SinOsc.kr(fake.linlin(0, 1, 4, 10)).range(0, 0.15)));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_gotham_stairs_smile loaded".postln;
