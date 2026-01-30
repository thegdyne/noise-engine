// gotham_stairs/sirens — Lightweight end-stage generator
SynthDef(\forge_gotham_stairs_sirens, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var distance, urgency, echo, layers, chaos;
    var siren1, siren2, siren3, sirenMod, doppler, delayed;

    distance = p[0];
    urgency = p[1];
    echo = p[2];
    layers = p[3];
    chaos = p[4];

    freq = In.kr(freqBus);

    // Siren modulation rate based on urgency
    sirenMod = urgency.linlin(0, 1, 0.5, 4);

    // Primary siren - classic dual tone wail
    siren1 = SinOsc.ar(
        freq * SinOsc.kr(sirenMod).range(1, 1.5),
        0,
        0.4
    );

    // FM component for richer siren tone
    siren1 = SinOsc.ar(
        freq * SinOsc.kr(sirenMod).range(1, 1.5) + (SinOsc.ar(freq * 2) * urgency * 100),
        0,
        0.35
    );

    // Secondary siren - different rate (police vs ambulance)
    siren2 = SinOsc.ar(
        freq * 1.2 * SinOsc.kr(sirenMod * 0.7 + (chaos * LFNoise1.kr(0.5).range(0, 0.5))).range(0.9, 1.4),
        0,
        0.25 * layers
    );

    // Tertiary siren - slower, more distant
    siren3 = SinOsc.ar(
        freq * 0.8 * SinOsc.kr(sirenMod * 0.4).range(1, 1.3),
        0,
        0.15 * layers * chaos
    );

    sig = siren1 + siren2 + siren3;

    // Doppler effect based on distance - subtle pitch shift
    doppler = 1 + (distance.neg * 0.02 * SinOsc.kr(0.1).range(-1, 1));
    sig = PitchShift.ar(sig, 0.1, doppler, 0, 0.01);

    // Distance filtering - farther = more muffled
    sig = RLPF.ar(sig, distance.linexp(0, 1, 8000, 1500), 0.5);

    // City canyon echo
    delayed = CombL.ar(sig, 0.5, echo.linlin(0, 1, 0.1, 0.4), echo.linlin(0, 1, 0.5, 2));
    sig = sig + (delayed * echo * 0.35);

    // Distance amplitude rolloff
    sig = sig * distance.linlin(0, 1, 1, 0.3);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_gotham_stairs_sirens loaded".postln;
