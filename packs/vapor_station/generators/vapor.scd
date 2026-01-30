// vapor_station/vapor — Lightweight end-stage generator
// vapor: Fog rolling across the empty lot
SynthDef(\forge_vapor_station_vapor, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var density, drift, depth, diffuse, damp;

    density = p[0].linlin(0, 1, 0.3, 1);  // P1: Fog density
    drift = p[1].linlin(0, 1, 0.02, 0.2);  // P2: Drift speed
    depth = p[2].linlin(0, 1, 0.5, 2);  // P3: Low frequency depth
    diffuse = p[3].linlin(0, 1, 0.1, 0.6);  // P4: High diffusion
    damp = p[4].linlin(0, 1, 200, 2000);  // P5: Damping frequency

    freq = In.kr(freqBus);

    // DSP: Layered filtered noise for fog
    sig = LPF.ar(PinkNoise.ar(density), damp * LFNoise1.kr(drift).range(0.5, 1.5));
    sig = sig + (LPF.ar(BrownNoise.ar(depth * 0.5), freq * 2));

    // High diffusion shimmer
    sig = sig + (HPF.ar(PinkNoise.ar(diffuse * 0.3), 3000) * LFNoise1.kr(drift * 2).range(0.3, 1));

    // Subtle tonal anchor
    sig = sig + (SinOsc.ar(freq * [0.5, 0.501]) * density * 0.15);

    sig = sig * 0.35;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_vapor_station_vapor loaded".postln;
