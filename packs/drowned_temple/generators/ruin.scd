// drowned_temple/ruin — Lightweight end-stage generator
// ruin: Crumbling ancient architecture
SynthDef(\forge_drowned_temple_ruin, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var erosion, weight, fracture, memory, void;

    erosion = p[0].linlin(0, 1, 0.1, 0.6);  // P1: Erosion texture
    weight = p[1].linlin(0, 1, 0.3, 1);  // P2: Stone weight
    fracture = p[2].linlin(0, 1, 1, 8);  // P3: Fracture rate
    memory = p[3].linlin(0, 1, 0.1, 0.5);  // P4: Fading memory tone
    void = p[4].linlin(0, 1, 0.1, 0.5);  // P5: Empty void

    freq = In.kr(freqBus);

    // DSP: Erosion - continuous textured noise
    sig = LPF.ar(Crackle.ar(1.6) * erosion * 0.3, freq * 4);

    // Heavy stone presence
    sig = sig + (SinOsc.ar(freq * [0.5, 1]) * weight * 0.25);
    sig = sig + (LPF.ar(Pulse.ar(freq * 0.5, 0.3), 400) * weight * 0.15);

    // Fracture events - stereo
    sig = sig + (Ringz.ar(Dust.ar(fracture) * 0.25, freq * [0.7, 1, 1.5], 0.2) * 0.4);

    // Memory - fading distant tone
    sig = sig + (SinOsc.ar(freq * 2 * LFNoise1.kr(0.05).range(0.98, 1.02)) * memory * LFNoise1.kr(0.1).range(0.3, 1) * 0.15);

    // Void - empty filtered space
    sig = sig + (LPF.ar(PinkNoise.ar(void * 0.3), 300));

    sig = sig * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_drowned_temple_ruin loaded".postln;
