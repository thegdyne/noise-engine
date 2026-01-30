// drowned_temple/moss — Lightweight end-stage generator
// moss: Soft overgrown decay
SynthDef(\forge_drowned_temple_moss, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var soft, organic, growth, damp, life;

    soft = p[0].linlin(0, 1, 0.3, 1);  // P1: Softness
    organic = p[1].linlin(0, 1, 0.05, 0.3);  // P2: Organic movement
    growth = p[2].linlin(0, 1, 0.2, 0.7);  // P3: Growth texture
    damp = p[3].linlin(0, 1, 300, 1500);  // P4: Damp cutoff
    life = p[4].linlin(0, 1, 0, 0.4);  // P5: Tiny life sounds

    freq = In.kr(freqBus);

    // DSP: Soft pad - heavily filtered
    sig = LPF.ar(Saw.ar(freq * [0.5, 0.501, 1, 1.002]) * soft, damp);
    sig = Splay.ar(sig, 0.6) * 0.25;

    // Organic movement - slow modulated noise
    sig = sig + (LPF.ar(PinkNoise.ar(growth), damp * 0.5) * LFNoise1.kr(organic).range(0.5, 1) * 0.4);

    // Tiny life - sparse high crackles
    sig = sig + (HPF.ar(Dust2.ar(life * 15) * 0.08, 3000));

    // Sub warmth
    sig = sig + (SinOsc.ar(freq * 0.25) * soft * 0.15);

    sig = sig * 0.45;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_drowned_temple_moss loaded".postln;
