// gotham_stairs/decay — Lightweight end-stage generator
SynthDef(\forge_gotham_stairs_decay, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var crumble, rust, hollow, neglect, collapse;
    var dustTrig, crumbleSig, rustRes, hollowRes, collapseBurst, droneBase;

    crumble = p[0];
    rust = p[1];
    hollow = p[2];
    neglect = p[3];
    collapse = p[4];

    freq = In.kr(freqBus);

    // Dust trigger for crumbling particles
    dustTrig = Dust.ar(crumble.linlin(0, 1, 2, 30));

    // Crumbling concrete/plaster particles
    crumbleSig = Ringz.ar(dustTrig, freq * [1, 1.5, 2.3], crumble.linlin(0, 1, 0.05, 0.2)).sum;
    crumbleSig = crumbleSig * neglect * 0.4;

    // Rust resonance - metallic decay on railings
    rustRes = Ringz.ar(
        Dust.ar(rust.linlin(0, 1, 1, 15)),
        freq * [3.1, 4.7, 6.2],
        rust.linlin(0, 1, 0.1, 0.4)
    ).sum * rust * 0.3;

    // Hollow spaces - resonant cavities in walls
    hollowRes = Resonz.ar(
        PinkNoise.ar(0.2),
        freq * hollow.linlin(0, 1, 0.5, 2),
        0.1 + (hollow * 0.2)
    ) * 4 * hollow;

    // Collapse bursts - structural failure moments
    collapseBurst = Dust.ar(collapse.linlin(0, 1, 0.2, 2));
    collapseBurst = DynKlank.ar(
        `[
            [1, 1.7, 2.4, 3.8, 5.1],
            [1, 0.6, 0.4, 0.2, 0.1],
            [0.5, 0.4, 0.3, 0.2, 0.1] * (1 + neglect)
        ],
        collapseBurst * 0.4,
        freq * 0.5
    ) * collapse;

    // Continuous drone base for drone mode compatibility
    droneBase = BrownNoise.ar(0.08) + (PinkNoise.ar(0.05) * neglect);
    droneBase = RLPF.ar(droneBase, freq * 2, 0.5);

    sig = crumbleSig + rustRes + hollowRes + collapseBurst + droneBase;

    // Neglect degrades the overall sound
    sig = sig * (0.7 + (neglect * 0.3));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_gotham_stairs_decay loaded".postln;
