// vinyl: Record crackle and lo-fi warmth
SynthDef(\forge_bed_stuy_vinyl, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var crackle, warmth, dust, hiss, worn;

    // Theme params
    crackle = In.kr(customBus0).linlin(0, 1, 5, 50);        // P1: Crackle density
    warmth = In.kr(customBus1).linlin(0, 1, 0.3, 1);        // P2: Warm saturation
    dust = In.kr(customBus2).linlin(0, 1, 0, 0.4);          // P3: Dust pops
    hiss = In.kr(customBus3).linlin(0, 1, 0, 0.3);          // P4: Surface hiss
    worn = In.kr(customBus4).linlin(0, 1, 500, 3000);       // P5: Worn frequency

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

    // DSP: Warm base tone - saturated
    sig = SinOsc.ar(freq * [1, 1.002]) * warmth;
    sig = (sig * 2).tanh * 0.5;  // Soft saturation

    // Crackle texture
    sig = sig + (HPF.ar(Dust2.ar(crackle) * 0.15, 800));

    // Dust pops - occasional loud clicks
    sig = sig + (Ringz.ar(Dust.ar(dust * 3) * 0.2, 1500, 0.01));

    // Surface hiss
    sig = sig + (BPF.ar(WhiteNoise.ar(hiss), worn, 0.5) * 0.5);

    // Lo-fi filter
    sig = LPF.ar(sig, worn);

    sig = sig * 0.45;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_bed_stuy_vinyl loaded".postln;
