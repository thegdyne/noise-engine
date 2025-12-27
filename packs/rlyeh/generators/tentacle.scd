// tentacle: Writhing appendages - organic alien movement
SynthDef(\forge_rlyeh_tentacle, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var writhe, slime, mass, sucker, alien;

    // Theme params
    writhe = In.kr(customBus0).linlin(0, 1, 0.2, 3);       // P1: Writhing speed
    slime = In.kr(customBus1).linlin(0, 1, 0.1, 0.8);      // P2: Wet slime texture
    mass = In.kr(customBus2).linlin(0, 1, 2, 8);           // P3: Tentacle count
    sucker = In.kr(customBus3).linlin(0, 1, 0, 0.6);       // P4: Sucker pops
    alien = In.kr(customBus4).linlin(0, 1, 0, 0.5);        // P5: Alien harmonics

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

    // DSP: Writhing FM clusters
    sig = Mix.fill(mass.round, { |i|
        var phase = i / mass * 2pi;
        var modFreq = freq * (1 + (i * 0.1));
        var writheRate = writhe * (1 + (i * 0.15));
        PMOsc.ar(
            modFreq * (1 + (SinOsc.kr(writheRate, phase).range(0, 0.1))),
            modFreq * 2,
            SinOsc.kr(writheRate * 0.7, phase).range(0.5, 2),
            0
        ) * (1 / mass.sqrt)
    });

    // Slime texture
    sig = sig + (Resonz.ar(PinkNoise.ar(slime), freq * LFNoise1.kr(writhe).range(1, 3), 0.1) * 2);

    // Sucker pops
    sig = sig + (Ringz.ar(Dust.ar(sucker * 20) * 0.2, freq * [2, 3, 4], 0.05).sum);

    // Alien overtones
    sig = sig + (SinOsc.ar(freq * [1.618, 2.618, 4.236]) * alien * 0.15);

    sig = sig * 0.2;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_rlyeh_tentacle loaded".postln;
