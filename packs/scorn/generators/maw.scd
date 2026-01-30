// scorn/maw — Lightweight end-stage generator
// maw: Organic mouth - breath, gurgle
SynthDef(\forge_scorn_maw, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var breath, gurgle, throat, teeth, saliva;
    var breathMod;

    breath = p[0].linlin(0, 1, 0.1, 0.3);  // P1: Breath rate
    gurgle = p[1].linlin(0, 1, 3, 20);  // P2: Gurgle sounds
    throat = p[2].linlin(0, 1, 0.3, 0.9);  // P3: Throat resonance
    teeth = p[3].linlin(0, 1, 0, 0.4);  // P4: Teeth click
    saliva = p[4].linlin(0, 1, 0.1, 0.5);  // P5: Wet saliva

    freq = In.kr(freqBus);

    // DSP: Breathing - slow modulated noise
    breathMod = SinOsc.kr(breath).range(0.3, 1);
    sig = BPF.ar(PinkNoise.ar(throat * 0.5), freq * 2, 0.4) * breathMod;

    // Throat resonance - formant-like
    sig = sig + (Formant.ar(freq * 0.5, freq * 2, freq * 4) * throat * 0.25);

    // Gurgle - wet bubbling
    sig = sig + (Ringz.ar(Dust.ar(gurgle) * 0.15, freq * [1.5, 2, 2.5], 0.06) * saliva * 0.5);

    // Teeth clicks
    sig = sig + (HPF.ar(Dust.ar(teeth * 8) * 0.2, 2000) * teeth);

    // Saliva wetness
    sig = sig + (LPF.ar(Crackle.ar(1.8) * saliva * 0.2, 1500));

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_scorn_maw loaded".postln;
