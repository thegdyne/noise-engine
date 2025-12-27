// vault: Vast stone chamber resonance
SynthDef(\forge_drowned_temple_vault, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var size, stone, echo, darkness, age;

    // Theme params
    size = In.kr(customBus0).linlin(0, 1, 0.3, 0.9);        // P1: Chamber size
    stone = In.kr(customBus1).linlin(0, 1, 0.3, 0.9);       // P2: Stone resonance (boosted)
    echo = In.kr(customBus2).linlin(0, 1, 0.2, 0.7);        // P3: Echo density
    darkness = In.kr(customBus3).linlin(0, 1, 400, 2500);   // P4: Damping darkness (brighter)
    age = In.kr(customBus4).linlin(0, 1, 0.2, 0.6);         // P5: Ancient dust

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

    // DSP: Base drone - pitched to freq (boosted)
    sig = SinOsc.ar(freq * [0.5, 1, 1.002]) * stone * 0.5;
    sig = Splay.ar(sig, 0.5);

    // Chamber reverb via comb (boosted input)
    sig = sig + CombL.ar(sig * 0.3, 0.3, size * 0.12 + 0.03, size * 3);

    // Sparse echo reflections (boosted)
    sig = sig + (Ringz.ar(Dust.ar(echo * 5) * 0.2, freq * [1, 1.5, 2], size * 1.5) * echo * 0.5);

    // Darkness filter
    sig = LPF.ar(sig, darkness);

    // Ancient dust texture (boosted)
    sig = sig + (LPF.ar(PinkNoise.ar(age * 0.5), 800));

    sig = sig * 0.5;

    // Output chain (with Limiter for comb)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_drowned_temple_vault loaded".postln;
