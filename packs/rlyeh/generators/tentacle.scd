// rlyeh/tentacle — Lightweight end-stage generator
// tentacle: Writhing appendages - organic alien movement
SynthDef(\forge_rlyeh_tentacle, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var writhe, slime, mass, sucker, alien;

    writhe = p[0].linlin(0, 1, 0.2, 3);  // P1: Writhing speed
    slime = p[1].linlin(0, 1, 0.1, 0.8);  // P2: Wet slime texture
    mass = p[2].linlin(0, 1, 0.3, 1);  // P3: Tentacle density (amplitude)
    sucker = p[3].linlin(0, 1, 0, 0.6);  // P4: Sucker pops
    alien = p[4].linlin(0, 1, 0, 0.5);  // P5: Alien harmonics

    freq = In.kr(freqBus);

    // DSP: Writhing FM clusters (fixed 8, mass controls amplitude rolloff)
    sig = Mix.fill(8, { |i|
        var phase = i / 8 * 2pi;
        var modFreq = freq * (1 + (i * 0.1));
        var writheRate = writhe * (1 + (i * 0.15));
        var tentAmp = (mass ** (i / 4)) / 8.sqrt;
        PMOsc.ar(
            modFreq * (1 + (SinOsc.kr(writheRate, phase).range(0, 0.1))),
            modFreq * 2,
            SinOsc.kr(writheRate * 0.7, phase).range(0.5, 2),
            0
        ) * tentAmp
    });

    // Slime texture
    sig = sig + (Resonz.ar(PinkNoise.ar(slime), freq * LFNoise1.kr(writhe).range(1, 3), 0.1) * 2);

    // Sucker pops
    sig = sig + (Ringz.ar(Dust.ar(sucker * 20) * 0.2, freq * [2, 3, 4], 0.05).sum);

    // Alien harmonics
    sig = sig + (SinOsc.ar(freq * [1.618, 2.618, 4.236]) * alien * 0.15).sum;

    sig = sig * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_rlyeh_tentacle loaded".postln;
