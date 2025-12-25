SynthDef(\forge_arctic_henge_starfield, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var density, twinkle, distance, constellation, vastness;
    var stars, reverb;

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
    density = In.kr(customBus0);
    twinkle = In.kr(customBus1);
    distance = In.kr(customBus2);
    constellation = In.kr(customBus3);
    vastness = In.kr(customBus4);

    // Multiple star voices at different positions
    stars = Mix.fill(8, { |i|
        var trigRate = density.linexp(0, 1, 0.5, 8) * Rand(0.5, 2);
        var trig = Dust.ar(trigRate);

        // Pitch clustering around base freq with constellation spread
        var clusterSpread = constellation.linexp(0, 1, 1, 4);
        var starFreq = freq * (4 + i) * TRand.ar(1 / clusterSpread, clusterSpread, trig);

        // Brightness variation
        var brightness = TRand.ar(0.3, 1.0, trig) * twinkle + ((1 - twinkle) * 0.7);

        // Distance affects decay time
        var starDecay = distance.linexp(0, 1, 0.1, 0.8);

        // Pan position based on vastness
        var pan = TRand.ar(vastness * -1, vastness, trig);

        // The star itself - modal ring
        var star = Ringz.ar(
            trig * brightness,
            starFreq.min(14000),
            starDecay
        ) * 0.1;

        Pan2.ar(star, pan)
    });

    // Distance reverb
    reverb = FreeVerb.ar(
        stars,
        distance,
        distance.linlin(0, 1, 0.3, 0.9),
        0.5
    );

    sig = stars + (reverb * 0.5);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_arctic_henge_starfield loaded".postln;
