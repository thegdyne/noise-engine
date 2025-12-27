// cascade: Main curtain of falling water
SynthDef(\forge_sgwd_cascade, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var width, weight, height, foam, veil;

    // Theme params
    width = In.kr(customBus0).linlin(0, 1, 0.3, 1);           // P1: Curtain width
    weight = In.kr(customBus1).linlin(0, 1, 200, 800);        // P2: Water weight (LPF)
    height = In.kr(customBus2).linlin(0, 1, 0.2, 0.8);        // P3: Drop height (pitch)
    foam = In.kr(customBus3).linlin(0, 1, 0.1, 0.5);          // P4: White foam
    veil = In.kr(customBus4).linlin(0, 1, 0.2, 0.7);          // P5: Veil texture

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

    // DSP: Layered falling water
    // Main cascade body - filtered noise
    sig = BrownNoise.ar(width) + PinkNoise.ar(width * 0.5);
    sig = LPF.ar(sig, weight);
    sig = sig * LFNoise1.kr(3).range(0.8, 1);  // Gentle variation

    // Foam layer - bright hiss
    sig = sig + (WhiteNoise.ar(foam) * HPF.ar(WhiteNoise.ar(0.3), 3000));

    // Height creates pitch content
    sig = sig + (Resonz.ar(PinkNoise.ar(height * 0.4), freq * [1, 1.5, 2], 0.15).sum);

    // Veil texture - delicate high frequencies
    sig = sig + (BPF.ar(WhiteNoise.ar(veil * 0.3), 4000 * LFNoise1.kr(0.5).range(0.8, 1.2), 0.3));

    sig = sig * 0.35;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_sgwd_cascade loaded".postln;
