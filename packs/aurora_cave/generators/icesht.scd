// aurora_cave/icesht — Lightweight end-stage generator
SynthDef(\forge_aurora_cave_icesht, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var crack, stress, thick, brittle, sheet;
    var crackle, snap, thud, body, trig;

    freq = In.kr(freqBus);

    crack = p[0];
    stress = p[1];
    thick = p[2];
    brittle = p[3];
    sheet = p[4];

    // Crackle impulses at varying densities
    trig = Dust.ar(crack.linexp(0, 1, 1, 40));

    // High frequency snap/crack
    snap = trig * TRand.ar(0.3, 1, trig);
    snap = Ringz.ar(snap, TRand.ar(3000, 8000, trig) * brittle.linlin(0, 1, 0.5, 1.5), 0.02);
    snap = snap + Ringz.ar(snap * 0.5, TRand.ar(5000, 12000, trig), 0.01);
    snap = snap * brittle;

    // Low thud from thick ice
    thud = trig * TRand.ar(0.2, 0.8, trig);
    thud = Ringz.ar(thud, freq * thick.linlin(0, 1, 0.5, 1.5), thick.linlin(0, 1, 0.05, 0.2));
    thud = LPF.ar(thud, thick.linexp(0, 1, 400, 150));
    thud = thud * thick;

    // Sheet resonance - stress harmonics
    body = trig * stress;
    body = Ringz.ar(body, freq * [1, 2.3, 4.1, 6.7], stress.linlin(0, 1, 0.1, 0.4)).sum;
    body = body * sheet;

    // Continuous stress creak
    crackle = Crackle.ar(stress.linlin(0, 1, 1.2, 1.8)) * stress * 0.1;
    crackle = BPF.ar(crackle, freq * 3, 0.3);

    // Mix layers
    sig = (snap * 0.3) + (thud * 0.4) + (body * 0.25) + crackle;
    sig = sig * 0.5;

    // Slight stereo spread for space
    sig = [
        DelayC.ar(sig, 0.02, LFNoise2.kr(0.5).range(0.001, 0.008)),
        DelayC.ar(sig, 0.02, LFNoise2.kr(0.4).range(0.002, 0.01))
    ];

    sig = sig * 8;
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_aurora_cave_icesht loaded".postln;
