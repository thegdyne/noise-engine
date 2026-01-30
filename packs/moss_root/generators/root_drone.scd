// moss_root/root_drone — Lightweight end-stage generator
SynthDef(\forge_moss_root_root_drone, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var age, depth, sap, grit, spread;
    var main, sub, aged, sapMod, gritSig;

    freq = In.kr(freqBus);

    age = p[0];  // Inharmonic aging
    depth = p[1];  // Sub-octave mix
    sap = p[2];  // Slow drift
    grit = p[3];  // Bark texture
    spread = p[4];  // Stereo width

    // Sap flow: slow pitch drift
    sapMod = LFNoise1.kr(sap.linexp(0, 1, 0.02, 0.2)) * sap.linlin(0, 1, 0, 0.02);

    // Main oscillator: slightly detuned for organic feel
    main = Mix([
        Saw.ar(freq * (1 + sapMod)),
        Saw.ar(freq * 1.002 * (1 + sapMod)),
        Pulse.ar(freq * 0.999 * (1 + sapMod), 0.4) * 0.5
    ]) * 0.4;

    // Sub oscillator for depth
    sub = SinOsc.ar(freq * 0.5 * (1 + sapMod)) * depth.linlin(0, 1, 0, 0.6);

    // Age: add inharmonic partials (stretched harmonics like old wood)
    aged = Mix(Array.fill(4, { |i|
        var ratio = (i + 2) * (1 + (age * 0.1 * (i + 1).rand2));
        SinOsc.ar(freq * ratio) * (0.15 / (i + 1)) * age
    }));

    sig = main + sub + aged;

    // Grit: soft waveshaping for bark texture
    gritSig = (sig * grit.linexp(0, 1, 1, 4)).tanh;
    sig = sig.blend(gritSig, grit * 0.7);

    // Stereo spread
    sig = Pan2.ar(Mix(sig), SinOsc.kr(spread.linexp(0, 1, 0.05, 0.3).max(0.001)) * spread);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_moss_root_root_drone loaded".postln;
