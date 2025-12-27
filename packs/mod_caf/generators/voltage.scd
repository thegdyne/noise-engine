// voltage: CV modulation textures - stepped random, chaos
SynthDef(\forge_mod_caf_voltage, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var stepRate, chaos, slew, depth, bipolar;
    var stepped, chaotic;

    // Theme params
    stepRate = In.kr(customBus0).linlin(0, 1, 0.5, 15);     // P1: Step rate
    chaos = In.kr(customBus1).linlin(0, 1, 1.5, 1.99);      // P2: Chaos amount
    slew = In.kr(customBus2).linlin(0, 1, 0.001, 0.2);      // P3: Slew limiting
    depth = In.kr(customBus3).linlin(0, 1, 0.3, 1);         // P4: Modulation depth
    bipolar = In.kr(customBus4).linlin(0, 1, 0, 0.5);       // P5: Bipolar offset

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

    // DSP: Stepped random - S&H style
    stepped = LFNoise0.kr(stepRate).lag(slew);

    // Chaotic - Lorenz-style via Crackle
    chaotic = Crackle.ar(chaos);

    // Modulated oscillator
    sig = SinOsc.ar(freq * (1 + (stepped * depth * 0.5))) * 0.3;
    sig = sig + (Pulse.ar(freq * (1 + (stepped * depth * 0.3)), 0.3 + (chaotic * 0.2)) * 0.2);

    // Chaos texture layer
    sig = sig + (BPF.ar(chaotic, freq * 2, 0.3) * depth * 0.3);

    // Bipolar offset adds asymmetry
    sig = sig + (SinOsc.ar(freq * 0.5) * bipolar * 0.2);

    sig = sig * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_mod_caf_voltage loaded".postln;
