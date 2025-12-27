// hymn: Ancient prayer echoing through ruins
SynthDef(\forge_drowned_temple_hymn, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var voice, choir, sacred, ancient, fade;

    // Theme params
    voice = In.kr(customBus0).linlin(0, 1, 0.3, 1);         // P1: Voice level
    choir = In.kr(customBus1).linlin(0, 1, 1, 4);           // P2: Choir voices
    sacred = In.kr(customBus2).linlin(0, 1, 0.1, 0.6);      // P3: Sacred harmonics
    ancient = In.kr(customBus3).linlin(0, 1, 0.05, 0.2);    // P4: Ancient waver
    fade = In.kr(customBus4).linlin(0, 1, 0.2, 0.7);        // P5: Fade into distance

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

    // DSP: Formant voice drone
    sig = Formant.ar(
        freq * LFNoise1.kr(ancient).range(0.98, 1.02),
        freq * 2 * LFNoise1.kr(ancient * 0.7).range(0.95, 1.05),
        freq * 4
    ) * voice;

    // Choir - detuned copies
    sig = sig + (Formant.ar(
        freq * 1.003 * LFNoise1.kr(ancient).range(0.98, 1.02),
        freq * 2.5,
        freq * 5
    ) * voice * (choir / 4));

    // Sacred harmonics
    sig = sig + (SinOsc.ar(freq * [1.5, 2, 3]) * sacred * 0.15);

    // Distance blur
    sig = LPF.ar(sig, 2000 * (1 - (fade * 0.5)));

    sig = sig * 0.3;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_drowned_temple_hymn loaded".postln;
