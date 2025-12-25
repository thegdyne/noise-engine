// Vine Ping - Woody/metallic branch taps
// Role: accent | Family: physical

SynthDef(\forge_emerald_canopy_vine_ping, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                             filterTypeBus, envEnabledBus, envSourceBus=0,
                                             clockRateBus, clockTrigBus,
                                             midiTrigBus=0, slotIndex=0,
                                             customBus0, customBus1, customBus2, customBus3, customBus4,
                                             portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var tension, node, wood, ring, hollow;
    var exciter, modes, modeFreqs, modeDecays, body, cavity;

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
    tension = In.kr(customBus0);  // String tightness
    node = In.kr(customBus1);     // Strike position
    wood = In.kr(customBus2);     // Body character
    ring = In.kr(customBus3);     // Sustain
    hollow = In.kr(customBus4);   // Cavity resonance

    // Exciter - click/strike with node affecting brightness
    exciter = WhiteNoise.ar * EnvGen.ar(
        Env.perc(0.0001, node.linexp(0, 1, 0.001, 0.02))
    );
    exciter = HPF.ar(exciter, node.linexp(0, 1, 200, 2000));

    // Modal resonances - vine-like inharmonic partials
    modeFreqs = [
        freq * tension.linexp(0, 1, 0.8, 1.2),
        freq * 2.3 * tension.linexp(0, 1, 0.9, 1.1),
        freq * 4.1 * tension.linexp(0, 1, 0.85, 1.15),
        freq * 6.7
    ];

    modeDecays = [
        ring.linexp(0, 1, 0.1, 2),
        ring.linexp(0, 1, 0.05, 1),
        ring.linexp(0, 1, 0.02, 0.5),
        ring.linexp(0, 1, 0.01, 0.3)
    ];

    // Create resonant modes
    modes = Array.fill(4, { |i|
        var modeRing = Ringz.ar(exciter, modeFreqs[i], modeDecays[i]);
        modeRing * (1 - (i * 0.2))  // Higher modes quieter
    }).sum;

    // Woody body resonance - lowpass colored
    body = BPF.ar(modes, freq * wood.linexp(0, 1, 0.5, 2), 0.3) * wood;

    // Hollow cavity - comb filter resonance
    cavity = CombL.ar(
        modes * hollow,
        0.1,
        (freq * hollow.linexp(0, 1, 0.5, 2)).reciprocal.clip(0.001, 0.1),
        ring.linexp(0, 1, 0.1, 0.8)
    ) * 0.4;

    sig = modes + body + cavity;

    // Slight stereo from node position
    sig = Pan2.ar(sig, (node - 0.5) * 0.6);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_emerald_canopy_vine_ping loaded".postln;
