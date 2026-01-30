// q121/airflow — Lightweight end-stage generator
SynthDef(\forge_q121_airflow, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var speed, laminar, tube, gusts, width;
    var windBase, gustMod, tubeRes, laminarNoise, turbNoise;

    speed = p[0];
    laminar = p[1];
    tube = p[2];
    gusts = p[3];
    width = p[4];

    freq = In.kr(freqBus);

    // Gust modulation - slow random amplitude swells
    gustMod = LFNoise2.kr(gusts.linexp(0, 1, 0.1, 2)).range(1 - (gusts * 0.5), 1);

    // Laminar flow - smoother filtered noise
    laminarNoise = BPF.ar(PinkNoise.ar(1), freq * speed.linexp(0, 1, 0.5, 4), 0.3);
    laminarNoise = laminarNoise + BPF.ar(PinkNoise.ar(0.5), freq * 2, 0.4);

    // Turbulent flow - harsher, wider bandwidth
    turbNoise = BrownNoise.ar(0.6) + WhiteNoise.ar(0.2);
    turbNoise = RHPF.ar(turbNoise, speed.linexp(0, 1, 100, 800), 0.5);
    turbNoise = RLPF.ar(turbNoise, speed.linexp(0, 1, 2000, 12000), 0.6);

    // Crossfade laminar/turbulent
    windBase = XFade2.ar(turbNoise, laminarNoise, laminar.linlin(0, 1, -1, 1));

    // Tunnel tube resonance - formant-like peaks
    tubeRes = Resonz.ar(windBase, freq, tube.linlin(0, 1, 0.5, 0.1)) * 4;
    tubeRes = tubeRes + Resonz.ar(windBase, freq * 1.5, tube.linlin(0, 1, 0.6, 0.15)) * 2;
    tubeRes = tubeRes + Resonz.ar(windBase, freq * 2.5, tube.linlin(0, 1, 0.7, 0.2)) * 1.5;

    // Mix with dry wind
    sig = (windBase * (1 - (tube * 0.6))) + (tubeRes * tube * 0.5);
    sig = sig * gustMod;

    // Stereo width
    sig = Splay.ar(sig.asArray, width, 1, 0);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_q121_airflow loaded".postln;
