SynthDef(\forge_robotjox_clash, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var impactRate, metal, mass, scrape, chaos;
    var trig, resonances, lowImpact, scrapeNoise, ringTime;

    // Theme params
    impactRate = In.kr(customBus0);
    metal = In.kr(customBus1);
    mass = In.kr(customBus2);
    scrape = In.kr(customBus3);
    chaos = In.kr(customBus4);

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

    // Impact trigger
    trig = Dust.ar(impactRate.linexp(0, 1, 1, 20));

    // Ring time based on metal
    ringTime = metal.linexp(0, 1, 0.1, 0.5);

    // Metal resonances - various collision pitches
    resonances = Ringz.ar(trig, freq * (1 + (LFNoise0.kr(5) * chaos * 0.3)), ringTime, 0.3);
    resonances = resonances + Ringz.ar(trig, freq * 1.7 * (1 + (LFNoise0.kr(4) * chaos * 0.2)), ringTime * 0.7, 0.25);
    resonances = resonances + Ringz.ar(trig, freq * 2.4 * (1 + (LFNoise0.kr(3) * chaos * 0.25)), ringTime * 0.5, 0.2);
    resonances = resonances + Ringz.ar(trig, freq * 3.2, ringTime * 0.4, 0.15 * metal);
    resonances = resonances + Ringz.ar(trig, freq * 4.5, ringTime * 0.3, 0.1 * metal);

    // Low mass impact
    lowImpact = Ringz.ar(trig, freq * 0.5, ringTime * 1.5, 0.35 * mass);
    lowImpact = lowImpact + (SinOsc.ar(freq * 0.25, 0, 0.3 * mass) * Decay.ar(trig, 0.3));

    sig = (resonances + lowImpact) * 0.5;

    // Impact transient
    sig = sig + (HPF.ar(WhiteNoise.ar(0.5), 500) * Decay.ar(trig, 0.02));

    // Metal scrape - continuous friction
    scrapeNoise = BPF.ar(Crackle.ar(1.7, 0.3), freq * 2 * LFNoise1.kr(3).range(0.8, 1.2), 0.2) * 2;
    scrapeNoise = scrapeNoise * LFNoise2.kr(2 + (scrape * 5)).range(0.3, 1.0);
    sig = sig + (scrapeNoise * scrape);

    // Continuous metal hum
    sig = sig + BPF.ar(BrownNoise.ar(0.2), freq, 0.25) * 2;

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.1), 400);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_robotjox_clash loaded".postln;
