// ekrano/turbine — Lightweight end-stage generator
SynthDef(\forge_ekrano_turbine, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var throttle, fans, spin, roar, whine;
    var noise, lowNoise, midNoise, highNoise, spinMod, fanLayers;

    freq = In.kr(freqBus);

    throttle = p[0].linlin(0, 1, 0.1, 1.0);
    fans = p[1].linlin(0, 1, 0.2, 1.0);
    spin = p[2].linexp(0, 1, 0.5, 20);
    roar = p[3];
    whine = p[4];

    // Spin modulation - turbine wobble
    spinMod = SinOsc.kr(spin, 0, 0.1, 1);

    // Eight turbofan layers using noise bands
    lowNoise = LPF.ar(BrownNoise.ar(0.5), freq * 0.5 * spinMod) * roar;
    midNoise = BPF.ar(PinkNoise.ar(0.4), freq * spinMod, 0.3) * fans;
    highNoise = HPF.ar(WhiteNoise.ar(0.15), freq * 4 * spinMod) * whine;

    // Layer the engine bands
    fanLayers = Mix.ar([
        lowNoise * 0.6,
        midNoise * 0.8,
        highNoise * 0.4,
        BPF.ar(PinkNoise.ar(0.3), freq * 2 * spinMod, 0.2) * fans * 0.5,
        BPF.ar(WhiteNoise.ar(0.2), freq * 3, 0.15) * whine * 0.3
    ]);

    sig = fanLayers * throttle;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ekrano_turbine loaded".postln;
