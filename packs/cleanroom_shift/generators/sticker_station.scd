// cleanroom_shift/sticker_station.scd
// Cleanroom Shift — sticker_station
// Generated from GENERATOR_PACK_SESSION.md contract
//
// P1 DRF: drift / fatigue / micro instability
// P2 GRT: grit / switching hash
// P3 SPC: space / duct bloom
// P4 DRP: dropout / interlock gating
// P5 SHF: shift state (timeless cycle intensity)

SynthDef(\forge_cleanroom_shift_sticker_station, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                    filterTypeBus, envEnabledBus, envSourceBus=0,
                                    clockRateBus, clockTrigBus,
                                    midiTrigBus=0, slotIndex=0,
                                    customBus0, customBus1, customBus2, customBus3, customBus4,
                                    portamentoBus|

    var sig, trig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var drf, grt, spc, drp, shf;
    var a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p, q, bed;

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

a = (2 + (shf * 10)).clip(2, 14);
b = LFPulse.kr(a, 0, (0.12 + (shf * 0.35)).clip(0.12, 0.8)).lag(0.003);
c = Dust.kr(0.3 + (shf * 2.0));
d = (b + (c * 0.4)).clip(0.0, 1.0);
d = d + 0.25;   // stronger constant peel energy in drone render
d = d.clip(0, 1);


e = WhiteNoise.ar(0.22) * d;
f = BPF.ar(e, (900 + (shf * 2600)).clip(300, 5000), 0.3);

// Drone-safe machine bed (rollers / airflow)
bed = HPF.ar(PinkNoise.ar(0.04), 600);
bed = BPF.ar(bed, (700 + (shf * 900)).clip(300, 2000), 0.5);
f = f + (bed * (0.6 + (shf * 0.6)));

g = Dust.ar(0.15 + (shf * 1.2)) * (1 - (drp * 0.7));
h = Decay2.ar(g, 0.001, 0.03);
i = SinOsc.ar((2000 + (shf * 1200)).clip(800, 4000)) * h * 0.25;

j = LFNoise0.kr(1.6 + (shf * 8)).range(0, 1);
k = (j - drp).clip(0.55, 1);   // never starves the station

l = (f + i) * k;
l = l + HPF.ar(PinkNoise.ar(0.06), 800);   // unconditional machine-air bed

m = (l * (1 + (grt * 5))).tanh;
n = CombC.ar(m, 0.20, (0.01 + (spc * 0.10)).clip(0.01, 0.14), 0.35 + (spc * 1.2));
sig = (m * 0.9) + (n * 0.35) + HPF.ar(PinkNoise.ar(0.01), 500);

    // MANDATORY output chain (this order):
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_cleanroom_shift loaded".postln;
