// hoar_frost/crystal_chime — Lightweight end-stage generator
// crystal_chime: Ice crystals tinkling - metallic Klank tones (continuous shimmer)
SynthDef(\forge_hoar_frost_crystal_chime, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var metallic, ringTime, spread, density, brightness;
    var trig, exciter;

    metallic = p[0].linlin(0, 1, 1, 2.5);
    ringTime = p[1].linlin(0, 1, 0.5, 4);
    spread = p[2].linlin(0, 1, 0, 0.01);
    density = p[3].linlin(0, 1, 2, 15);
    brightness = p[4].linlin(0, 1, 0.3, 1.5);

    freq = In.kr(freqBus);

    // DSP: Continuous chime excitation with Dust
    trig = Dust.ar(density);
    exciter = trig * 0.3;

    // Resonant bank tuned to metallic partials
    sig = DynKlank.ar(
        `[[1, 2.2, 3.5, 4.7, 6.1] * metallic.sqrt,
          [1, 0.5, 0.35, 0.25, 0.15] * brightness,
          [1, 0.8, 0.6, 0.4, 0.3] * ringTime],
        exciter,
        freq
    );

    // Stereo spread
    sig = [
        DynKlank.ar(
            `[[1, 2.2, 3.5, 4.7, 6.1] * metallic.sqrt,
              [1, 0.5, 0.35, 0.25, 0.15] * brightness,
              [1, 0.8, 0.6, 0.4, 0.3] * ringTime],
            Dust.ar(density) * 0.3,
            freq
        ),
        DynKlank.ar(
            `[[1, 2.2, 3.5, 4.7, 6.1] * metallic.sqrt * 1.003,
              [1, 0.5, 0.35, 0.25, 0.15] * brightness,
              [1, 0.8, 0.6, 0.4, 0.3] * ringTime],
            Dust.ar(density) * 0.3,
            freq * (1 + spread)
        )
    ];

    sig = sig * 0.25;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_hoar_frost_crystal_chime loaded".postln;
