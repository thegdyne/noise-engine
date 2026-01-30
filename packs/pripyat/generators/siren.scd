// pripyat/siren — Lightweight end-stage generator
SynthDef(\forge_pripyat_siren, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var dist, wail, rate, tone, dopp;
    var sweepFreq, harmonics, dopplerMod;

    freq = In.kr(freqBus);

    dist = p[0];
    wail = p[1];
    rate = p[2];
    tone = p[3];
    dopp = p[4];

    // Sweep oscillator for wailing
    sweepFreq = SinOsc.kr(rate.linexp(0, 1, 0.1, 2)).range(
        freq * (1 - (wail * 0.3)),
        freq * (1 + (wail * 0.3))
    );

    // Doppler drift
    dopplerMod = LFNoise2.kr(0.1).range(1 - (dopp * 0.05), 1 + (dopp * 0.05));
    sweepFreq = sweepFreq * dopplerMod;

    // Harmonic series - civil defense siren character
    harmonics = Mix.fill(8, { |i|
        SinOsc.ar(
            sweepFreq * (i + 1),
            0,
            (1 / (i + 1)) * (tone.linlin(0, 1, 0.3, 1) ** i) * if((i + 1).odd, 1, 0.6)
        );
    });

    sig = harmonics * 0.6;

    // Distance processing - gentler lowpass, boost before filter
    sig = LPF.ar(sig, dist.linexp(0, 1, 10000, 1500));

    // Compensate for distance attenuation
    sig = sig * dist.linlin(0, 1, 1, 2);

    // Simple distance reverb
    sig = sig + (CombL.ar(sig, 0.2, dist.linlin(0, 1, 0.02, 0.12), dist.linlin(0, 1, 0.1, 1.2)) * dist * 0.3);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_pripyat_siren loaded".postln;
