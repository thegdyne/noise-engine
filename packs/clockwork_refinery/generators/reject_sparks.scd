// clockwork_refinery/reject_sparks.scd
// Clockwork Refinery — reject_sparks
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_reject_sparks, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var drf, grt, spc, drp, mod;
    var a, b, c, d, e, f, g, h, i, j, k, l, m, n;

    // Theme params
    drf = In.kr(customBus0).clip(0, 1);
    grt = In.kr(customBus1).clip(0, 1);
    spc = In.kr(customBus2).clip(0, 1);
    drp = In.kr(customBus3).clip(0, 1);
    mod = In.kr(customBus4).clip(0, 1);

    // Standard reads
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5)).clip(20, 20000);
    filterFreq = In.kr(cutoffBus).clip(20, 18000);
    rq = In.kr(resBus).clip(0.05, 2);
    attack = In.kr(attackBus).clip(0, 1);
    decay = In.kr(decayBus).clip(0, 1);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    ampVal = In.kr(~params[\amplitude]);

a = Dust.ar(2 + (mod * 28)) * (1 - (drp * 0.85));
b = Decay2.ar(a, 0.001, 0.02 + (mod * 0.08));
c = WhiteNoise.ar(0.25) * b;

d = (freq * (2 + (mod * 10))).clip(80, 16000);
e = SinOsc.ar(d * (1 + (LFNoise1.kr(0.3).range(-0.02, 0.02) * drf)));

f = (c * e) * (2 + (mod * 3));   // ring mod
g = (f * (1 + (grt * 6))).tanh;

// Under-bed so drone mode is never silent
h = PinkNoise.ar(0.02) * (1 - (drp * 0.9));
i = HPF.ar(h, 120);

// Space tail
j = CombC.ar(g, 0.3, (0.01 + (spc * 0.16)).clip(0.01, 0.22), 0.4 + (spc * 1.4));
sig = (g * 0.9) + (j * 0.5) + (i * 0.3);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
