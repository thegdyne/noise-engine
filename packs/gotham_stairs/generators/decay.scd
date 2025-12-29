SynthDef(\forge_gotham_stairs_decay, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var crumble, rust, hollow, neglect, collapse;
    var dustTrig, crumbleSig, rustRes, hollowRes, collapseBurst, droneBase;

    // Theme params
    crumble = In.kr(customBus0);
    rust = In.kr(customBus1);
    hollow = In.kr(customBus2);
    neglect = In.kr(customBus3);
    collapse = In.kr(customBus4);

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

    // Dust trigger for crumbling particles
    dustTrig = Dust.ar(crumble.linlin(0, 1, 2, 30));

    // Crumbling concrete/plaster particles
    crumbleSig = Ringz.ar(dustTrig, freq * [1, 1.5, 2.3], crumble.linlin(0, 1, 0.05, 0.2)).sum;
    crumbleSig = crumbleSig * neglect * 0.4;

    // Rust resonance - metallic decay on railings
    rustRes = Ringz.ar(
        Dust.ar(rust.linlin(0, 1, 1, 15)),
        freq * [3.1, 4.7, 6.2],
        rust.linlin(0, 1, 0.1, 0.4)
    ).sum * rust * 0.3;

    // Hollow spaces - resonant cavities in walls
    hollowRes = Resonz.ar(
        PinkNoise.ar(0.2),
        freq * hollow.linlin(0, 1, 0.5, 2),
        0.1 + (hollow * 0.2)
    ) * 4 * hollow;

    // Collapse bursts - structural failure moments
    collapseBurst = Dust.ar(collapse.linlin(0, 1, 0.2, 2));
    collapseBurst = DynKlank.ar(
        `[
            [1, 1.7, 2.4, 3.8, 5.1],
            [1, 0.6, 0.4, 0.2, 0.1],
            [0.5, 0.4, 0.3, 0.2, 0.1] * (1 + neglect)
        ],
        collapseBurst * 0.4,
        freq * 0.5
    ) * collapse;

    // Continuous drone base for drone mode compatibility
    droneBase = BrownNoise.ar(0.08) + (PinkNoise.ar(0.05) * neglect);
    droneBase = RLPF.ar(droneBase, freq * 2, 0.5);

    sig = crumbleSig + rustRes + hollowRes + collapseBurst + droneBase;

    // Neglect degrades the overall sound
    sig = sig * (0.7 + (neglect * 0.3));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_gotham_stairs_decay loaded".postln;
