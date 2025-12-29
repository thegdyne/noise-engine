SynthDef(\forge_kaiju_beats_kaiju, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var throat, roar, breath, vowel, size;
    var source, formants, f1, f2, f3, breathNoise;

    // Theme params
    throat = In.kr(customBus0);       // P1: Throat size - formant spacing
    roar = In.kr(customBus1);         // P2: Roar intensity - distortion
    breath = In.kr(customBus2);       // P3: Breath noise mix
    vowel = In.kr(customBus3);        // P4: Vowel morph (A-O-U)
    size = In.kr(customBus4);         // P5: Monster size - pitch shift

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
    ampVal = 0.2;

    // Source - pulse with size scaling
    freq = freq * (1 - (size * 0.5));
    source = Pulse.ar(freq, 0.3 + (LFNoise1.kr(2) * 0.1));
    source = source + (Saw.ar(freq * 0.999) * 0.5);

    // Add growl modulation
    source = source * (1 + (LFNoise2.kr(3 + (roar * 8)) * roar * 0.5));

    // Formant frequencies - monster vowels
    f1 = LinXFade2.kr(800, 400, vowel * 2 - 1) * (1 - (throat * 0.3));
    f2 = LinXFade2.kr(1200, 800, vowel * 2 - 1) * (1 - (throat * 0.3));
    f3 = LinXFade2.kr(2500, 2200, vowel * 2 - 1) * (1 - (throat * 0.3));

    // Formant filters with gain boost
    formants = BPF.ar(source, f1, 0.1) * 4;
    formants = formants + (BPF.ar(source, f2, 0.12) * 3);
    formants = formants + (BPF.ar(source, f3, 0.15) * 2);

    // Breath noise
    breathNoise = BPF.ar(PinkNoise.ar(1), f1 * 1.5, 0.2) * breath * 0.4;

    // Mix and soft clip for roar
    sig = formants + breathNoise;
    sig = (sig * (1 + (roar * 3))).tanh;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_kaiju_beats_kaiju loaded".postln;
