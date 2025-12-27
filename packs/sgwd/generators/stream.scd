// stream: Foreground water over rocks
SynthDef(\forge_sgwd_stream, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var flow, bubble, rocks, shallow, eddy;

    // Theme params
    flow = In.kr(customBus0).linlin(0, 1, 0.3, 0.8);          // P1: Flow rate
    bubble = In.kr(customBus1).linlin(0, 1, 5, 30);           // P2: Bubble rate
    rocks = In.kr(customBus2).linlin(0, 1, 0.2, 0.6);         // P3: Over rocks
    shallow = In.kr(customBus3).linexp(0, 1, 500, 2000);      // P4: Shallow brightness
    eddy = In.kr(customBus4).linlin(0, 1, 0.5, 3);            // P5: Eddy rate

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

    // DSP: Bubbling stream
    // Main flow
    sig = BPF.ar(PinkNoise.ar(flow), shallow, 0.5);
    sig = sig * LFNoise1.kr(eddy).range(0.7, 1);

    // Bubbling
    sig = sig + (Ringz.ar(Dust.ar(bubble) * 0.2, freq * [2, 3, 4, 5], 0.08).sum);

    // Over rocks - irregular splashes
    sig = sig + (BPF.ar(Crackle.ar(1.8, rocks * 0.3), 1500, 0.4));

    // Eddy swirls
    sig = sig + (BPF.ar(PinkNoise.ar(0.2), 800 * SinOsc.kr(eddy).range(0.7, 1.3), 0.3) * LFNoise1.kr(eddy).range(0.3, 1));

    sig = sig * 0.4;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_sgwd_stream loaded".postln;
