SynthDef(\forge_summer_of_love_tribal_pulse, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                                 filterTypeBus, envEnabledBus, envSourceBus=0,
                                                 clockRateBus, clockTrigBus,
                                                 midiTrigBus=0, slotIndex=0,
                                                 customBus0, customBus1, customBus2, customBus3, customBus4,
                                                 portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var skin, body, strike, earth, ring;
    var exciter, modes, modeRatios, modeDecays, bodyRes, earthThump, trig;

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
    skin = In.kr(customBus0);     // Membrane tension
    body = In.kr(customBus1);     // Shell resonance
    strike = In.kr(customBus2);   // Attack character
    earth = In.kr(customBus3);    // Sub-bass thump
    ring = In.kr(customBus4);     // Overtone decay

    // Internal trigger for sound design (always triggers for preview)
    // In actual use, the envelope handles amplitude
    trig = Impulse.ar(0);

    // Exciter - noise burst for strike
    exciter = WhiteNoise.ar(1) * EnvGen.ar(
        Env.perc(0.001, strike.linexp(0, 1, 0.005, 0.03)),
        trig
    );
    // Add filtered component for finger vs palm
    exciter = exciter + (LPF.ar(PinkNoise.ar(1), strike.linexp(0, 1, 2000, 8000)) * 0.5);

    // Membrane mode ratios - inharmonic like real drum heads
    // Ratios shift with skin tension
    modeRatios = [
        1.0,                              // Fundamental
        1.59 + (skin * 0.2),              // (0,1) mode
        2.14 + (skin * 0.3),              // (1,1) mode
        2.30 + (skin * 0.25),             // (2,1) mode
        2.65 + (skin * 0.35)              // (0,2) mode
    ];

    // Mode decay times - ring controls overall
    modeDecays = [0.15, 0.08, 0.05, 0.04, 0.03] * ring.linlin(0, 1, 0.5, 2.0);

    // Create membrane modes using resonant filters
    modes = modeRatios.collect({ |ratio, i|
        var modeFreq = freq * ratio;
        var modeDecay = modeDecays[i];
        var gain = [1.0, 0.6, 0.4, 0.3, 0.2][i];
        Ringz.ar(exciter, modeFreq.clip(50, 8000), modeDecay) * gain
    }).sum;

    // Body resonance - low shell tone
    bodyRes = Ringz.ar(exciter * 2, freq * 0.5, ring.linlin(0, 1, 0.1, 0.3)) * body;
    bodyRes = LPF.ar(bodyRes, 400);

    // Earth thump - sub-bass sine punch
    earthThump = SinOsc.ar(freq * 0.25) * EnvGen.ar(
        Env.perc(0.001, ring.linlin(0, 1, 0.05, 0.15)),
        trig
    ) * earth * 2;

    sig = modes + bodyRes + earthThump;

    // Gentle limiting
    sig = sig.tanh;

    // Subtle stereo for natural placement
    sig = ~stereoSpread.(sig, 0.1, 0.2);

    // Apply standard processing chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_summer_of_love_tribal_pulse loaded".postln;
