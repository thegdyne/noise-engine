SynthDef(\forge_arctic_henge_threshold, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0, clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var power, portal, cross, resonance, void;
    var transient, sweep, body, subTail, impact;

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
    power = In.kr(customBus0);
    portal = In.kr(customBus1);
    cross = In.kr(customBus2);
    resonance = In.kr(customBus3);
    void = In.kr(customBus4);

    // Sharp transient - the crossing moment
    transient = WhiteNoise.ar * EnvGen.ar(
        Env.perc(0.001, cross.linexp(0, 1, 0.01, 0.1))
    ) * cross;

    // Spectral sweep - portal opening
    sweep = RLPF.ar(
        WhiteNoise.ar + (Saw.ar(freq * 2) * 0.3),
        EnvGen.ar(
            Env.perc(0.01, portal.linexp(0, 1, 0.3, 2)),
            levelScale: portal.linexp(0, 1, 2000, 8000)
        ) + 200,
        0.3
    ) * portal * 0.5;

    // Resonant body - stone ringing
    body = Mix.fill(6, { |i|
        var partial = [1, 1.5, 2, 2.7, 3.5, 4.2].at(i);
        var ringTime = resonance.linexp(0, 1, 0.3, 2);
        Ringz.ar(
            Impulse.ar(0),
            freq * partial,
            ringTime
        ) * power * (0.15 / (i + 1))
    });

    // Sub bass tail - void beneath
    subTail = SinOsc.ar(freq * void.linexp(0, 1, 0.5, 1)) *
        EnvGen.ar(Env.perc(0.05, void.linexp(0, 1, 0.5, 3))) * void * 0.5;

    // Combine
    impact = (transient * 0.3) + sweep + body + subTail;
    sig = impact * power;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_arctic_henge_threshold loaded".postln;
