// Capillary Lead - Water drawn up through thin tubes
// FM synthesis with rising pitch envelope and flowing modulation

SynthDef(\forge_dew_sphere_capillary_lead, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
    filterTypeBus, envEnabledBus, envSourceBus=0,
    clockRateBus, clockTrigBus,
    midiTrigBus=0, slotIndex=0,
    customBus0, customBus1, customBus2, customBus3, customBus4,
    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var rise, thin, flow, meniscus, bright;
    var riseEnv, flowMod, carrier, modulator;
    var meniscusBend, thinFilter;

    // Standard bus reads
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
    rise = In.kr(customBus0);       // Upward pitch
    thin = In.kr(customBus1);       // Thinness
    flow = In.kr(customBus2);       // Flow rate
    meniscus = In.kr(customBus3);   // Surface curve
    bright = In.kr(customBus4);     // Brightness

    // Rising pitch envelope - simulates water being drawn up
    riseEnv = EnvGen.ar(
        Env([1, 1 + (rise * 0.1)], [0.5], \lin),
        Impulse.ar(0)
    );

    // Flow modulation - continuous rippling movement
    flowMod = SinOsc.ar(flow.linexp(0, 1, 2, 15)) * flow * 0.02;

    // Meniscus bend - curved surface tension effect
    meniscusBend = SinOsc.ar(freq * meniscus.linexp(0, 1, 0.5, 2)) * meniscus * 0.3;

    // FM synthesis - thin columns have more harmonics
    modulator = SinOsc.ar(freq * 3 * riseEnv) * thin.linexp(0, 1, 1, 6) * freq * 0.3;
    carrier = SinOsc.ar((freq * riseEnv * (1 + flowMod)) + modulator + meniscusBend);

    // Add octave for brightness
    sig = carrier + (SinOsc.ar(freq * 2 * riseEnv) * bright * 0.3);

    // Sub layer for body
    sig = sig + (SinOsc.ar(freq * 0.5 * riseEnv) * (1 - thin) * 0.2);

    // Thinness filter - thinner = more highs, less lows
    thinFilter = thin.linexp(0, 1, 200, 2000);
    sig = HPF.ar(sig, thinFilter) + (LPF.ar(sig, 300) * (1 - thin) * 0.5);

    // Brightness top end
    sig = sig + (HPF.ar(sig, 4000) * bright * 0.3);

    // Normalize
    sig = sig * 0.5;

    // Output chain
    sig = ~stereoSpread.(sig, 0.2 + (flow * 0.3), 0.2);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_dew_sphere_capillary_lead loaded".postln;
