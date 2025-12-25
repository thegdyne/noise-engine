SynthDef(\forge_seagrass_bay_surface_light, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var ripple, sun, dance, sparkle, wave;
    var carrier, modulator, rippleMod, dancePattern, sparkleGlints, amDepth;

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

    // Custom params
    ripple = In.kr(customBus0);     // Surface wave rate
    sun = In.kr(customBus1);        // Brightness
    dance = In.kr(customBus2);      // Light pattern
    sparkle = In.kr(customBus3);    // Glints
    wave = In.kr(customBus4);       // Mod depth

    // Ripple modulation rate
    rippleMod = ripple.linexp(0, 1, 2, 15);

    // AM modulator - multiple ripple frequencies for complex pattern
    modulator = SinOsc.ar(rippleMod) * 0.4;
    modulator = modulator + (SinOsc.ar(rippleMod * 1.618) * 0.3);  // Golden ratio
    modulator = modulator + (SinOsc.ar(rippleMod * 0.618) * 0.3);  // Inverse golden

    // Dance pattern - irregular brightness shifts
    dancePattern = LFNoise1.kr(dance.linexp(0, 1, 0.5, 3)).range(0.7, 1);

    // Carrier - bright harmonics for sun quality
    carrier = Pulse.ar(freq, 0.3) * 0.4;
    carrier = carrier + (Pulse.ar(freq * 2.01, 0.4) * 0.25 * sun);
    carrier = carrier + (SinOsc.ar(freq * 3) * 0.15 * sun);

    // AM depth controlled by wave
    amDepth = wave.linlin(0, 1, 0.1, 0.6);
    sig = carrier * (1 + (modulator * amDepth));

    // Apply dance pattern
    sig = sig * dancePattern;

    // Sparkle - high frequency glints
    sparkleGlints = Ringz.ar(
        Dust.ar(sparkle.linexp(0, 1, 5, 40)),
        freq * [3, 4, 5, 6],
        0.05
    ).sum * sparkle * 0.2;
    sig = sig + sparkleGlints;

    // Sun = overall brightness
    sig = sig * sun.linlin(0, 1, 0.5, 1.2);

    // Wide stereo for shimmering effect
    sig = ~stereoSpread.(sig, rippleMod * 0.1, 0.6);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_seagrass_bay_surface_light loaded".postln;
