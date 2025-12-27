// test: Acoustic test tones - calibration signals
SynthDef(\forge_mod_caf_test, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var sine, pink, sweep, click, reference;
    var sweepFreq;

    // Theme params
    sine = In.kr(customBus0).linlin(0, 1, 0.2, 0.8);        // P1: Sine level
    pink = In.kr(customBus1).linlin(0, 1, 0, 0.5);          // P2: Pink noise
    sweep = In.kr(customBus2).linlin(0, 1, 0, 0.5);         // P3: Sweep amount
    click = In.kr(customBus3).linlin(0, 1, 0.5, 4);         // P4: Click rate
    reference = In.kr(customBus4).linlin(0, 1, 0, 0.4);     // P5: Reference tone (1kHz)

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

    // DSP: Pure sine test tone
    sig = SinOsc.ar(freq) * sine * 0.4;

    // Pink noise - broadband test
    sig = sig + (PinkNoise.ar(pink) * 0.4);

    // Sweep - slow frequency sweep around base
    sweepFreq = freq * LFTri.kr(0.1).range(0.5, 2);
    sig = sig + (SinOsc.ar(sweepFreq) * sweep * 0.3);

    // Click track - timing reference
    sig = sig + (Ringz.ar(Impulse.ar(click), 1000, 0.01) * 0.2);

    // 1kHz reference tone
    sig = sig + (SinOsc.ar(1000) * reference * 0.3);

    sig = sig * 0.45;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_mod_caf_test loaded".postln;
