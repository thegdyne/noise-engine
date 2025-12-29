// cleanroom_shift/muffled_radio.scd
// Cleanroom Shift — muffled_radio
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_muffled_radio, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

a = (3 + (shf * 30)).clip(3, 36);
b = (0.03 + (shf * 0.10)).clip(0.03, 0.16);
c = Dust.ar(a * (1 - (drp * 0.6)));

d = Mix.fill(7, { |i|
    var ff, pp, ww;
    ww = (0.18 + (i * 0.07)).clip(0.18, 0.6);
    ff = (freq * (0.75 + (i * ww))).clip(80, 6000);
    pp = LFNoise1.kr(0.12 + (drf * 0.5)).range(-1, 1);
    GrainSin.ar(2, c, b, ff, pp, -1, 512, 0.10)
});

e = BPF.ar(d, (900 + (shf * 1800)).clip(300, 3500), 0.4);
f = (e * (1 + (grt * 2.5))).tanh;

g = LFNoise0.kr(0.8 + (shf * 5)).range(0, 1);
h = (1 - ((g * drp) * 0.8)).clip(0.2, 1);

i = CombC.ar(f, 0.35, (0.02 + (spc * 0.22)).clip(0.02, 0.28), 1.0 + (spc * 2.6));

sig = ((f * 0.85) + (i * 0.35)) * h + PinkNoise.ar(0.003);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
