// dagon: Father of the deep ones - aquatic horror
SynthDef(\forge_rlyeh_dagon, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var bubble, depth, scale, call, ancient;

    // Theme params
    bubble = In.kr(customBus0).linlin(0, 1, 2, 25);        // P1: Bubble rate
    depth = In.kr(customBus1).linlin(0, 1, 0.3, 1);        // P2: Ocean depth filter
    scale = In.kr(customBus2).linlin(0, 1, 0, 0.5);        // P3: Fish scale shimmer
    call = In.kr(customBus3).linlin(0, 1, 0, 0.7);         // P4: Deep one call
    ancient = In.kr(customBus4).linlin(0, 1, 0.3, 1);      // P5: Ancient presence

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

    // DSP: Ancient presence - deep drone
    sig = SinOsc.ar(freq * [0.5, 1, 1.01]) * ancient;
    sig = Splay.ar(sig, 0.5);

    // Bubble texture - stereo array, no .sum needed
    sig = sig + Ringz.ar(Dust.ar(bubble) * 0.2, freq * LFNoise0.kr(bubble).range(2, 5) * [1, 1.03], 0.08);

    // Depth filtering
    sig = LPF.ar(sig, freq * depth * 8);

    // Scale shimmer
    sig = sig + (Blip.ar(freq * 2, LFNoise1.kr(0.5).range(3, 8)) * scale * 0.2);

    // Deep one call - eerie formant
    sig = sig + (Formant.ar(
        freq * 0.5 * LFNoise1.kr(0.3).range(0.95, 1.05),
        freq * 1.5,
        freq * 3
    ) * call * 0.3);

    sig = sig * 0.3;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_rlyeh_dagon loaded".postln;
