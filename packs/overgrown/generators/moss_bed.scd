// overgrown/moss_bed — Lightweight end-stage generator
SynthDef(\forge_overgrown_moss_bed, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var thick, damp, soft, life, earth;
    var pad, moisture, movement, earthTone, cushion;

    thick = p[0];
    damp = p[1];
    soft = p[2];
    life = p[3];
    earth = p[4];

    freq = In.kr(freqBus);

    // Soft pad base - filtered sines
    pad = SinOsc.ar(freq) * 0.3;
    pad = pad + (SinOsc.ar(freq * 2.01) * 0.1 * (1 - soft));
    pad = pad + (SinOsc.ar(freq * 0.5) * thick * 0.2);
    pad = LPF.ar(pad, soft.linexp(0, 1, 2000, 600));

    // Moisture - filtered noise
    moisture = LPF.ar(BrownNoise.ar(0.15), damp.linexp(0, 1, 300, 1200)) * damp * 0.3;
    moisture = moisture * LFNoise1.kr(0.2).range(0.7, 1);

    // Living movement - slow modulated harmonics
    movement = SinOsc.ar(freq * 3 * LFNoise1.kr(life.linexp(0, 1, 0.05, 0.3)).range(0.98, 1.02)) * life * 0.06;
    movement = movement + (SinOsc.ar(freq * 4 * LFNoise1.kr(life.linexp(0, 1, 0.04, 0.25)).range(0.97, 1.03)) * life * 0.03);

    // Earthy undertone - very low filtered noise
    earthTone = LPF.ar(BrownNoise.ar(0.1), earth.linexp(0, 1, 60, 150)) * earth * 0.25;
    earthTone = earthTone + (SinOsc.ar(freq * 0.25) * earth * 0.15);

    // Cushion - soft sub layer
    cushion = SinOsc.ar(freq * 0.5) * thick * 0.15;
    cushion = LPF.ar(cushion, 200);

    // Combine
    sig = pad + moisture + movement + earthTone + cushion;
    sig = [sig, sig * LFNoise1.kr(0.1).range(0.95, 1.05)];

    // Extra softening
    sig = LPF.ar(sig, soft.linexp(0, 1, 3000, 1000));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_overgrown_moss_bed loaded".postln;
