// clockwork_refinery/selector_dial.scd
// Clockwork Refinery — selector_dial
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / instability
// P2 GRT: grit / saturation
// P3 SPC: space / chamber
// P4 DRP: dropout / missing teeth
// P5 MOD: mode / coarse↔fine morph

SynthDef(\forge_clockwork_refinery_selector_dial, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

// Dial steps (hybrid initial + occasional)
a = Impulse.kr(0) + Dust.kr(0.3 + (mod * 3));
b = Stepper.kr(a, 0, 0, 3, 1);  // 0..3
c = b / 3; // 0..1 for SelectX

d = SinOsc.ar(freq);
e = LFTri.ar(freq);
f = Saw.ar(freq);
g = Pulse.ar(freq, 0.5);

// Morph with a stepped center + drift wiggle
h = (c + (LFNoise1.kr(0.2).range(-0.12, 0.12) * drf)).clip(0, 1);
i = SelectX.ar(h * 3, [d, e, f, g]) * 0.35;

// Processing: dropout = missing cycles, grit = crush
j = (LFNoise0.kr(10 + (mod * 30)).range(0, 1) > drp).asInteger;
k = i * j;
l = (k * (1 + (grt * 8))).tanh;

// Space
m = CombC.ar(l, 0.3, (0.012 + (spc * 0.18)).clip(0.012, 0.25), 0.9 + (spc * 2.6));
sig = (l * 0.85) + (m * 0.45);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_clockwork_refinery loaded".postln;
