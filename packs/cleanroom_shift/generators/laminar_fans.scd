// cleanroom_shift/laminar_fans.scd
// Cleanroom Shift — laminar_fans
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_laminar_fans, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

a = PinkNoise.ar(0.45) + BrownNoise.ar(0.18);
a = HPF.ar(a, 80);

b = (0.03 + (shf * 0.12)).clip(0.03, 0.2);
c = LFNoise1.kr(b).range(0.6, 1.4);

d = (filterFreq * (0.5 + (c * 0.7))).clip(120, 9000);
e = Resonz.ar(a, d, (0.03 + (rq * 0.06)).clip(0.02, 0.25)) * 8;
f = Resonz.ar(a, (d * 1.6).clip(120, 12000), (0.02 + (rq * 0.05)).clip(0.02, 0.2)) * 6;

g = LFNoise0.kr(0.6 + (shf * 3)).range(0, 1);
h = (g - drp).clip(0.15, 1);
i = (e + f) * h;

j = (i * (1 + (grt * 2.5))).tanh;
k = CombC.ar(j, 0.30, (0.02 + (spc * 0.16)).clip(0.02, 0.22), 1.4 + (spc * 2.0));
sig = (j * 0.95) + (k * 0.45) + PinkNoise.ar(0.012);
sig = sig * (2.5 + (shf * 1.5));   // louder, “shift intensity”
sig = (sig * 1.2).tanh;

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
