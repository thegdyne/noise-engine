// clockwork_refinery/mainspring.scd
// Clockwork Refinery — mainspring
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_mainspring, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

a = (0.15 + (drf * 0.35)).clip(0.15, 0.6);
b = (0.2 + (mod * 0.75)).clip(0.2, 0.95); // pulse width-ish
c = Pulse.ar(freq * (1 + (LFNoise1.kr(a).range(-0.01, 0.01) * drf)), b) * 0.35;
d = SinOsc.ar(freq * 0.5) * 0.12;
e = c + d;

// "Spring tension" sweep into a narrow band
f = (freq * (1.5 + (mod * 6))).clip(80, 14000);
g = RLPF.ar(e, f, (0.12 + (mod * 0.5)).clip(0.12, 0.9)) * (1.5 + (mod * 1.5));

// Dropout + grit
h = g * (1 - (drp * 0.75));
i = (h * (1 + (grt * 6))).tanh;

// Space
j = CombC.ar(i, 0.25, (0.01 + (spc * 0.16)).clip(0.01, 0.22), 0.7 + (spc * 2.0));
sig = (i * 0.85) + (j * 0.4);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
