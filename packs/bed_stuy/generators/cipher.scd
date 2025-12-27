// cipher: MC vocal presence - formant drone
SynthDef(\forge_bed_stuy_cipher, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var voice, flow, breath, crowd, hype;

    // Theme params
    voice = In.kr(customBus0).linlin(0, 1, 0.3, 1);         // P1: Voice presence
    flow = In.kr(customBus1).linlin(0, 1, 0.05, 0.3);       // P2: Flow modulation
    breath = In.kr(customBus2).linlin(0, 1, 0.1, 0.5);      // P3: Breath texture
    crowd = In.kr(customBus3).linlin(0, 1, 0, 0.4);         // P4: Crowd murmur
    hype = In.kr(customBus4).linlin(0, 1, 0, 0.5);          // P5: Hype energy

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

    // DSP: Vocal formant drone
    sig = Formant.ar(
        freq * LFNoise1.kr(flow).range(0.98, 1.02),
        freq * 3 * LFNoise1.kr(flow * 0.7).range(0.9, 1.1),
        freq * 6
    ) * voice * 0.4;

    // Breath - aspirant noise
    sig = sig + (BPF.ar(PinkNoise.ar(breath), freq * 4, 0.3) * LFNoise1.kr(0.3).range(0.5, 1) * 0.5);

    // Crowd murmur - filtered noise
    sig = sig + (BPF.ar(PinkNoise.ar(crowd), 500 * LFNoise0.kr(0.5).range(0.7, 1.4), 0.3));

    // Hype energy - bright bursts
    sig = sig + (Ringz.ar(Dust.ar(hype * 8) * 0.15, freq * [4, 6], 0.05) * hype);

    sig = sig * 0.45;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_bed_stuy_cipher loaded".postln;
