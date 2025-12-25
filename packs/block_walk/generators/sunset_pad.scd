SynthDef(\forge_block_walk_sunset_pad, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var glow, haze, depth, shift, air;
    var pulse1, pulse2, pulse3, pwm1, pwm2, pwm3, detune;
    var chorus, airNoise;

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
    glow = In.kr(customBus0);       // PWM depth
    haze = In.kr(customBus1);       // Chorus
    depth = In.kr(customBus2);      // Layer count
    shift = In.kr(customBus3);      // Detune
    air = In.kr(customBus4);        // High shimmer

    // Detune amount for layers
    detune = shift.linexp(0, 1, 1.001, 1.015);

    // PWM LFOs at slightly different rates for glow
    pwm1 = SinOsc.kr(0.3).range(0.3, 0.7 - (glow * 0.2));
    pwm2 = SinOsc.kr(0.35).range(0.3 + (glow * 0.1), 0.7);
    pwm3 = SinOsc.kr(0.28).range(0.35, 0.65);

    // Three pulse layers with detune
    pulse1 = Pulse.ar(freq, pwm1);
    pulse2 = Pulse.ar(freq * detune, pwm2) * depth.linlin(0, 1, 0.3, 0.8);
    pulse3 = Pulse.ar(freq / detune, pwm3) * depth.linlin(0, 1, 0.2, 0.6);

    sig = (pulse1 + pulse2 + pulse3) * 0.25;

    // Chorus via modulated delay
    chorus = DelayC.ar(sig, 0.05,
        SinOsc.kr(0.5).range(0.005, 0.015 + (haze * 0.015))
    );
    chorus = chorus + DelayC.ar(sig, 0.05,
        SinOsc.kr(0.63, pi * 0.5).range(0.007, 0.018 + (haze * 0.012))
    );

    sig = sig + (chorus * haze.linlin(0, 1, 0.2, 0.6));

    // Air layer - filtered noise shimmer
    airNoise = BPF.ar(PinkNoise.ar(0.1), 6000 + (LFNoise1.kr(0.5) * 2000), 0.3);
    airNoise = airNoise * LFNoise1.kr(2).range(0.3, 1);
    sig = sig + (airNoise * air.linlin(0, 1, 0, 0.25));

    // Soft saturation
    sig = sig.tanh * 0.8;

    // Output chain
    sig = ~stereoSpread.(sig, 0.15, haze.linlin(0, 1, 0.3, 0.7));
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_block_walk_sunset_pad loaded".postln;
