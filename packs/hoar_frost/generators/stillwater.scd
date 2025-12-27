// stillwater: Frozen lake surface - deep slow pad
SynthDef(\forge_hoar_frost_stillwater, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var depth, ice, movement, sub, clarity;

    // Theme params
    depth = In.kr(customBus0).linlin(0, 1, 0.5, 2);        // P1: Sub octave depth
    ice = In.kr(customBus1).linlin(0, 1, 0, 0.5);          // P2: Icy overtone
    movement = In.kr(customBus2).linlin(0, 1, 0.01, 0.2);  // P3: Slow drift rate
    sub = In.kr(customBus3).linlin(0, 1, 0, 0.8);          // P4: Sub level
    clarity = In.kr(customBus4).linlin(0, 1, 0.1, 0.9);    // P5: Waveform clarity

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

    // DSP: Deep pad with slow modulation
    sig = VarSaw.ar(freq, 0, LFNoise1.kr(movement).range(0.3, 0.7)) * clarity;
    sig = sig + (SinOsc.ar(freq) * (1 - clarity));
    sig = sig + (SinOsc.ar(freq / depth) * sub * 0.5);
    sig = sig + (SinOsc.ar(freq * 3) * ice * LFNoise1.kr(movement * 2).range(0, 1) * 0.2);

    // Slow stereo movement
    sig = Pan2.ar(sig, SinOsc.kr(movement * 0.5).range(-0.3, 0.3));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_hoar_frost_stillwater loaded".postln;
