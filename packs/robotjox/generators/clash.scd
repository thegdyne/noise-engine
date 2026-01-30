// robotjox/clash — Lightweight end-stage generator
SynthDef(\forge_robotjox_clash, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var impactRate, metal, mass, scrape, chaos;
    var trig, resonances, lowImpact, scrapeNoise, ringTime;

    impactRate = p[0];
    metal = p[1];
    mass = p[2];
    scrape = p[3];
    chaos = p[4];

    freq = In.kr(freqBus);

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

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_robotjox_clash loaded".postln;
