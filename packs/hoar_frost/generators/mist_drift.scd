// hoar_frost/mist_drift — Lightweight end-stage generator
// mist_drift: Morning mist - evolving filtered noise
SynthDef(\forge_hoar_frost_mist_drift, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var density, drift, color, width, breath;

    density = p[0].linlin(0, 1, 0.5, 1);
    drift = p[1].linlin(0, 1, 0.02, 0.3);
    color = p[2].linexp(0, 1, 400, 3000);
    width = p[3].linlin(0, 1, 0.3, 1.5);
    breath = p[4].linlin(0, 1, 0, 0.6);

    freq = In.kr(freqBus);

    // DSP: Filtered noise with slow drift - wider filter, more gain
    sig = PinkNoise.ar(density) + (BrownNoise.ar(density * 0.3));
    sig = BPF.ar(sig,
        color * LFNoise1.kr(drift).exprange(0.7, 1.4),
        width
    ) * 8;

    // Add breathy tonal element
    sig = sig + (SinOsc.ar(freq * [1, 1.002]) * breath * LFNoise1.kr(drift * 0.5).range(0.3, 1) * 0.5);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_hoar_frost_mist_drift loaded".postln;
