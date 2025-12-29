// cleanroom_shift/airlock_ritual.scd
// Cleanroom Shift — airlock_ritual
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_airlock_ritual, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

a = (Impulse.ar(0) + Dust.ar(0.35 + (shf * 2.8)));
b = Decay2.ar(a, 0.001, 0.08 + (shf * 0.22));
c = WhiteNoise.ar(0.35) * b;

d = (freq * [0.7, 1.0, 1.28]).clip(40, 6000);
e = Ringz.ar(c, d * (1 + (LFNoise1.kr(0.15).range(-0.02, 0.02) * drf)), 0.10 + (shf * 0.35)).sum;

f = Decay2.ar(a, 0.02, 0.6 + (spc * 1.8));
g = HPF.ar(PinkNoise.ar(0.10), 200) * f;
h = BPF.ar(g, (1000 + (shf * 2500)).clip(400, 4000), 0.3);

i = LFNoise0.kr(1.2 + (shf * 5)).range(0, 1);
j = (i - drp).clip(0, 1);
k = ((e * 0.9) + (h * 0.8)) * (0.25 + (j * 0.75));

l = (k * (1 + (grt * 5))).tanh;
m = CombC.ar(l, 0.30, (0.02 + (spc * 0.20)).clip(0.02, 0.25), 0.9 + (spc * 2.2));
sig = (l * 0.85) + (m * 0.45) + PinkNoise.ar(0.003);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
