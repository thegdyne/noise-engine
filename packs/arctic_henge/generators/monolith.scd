SynthDef(\forge_arctic_henge_monolith, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var mass, age, ring, depth, crack;
    var sub, mid, harmonics, crackle, stone;

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

    // Theme params
    mass = In.kr(customBus0);
    age = In.kr(customBus1);
    ring = In.kr(customBus2);
    depth = In.kr(customBus3);
    crack = In.kr(customBus4);

    // Sub foundation - pure weight
    sub = SinOsc.ar(freq * depth.linexp(0, 1, 0.5, 1.0)) * mass;
    sub = sub + (SinOsc.ar(freq * 0.5) * mass * 0.5);

    // Mid stone body - detuned saws
    mid = Mix.fill(4, { |i|
        var detune = i.linlin(0, 3, 0.995, 1.005);
        var ageFilter = age.linexp(0, 1, 2000, 500);
        LPF.ar(
            Saw.ar(freq * detune * (1 + (i * 0.001))),
            ageFilter
        ) * 0.2
    });

    // Resonant harmonics - ring of the stone
    harmonics = Mix.fill(6, { |i|
        var partial = i + 1;
        var ringTime = ring.linexp(0, 1, 0.5, 4);
        var partialFreq = freq * partial * (1 + (age * 0.02 * i));
        Ringz.ar(
            Dust.ar(0.5 + (age * 2)),
            partialFreq.min(8000),
            ringTime
        ) * (0.1 / (partial + 1))
    });

    // Crack texture - ancient fractures
    crackle = LPF.ar(
        Dust2.ar(crack.linexp(0, 1, 1, 50)) * crack,
        freq * 4
    ) * 0.3;

    // Combine
    stone = (sub * 0.5) + (mid * 0.3) + (harmonics * 0.15) + (crackle * 0.05);

    sig = stone;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_arctic_henge_monolith loaded".postln;
