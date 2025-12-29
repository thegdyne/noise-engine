SynthDef(\forge_duga_steel, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var gust, tube, wire, ratt, cold;
    var windNoise, gustMod, tubeSig, wireSig, rattSig, combs;

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

    // Custom params
    gust = In.kr(customBus0);
    tube = In.kr(customBus1);
    wire = In.kr(customBus2);
    ratt = In.kr(customBus3);
    cold = In.kr(customBus4);

    // Wind gust modulation - always some wind
    gustMod = LFNoise2.kr(gust.linexp(0, 1, 0.1, 1)).range(0.5, 1);
    gustMod = gustMod * LFNoise2.kr(0.2).range(0.7, 1);

    // Base wind noise - continuous
    windNoise = PinkNoise.ar(1) * (0.3 + (gustMod * 0.4));

    // Comb resonators for hollow tubes
    combs = CombL.ar(windNoise, 0.1, freq.reciprocal, tube.linlin(0, 1, 0.1, 1));
    combs = combs + CombL.ar(windNoise, 0.1, (freq * 1.5).reciprocal, tube.linlin(0, 1, 0.1, 0.8));
    combs = combs + CombL.ar(windNoise, 0.1, (freq * 2.2).reciprocal, tube.linlin(0, 1, 0.1, 0.6));
    tubeSig = combs * tube * 0.6;

    // Wire singing - high pitched resonance
    wireSig = Resonz.ar(windNoise, freq * 4 * LFNoise2.kr(0.3).range(0.9, 1.1), 0.01);
    wireSig = wireSig * wire * 10;

    // Rattling loose parts
    rattSig = Dust.ar(ratt.linexp(0, 1, 1, 20) * gustMod) * 0.3;
    rattSig = Ringz.ar(rattSig, freq * LFNoise0.kr(5).range(2, 6), 0.05);
    rattSig = rattSig * ratt;

    // Mix
    sig = windNoise + tubeSig + wireSig + rattSig;

    // Cold wind - add high frequency
    sig = sig + (HPF.ar(WhiteNoise.ar(1), 4000) * cold * gustMod * 0.15);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_duga_steel loaded".postln;
