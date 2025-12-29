// cleanroom_shift/actuator_servo.scd
// Cleanroom Shift — actuator_servo
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_actuator_servo, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
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

a = (0.06 + (shf * 0.35)).clip(0.06, 0.6);
b = LFNoise1.kr(a).range(-1, 1) * (0.02 + (drf * 0.08));
c = (freq * (8 + (shf * 24))).clip(80, 14000);
d = SinOsc.ar(c * (1 + b)) * 0.25;

e = LFNoise0.kr(4 + (shf * 28)).range(-1, 1);
f = (e * (0.01 + (drf * 0.06)));
g = SinOsc.ar(c * (1 + f)) * 0.22;

h = HPF.ar(WhiteNoise.ar(0.08), 2500) * (0.4 + (grt * 1.2));

i = d + g + h;
j = LFNoise0.kr(0.8 + (shf * 5)).range(0, 1);
k = (j - drp).clip(0.2, 1);
l = i * k;

m = (l * (1 + (grt * 3))).tanh;
n = CombC.ar(m, 0.22, (0.01 + (spc * 0.12)).clip(0.01, 0.16), 0.5 + (spc * 1.4));
sig = (m * 0.85) + (n * 0.35) + PinkNoise.ar(0.002);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
