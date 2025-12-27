// ava: AI consciousness - questioning, aware
SynthDef(\forge_ex_machina_ava, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var aware, question, soft, human, machine;

    // Theme params
    aware = In.kr(customBus0).linlin(0, 1, 0.3, 1);         // P1: Awareness level
    question = In.kr(customBus1).linlin(0, 1, 0.05, 0.2);   // P2: Questioning inflection
    soft = In.kr(customBus2).linlin(0, 1, 500, 3000);       // P3: Softness filter
    human = In.kr(customBus3).linlin(0, 1, 0.1, 0.5);       // P4: Human breath
    machine = In.kr(customBus4).linlin(0, 1, 0, 0.3);       // P5: Machine undertone

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

    // DSP: Formant voice - soft, questioning
    sig = Formant.ar(
        freq * LFNoise1.kr(question).range(0.98, 1.02),
        freq * 3 * LFNoise1.kr(question * 0.5).range(0.9, 1.1),
        freq * 5
    ) * aware * 0.35;

    // Human breath texture
    sig = sig + (BPF.ar(PinkNoise.ar(human), freq * 3, 0.3) * LFNoise1.kr(0.2).range(0.5, 1) * 0.4);

    // Machine undertone - subtle digital
    sig = sig + (Pulse.ar(freq * [1, 1.001], 0.3) * machine * 0.15);

    // Softness filter
    sig = LPF.ar(sig, soft);

    // Continuous awareness hum
    sig = sig + (SinOsc.ar(freq * 0.5) * aware * 0.15);

    sig = sig * 0.45;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ex_machina_ava loaded".postln;
