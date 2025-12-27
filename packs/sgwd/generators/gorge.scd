// gorge: Hollow space behind waterfall
SynthDef(\forge_sgwd_gorge, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var depth, echo, dark, behind, ancient;

    // Theme params
    depth = In.kr(customBus0).linlin(0, 1, 0.03, 0.1);        // P1: Gorge depth (comb)
    echo = In.kr(customBus1).linlin(0, 1, 1, 4);              // P2: Echo decay
    dark = In.kr(customBus2).linexp(0, 1, 400, 100);          // P3: Darkness (LPF)
    behind = In.kr(customBus3).linlin(0, 1, 0.2, 0.6);        // P4: Behind falls
    ancient = In.kr(customBus4).linlin(0, 1, 0.1, 0.4);       // P5: Ancient presence

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

    // DSP: Cavernous gorge
    // Deep drone
    sig = SinOsc.ar(freq * [0.25, 0.5, 1] * LFNoise1.kr(0.03).range(0.98, 1.02)) * [0.4, 0.3, 0.2];
    sig = sig.sum;

    // Dark filtered noise
    sig = sig + (LPF.ar(BrownNoise.ar(0.4), dark) * behind);

    // Gorge resonance
    sig = CombL.ar(sig, 0.2, depth, echo);

    // Allpass diffusion
    sig = AllpassL.ar(sig, 0.1, 0.037, echo * 0.5);
    sig = AllpassL.ar(sig, 0.1, 0.059, echo * 0.4);

    // Ancient presence
    sig = sig + (SinOsc.ar(freq * 0.125) * ancient * 0.3);

    // Muffled waterfall sound from behind
    sig = sig + (LPF.ar(PinkNoise.ar(behind * 0.3), 300));

    sig = sig * 0.35;

    // Output chain (with Limiter for comb)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_sgwd_gorge loaded".postln;
