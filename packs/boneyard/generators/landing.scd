// LANDING - Gear collapse, hydraulic hiss, strut impact
// Role: accent
SynthDef(\forge_boneyard_landing, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                     filterTypeBus, envEnabledBus, envSourceBus=0,
                                     clockRateBus, clockTrigBus,
                                     midiTrigBus=0, slotIndex=0,
                                     customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var weight, leak, bounce, rubber, lock;
    var impact, hydraulic, bounceHits, rubberSqueal, lockClick;
    var exciter;

    // Custom params
    weight = In.kr(customBus0);     // Weight class
    leak = In.kr(customBus1);       // Hydraulic leak
    bounce = In.kr(customBus2);     // Strut bounce
    rubber = In.kr(customBus3);     // Tire squeal
    lock = In.kr(customBus4);       // Lock click

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

    // Exciter
    exciter = Impulse.ar(0);

    // Main impact - low thump scaled by weight
    impact = SinOsc.ar(
        freq * weight.linexp(0, 1, 0.25, 0.5),
        0,
        EnvGen.ar(Env.perc(0.001, weight.linexp(0, 1, 0.1, 0.4)))
    );
    impact = impact + LPF.ar(
        WhiteNoise.ar(0.3) * EnvGen.ar(Env.perc(0.001, 0.05)),
        weight.linexp(0, 1, 500, 200)
    );
    impact = impact * weight.linlin(0, 1, 0.5, 1);

    // Hydraulic hiss - escaping pressure
    hydraulic = BPF.ar(
        WhiteNoise.ar(0.4),
        leak.linexp(0, 1, 4000, 8000),
        0.2
    );
    hydraulic = hydraulic * EnvGen.ar(
        Env([0, 1, 0.3, 0], [0.01, leak.linexp(0, 1, 0.3, 1.5), 0.2]),
        exciter
    );
    hydraulic = hydraulic * leak;

    // Bounce hits - secondary impacts
    bounceHits = Mix.fill(3, { |i|
        var delay = (i + 1) * bounce.linexp(0, 1, 0.05, 0.15);
        var amp = 1 / (i + 2);
        DelayN.ar(
            SinOsc.ar(freq * 0.3, 0, amp) *
            EnvGen.ar(Env.perc(0.001, 0.05), TDelay.ar(exciter, delay)),
            0.5,
            delay
        );
    });
    bounceHits = bounceHits * bounce;

    // Rubber squeal - bandpass noise, deflating tire
    rubberSqueal = BPF.ar(
        PinkNoise.ar(0.5),
        freq * rubber.linexp(0, 1, 2, 6) * LFNoise1.kr(10).range(0.9, 1.1),
        0.15
    );
    rubberSqueal = rubberSqueal * EnvGen.ar(
        Env([0, 1, 0], [0.1, rubber.linexp(0, 1, 0.2, 0.8)]),
        exciter
    );
    rubberSqueal = rubberSqueal * rubber * 0.5;

    // Lock click - sharp transient at end
    lockClick = Ringz.ar(
        TDelay.ar(exciter, weight.linexp(0, 1, 0.15, 0.35)),
        freq * 4,
        0.01,
        lock
    );
    lockClick = lockClick + (
        HPF.ar(WhiteNoise.ar(0.2), 3000) *
        EnvGen.ar(Env.perc(0.001, 0.01), TDelay.ar(exciter, weight.linexp(0, 1, 0.15, 0.35))) *
        lock
    );

    // Combine
    sig = impact + hydraulic + bounceHits + rubberSqueal + lockClick;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_boneyard_landing loaded".postln;
