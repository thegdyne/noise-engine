// nexus/waste — Lightweight end-stage generator
SynthDef(\forge_nexus_waste, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var rad, dky, iso, ash, glw;
    var radiation, decayEnv, isotope, ashNoise, glow, geiger;

    // Read custom params - radioactive decay topology
    rad = p[0];  // P1: Radiation level (overall mod intensity)
    dky = p[1];  // P2: Decay halflife (envelope character)
    iso = p[2];  // P3: Isotope instability (ratio jitter)
    ash = p[3];  // P4: Ash accumulation (noise floor)
    glw = p[4];  // P5: Glow warmth vs harshness

    freq = In.kr(freqBus);

    // DSP: Radioactive wasteland

    // Geiger: random decay events
    geiger = Dust.ar(rad.linexp(0, 1, 1, 30) * [1, 0.9]);
    geiger = Ringz.ar(geiger, freq * [4, 6, 9] * (1 + (LFNoise0.kr(iso * 5) * iso * 0.3)), 0.02).sum * 0.2;

    // Isotope: unstable partials with jittery ratios
    isotope = Mix.fill(5, { |i|
        var ratio, jitter, partialDecay;
        jitter = LFNoise1.kr(iso * 3 + 0.5).range(1 - (iso * 0.2), 1 + (iso * 0.2));
        ratio = (i + 1) * jitter;
        partialDecay = dky.linlin(0, 1, 0.1, 0.8) / (i + 1);
        SinOsc.ar(freq * ratio, 0, 0.12 / (i + 1)) * Decay.kr(Dust.kr(rad * 5 + 1), partialDecay)
    });
    isotope = isotope * rad.linlin(0, 1, 0.3, 1);

    // Radiation: FM modulated drone
    radiation = SinOsc.ar(
        freq * (1 + (LFNoise2.ar(rad * 50 + 10) * rad * 0.05)),
        SinOsc.ar(freq * 2 * (1 + (iso * 0.5)), 0, rad * 2 * pi),
        0.25
    );

    // Decay envelope shaping
    decayEnv = 1 + (SinOsc.kr(dky.linexp(0, 1, 0.05, 1)) * dky * 0.3);
    radiation = radiation * decayEnv;

    // Ash: accumulated noise floor
    ashNoise = PinkNoise.ar(0.15) + (GrayNoise.ar(0.1) * ash);
    ashNoise = RLPF.ar(ashNoise, freq * ash.linlin(0, 1, 2, 8), 0.4);
    ashNoise = ashNoise * ash.linlin(0, 1, 0.1, 0.5);

    // Glow: warmth vs harshness character
    glow = radiation + isotope;
    glow = (glow * glw.linlin(0, 1, 0.5, 1)) + ((glow * 2).tanh * (1 - glw) * 0.5);
    glow = RLPF.ar(glow, glw.linexp(0, 1, 2000, 12000), 0.5);

    sig = glow + geiger + ashNoise;

    // Orange wasteland color: subtle saturation
    sig = (sig * (1 + (rad * 0.5))).tanh;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_nexus_waste loaded".postln;
