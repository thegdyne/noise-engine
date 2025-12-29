// cleanroom_shift/ballast_white.scd
// Cleanroom Shift — ballast_white
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_ballast_white, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

a = (50 + (shf * 30));
b = SinOsc.ar(a) * 0.10;
c = SinOsc.ar(a * (2.01 + (drf * 0.08))) * 0.06;
d = SinOsc.ar(a * (3.97 + (drf * 0.12))) * 0.04;
e = b + c + d;

f = SinOsc.ar((freq * (6 + (shf * 24))).clip(120, 12000));
g = (e * f) * (0.8 + (grt * 2.2));

h = Dust.ar(0.3 + (shf * 2.5)) * (1 - (drp * 0.8));
i = Decay2.ar(h, 0.001, 0.015 + (shf * 0.05));
j = WhiteNoise.ar(0.30) * i;
k = BPF.ar(j, (3000 + (shf * 9000)).clip(1000, 12000), 0.2);

l = (g + (k * 0.7));
m = (l * (1 + (grt * 3))).tanh;
n = CombC.ar(m, 0.20, (0.01 + (spc * 0.08)).clip(0.01, 0.12), 0.5 + (spc * 1.2));
sig = (m * 0.85) + (n * 0.35) + PinkNoise.ar(0.002);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
