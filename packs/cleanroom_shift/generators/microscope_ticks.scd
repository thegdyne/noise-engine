// cleanroom_shift/microscope_ticks.scd
// Cleanroom Shift — microscope_ticks
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_microscope_ticks, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var drf, grt, spc, drp, shf;
    var a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q;

    // Theme params
    drf = In.kr(customBus0).clip(0, 1);
    grt = In.kr(customBus1).clip(0, 1);
    spc = In.kr(customBus2).clip(0, 1);
    drp = In.kr(customBus3).clip(0, 1);
    shf = In.kr(customBus4).clip(0, 1);

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

a = Dust.ar(1.2 + (shf * 12)) * (1 - (drp * 0.75));
b = Decay2.ar(a, 0.001, 0.012 + (shf * 0.05));
c = WhiteNoise.ar(0.22) * b;

d = (freq * [2.0, 2.7, 3.9]).clip(200, 12000);
e = Ringz.ar(c, d * (1 + (LFNoise1.kr(0.25).range(-0.01, 0.01) * drf)), 0.04 + (shf * 0.14)).sum;

f = HPF.ar(PinkNoise.ar(0.015), 500);
g = HPF.ar(e, 250);
h = (g * (1 + (grt * 4))).tanh;

i = CombC.ar(h, 0.12, (0.008 + (spc * 0.06)).clip(0.008, 0.09), 0.25 + (spc * 0.6));
sig = (h * 0.9) + (i * 0.35) + (f * 0.35);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
