// vessel: The doomed ship - creaking hull facing the impossible
SynthDef(\forge_rlyeh_vessel, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var hull, creak, rock, sail, dread;

    // Theme params
    hull = In.kr(customBus0).linlin(0, 1, 0.4, 1);         // P1: Hull resonance
    creak = In.kr(customBus1).linlin(0, 1, 2, 10);         // P2: Creak rate
    rock = In.kr(customBus2).linlin(0, 1, 0.1, 0.5);       // P3: Rocking motion
    sail = In.kr(customBus3).linlin(0, 1, 0.2, 0.7);       // P4: Sail flutter
    dread = In.kr(customBus4).linlin(0, 1, 0.2, 0.8);      // P5: Impending dread

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

    // DSP: Hull resonance - wooden body (boosted gain)
    sig = Resonz.ar(PinkNoise.ar(hull), freq * [1, 1.5, 2.2], 0.2) * 12;
    sig = Splay.ar(sig, 0.4);

    // Creaking - continuous triggered hits
    sig = sig + (Ringz.ar(Dust.ar(creak) * 0.4, freq * [0.7, 1.5], 0.25) * 0.6);

    // Rocking motion - gentler
    sig = sig * SinOsc.kr(rock).range(0.7, 1);

    // Sail flutter - boosted
    sig = sig + (BPF.ar(PinkNoise.ar(sail), freq * 3, 0.4) * 0.5);

    // Dread undertone - always present, boosted
    sig = sig + (SinOsc.ar(freq * [0.25, 0.251]) * dread * 0.5);

    sig = sig * 0.4;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_rlyeh_vessel loaded".postln;
