SynthDef(\forge_summer_of_love_park_bell, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                              filterTypeBus, envEnabledBus, envSourceBus=0,
                                              clockRateBus, clockTrigBus,
                                              midiTrigBus=0, slotIndex=0,
                                              customBus0, customBus1, customBus2, customBus3, customBus4,
                                              portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var chime, breeze, jewelry, sustain, peace;
    var exciter, gain, modes, modeRatios, modeDecays, breezeWobble, jangle, trig;

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
    chime = In.kr(customBus0);     // Brightness/character
    breeze = In.kr(customBus1);    // Pitch movement
    jewelry = In.kr(customBus2);   // Extra jangle modes
    sustain = In.kr(customBus3);   // Ring time
    peace = In.kr(customBus4);     // Harmonic purity

    // Internal trigger
    trig = Impulse.ar(0);

    // Exciter - short bright click
    exciter = HPF.ar(WhiteNoise.ar(1), 2000) * EnvGen.ar(Env.perc(0.0001, 0.002), trig);
    exciter = exciter + (Impulse.ar(0) * 0.5);

    // Breeze - gentle pitch wobble
    breezeWobble = LFNoise1.kr(breeze.linlin(0, 1, 0.2, 2)) * breeze * 0.02;

    // Modal ratios - bell/chime partials
    // Peace parameter blends between inharmonic and harmonic
    modeRatios = [
        1.0,
        2.0 + ((1 - peace) * 0.41),      // ~2.41 for bell, 2.0 for pure
        3.0 + ((1 - peace) * 0.57),      // ~3.57 for bell
        4.0 + ((1 - peace) * 0.23) + (chime * 0.5),  // Higher with chime
        5.0 + ((1 - peace) * 0.64) + (chime * 0.8),
        6.0 + (chime * 1.2)              // Top brightness
    ];

    // Decay times - higher modes decay faster
    modeDecays = [1.0, 0.7, 0.5, 0.35, 0.25, 0.15] * sustain.linexp(0, 1, 0.3, 3.0);

    // Create modal resonators
    modes = modeRatios.collect({ |ratio, i|
        var modeFreq = freq * ratio * (1 + breezeWobble);
        var modeDecay = modeDecays[i];
        var gain = [1.0, 0.8, 0.5, 0.4, 0.3, 0.2][i];
        // Higher modes are brighter with chime parameter
        gain = gain * (1 + (chime * (i / 6)));
        Ringz.ar(exciter, modeFreq.clip(100, 12000), modeDecay) * gain
    }).sum;

    sig = modes;

    // Jewelry jangle - extra high inharmonic modes
    jangle = [7.23, 9.17, 11.89].collect({ |ratio, i|
        var jangleFreq = freq * ratio * (1 + (LFNoise1.kr(1 + i) * 0.01));
        Ringz.ar(exciter, jangleFreq.clip(500, 15000), 0.1 + (sustain * 0.2)) * 0.15
    }).sum;
    sig = sig + (jangle * jewelry);

    // Gentle limiting
    sig = sig.tanh * 0.7;

    // Subtle stereo spread
    sig = ~stereoSpread.(sig, 0.3, 0.4);

    // Apply standard processing chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_summer_of_love_park_bell loaded".postln;
