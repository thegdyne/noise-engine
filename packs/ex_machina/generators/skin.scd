// skin: Synthetic flesh - soft, uncanny
SynthDef(\forge_ex_machina_skin, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var texture, warmth, uncanny, membrane, touch;

    // Theme params
    texture = In.kr(customBus0).linlin(0, 1, 0.3, 0.9);     // P1: Skin texture
    warmth = In.kr(customBus1).linlin(0, 1, 500, 2500);     // P2: Body warmth filter
    uncanny = In.kr(customBus2).linlin(0, 1, 0.1, 0.5);     // P3: Uncanny quality
    membrane = In.kr(customBus3).linlin(0, 1, 0.3, 0.8);    // P4: Membrane flex
    touch = In.kr(customBus4).linlin(0, 1, 2, 12);          // P5: Touch sensitivity

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

    // DSP: Continuous body warmth tone (always present)
    sig = SinOsc.ar(freq * [0.5, 1]) * texture * 0.35;

    // Soft skin texture - filtered noise
    sig = sig + (LPF.ar(PinkNoise.ar(texture * 0.5), warmth));

    // Membrane flex - low resonance (boosted)
    sig = sig + (Ringz.ar(Dust.ar(touch) * 0.2, freq * [0.5, 1, 1.5], 0.25) * membrane * 0.5);

    // Uncanny quality - slight wrongness
    sig = sig + (SinOsc.ar(freq * LFNoise1.kr(0.05).range(0.98, 1.02) * [1, 1.003]) * uncanny * 0.25);

    // Touch response
    sig = sig + (LPF.ar(Dust2.ar(touch * 2) * 0.15, warmth));

    sig = LPF.ar(sig, warmth * 1.5) * 0.5;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ex_machina_skin loaded".postln;
