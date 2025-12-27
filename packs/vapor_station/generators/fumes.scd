// fumes: Chemical vapor shimmer and haze
SynthDef(\forge_vapor_station_fumes, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var volatile, iridescent, toxic, haze, nausea;

    // Theme params
    volatile = In.kr(customBus0).linlin(0, 1, 0.5, 4);     // P1: FM modulation depth
    iridescent = In.kr(customBus1).linlin(0, 1, 0.2, 1);   // P2: Shimmering overtones
    toxic = In.kr(customBus2).linlin(0, 1, 0, 0.5);        // P3: Harsh dissonance
    haze = In.kr(customBus3).linlin(0, 1, 0.1, 0.6);       // P4: Soft blur
    nausea = In.kr(customBus4).linlin(0, 1, 0.1, 1);       // P5: Slow undulation

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

    // DSP: FM shimmer
    sig = PMOsc.ar(
        freq,
        freq * LFNoise1.kr(nausea).range(1.99, 2.01),
        volatile * SinOsc.kr(nausea * 0.3).range(0.5, 1),
        0
    );

    // Iridescent overtones
    sig = sig + (SinOsc.ar(freq * [3, 5.01, 7.02, 9.03]) * iridescent * [0.2, 0.15, 0.1, 0.05]);
    sig = Splay.ar(sig, 0.6);

    // Toxic dissonance
    sig = sig + (SinOsc.ar(freq * [1.06, 1.94]) * toxic * 0.2);

    // Haze blur - filtered copy
    sig = sig + (LPF.ar(sig, 500) * haze);

    sig = sig * 0.3;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_vapor_station_fumes loaded".postln;
