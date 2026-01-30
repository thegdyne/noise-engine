// duga/signal — Lightweight end-stage generator
SynthDef(\forge_duga_signal, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var harm, warb, fade, data, dist;
    var harmonics, warbMod, fadeMod, dataSig;

    freq = In.kr(freqBus);

    harm = p[0];
    warb = p[1];
    fade = p[2];
    data = p[3];
    dist = p[4];

    // Signal warble - ionospheric effects
    warbMod = SinOsc.kr(warb.linexp(0, 1, 0.5, 8)).range(0.98, 1.02);

    // Fading - signal strength variation
    fadeMod = LFNoise2.kr(fade.linexp(0, 1, 0.1, 1)).range(1 - (fade * 0.6), 1);

    // Harmonic series - NO var inside Mix.fill
    harmonics = Mix.fill(8, { |i|
        SinOsc.ar(
            freq * (i + 1) * warbMod,
            0,
            (1 / (i + 1)) * (harm.linlin(0, 1, 0.3, 1) ** (i * 0.5))
        );
    });

    sig = harmonics * 0.4 * fadeMod;

    // Data bursts - digital transmission sounds
    dataSig = Pulse.ar(freq * 2, LFNoise0.kr(15).range(0.2, 0.8));
    dataSig = dataSig * LFPulse.kr(data.linexp(0, 1, 0.5, 4), 0, 0.3);
    dataSig = LPF.ar(dataSig, 3000) * data * 0.2;

    sig = sig + dataSig;

    // Distance - lowpass for propagation loss
    sig = LPF.ar(sig, dist.linexp(0, 1, 10000, 2000));

    // Add some static
    sig = sig + (BPF.ar(WhiteNoise.ar(1), freq, 0.5) * dist * 0.1);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_duga_signal loaded".postln;
