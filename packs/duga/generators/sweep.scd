SynthDef(\forge_duga_sweep, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var span, speed, depth, ring, echo;
    var sweepOsc, modulator, carrier, echoSig, sweepFreq;

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

    // Custom params
    span = In.kr(customBus0);
    speed = In.kr(customBus1);
    depth = In.kr(customBus2);
    ring = In.kr(customBus3);
    echo = In.kr(customBus4);

    // Sweep oscillator - slow rotation
    sweepOsc = SinOsc.kr(speed.linexp(0, 1, 0.05, 1));
    sweepFreq = freq * sweepOsc.range(1 - (span * 0.5), 1 + (span * 0.5));

    // Phase modulation FM
    modulator = SinOsc.ar(sweepFreq * 2, 0, depth.linlin(0, 1, 0.5, 4));
    carrier = SinOsc.ar(sweepFreq, modulator);

    // Add resonant ringing
    sig = carrier + (Ringz.ar(carrier * 0.1, sweepFreq * 3, ring.linlin(0, 1, 0.05, 0.3)) * ring);

    sig = sig * 0.4;

    // Radar echo returns - delayed copies
    echoSig = CombL.ar(sig, 0.5, echo.linlin(0, 1, 0.05, 0.3), echo.linlin(0, 1, 0.1, 1));
    sig = sig + (echoSig * echo * 0.4);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_duga_sweep loaded".postln;
