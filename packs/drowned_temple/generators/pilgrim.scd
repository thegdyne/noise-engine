// drowned_temple/pilgrim — Lightweight end-stage generator
// pilgrim: Hooded wanderer in the ruins
SynthDef(\forge_drowned_temple_pilgrim, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var breath, solitude, cloak, steps, reverence;

    breath = p[0].linlin(0, 1, 0.2, 0.8);  // P1: Breath noise
    solitude = p[1].linlin(0, 1, 0.1, 0.6);  // P2: Lonely tone
    cloak = p[2].linlin(0, 1, 0.1, 0.5);  // P3: Fabric rustle
    steps = p[3].linlin(0, 1, 0.5, 3);  // P4: Footstep rate
    reverence = p[4].linlin(0, 1, 0.2, 0.7);  // P5: Reverent sub

    freq = In.kr(freqBus);

    // DSP: Breath - filtered noise with slow modulation
    sig = BPF.ar(PinkNoise.ar(breath), freq * 2 * LFNoise1.kr(0.2).range(0.8, 1.2), 0.3) * 2;

    // Solitude - lonely wavering tone
    sig = sig + (SinOsc.ar(freq * [1, 1.003] * LFNoise1.kr(0.15).range(0.995, 1.005)) * solitude * 0.3);

    // Cloak rustle
    sig = sig + (HPF.ar(Dust2.ar(cloak * 10) * 0.1, 1500));

    // Soft footsteps
    sig = sig + (LPF.ar(Dust.ar(steps) * 0.2, 300).lag(0.01, 0.1));

    // Reverent sub drone
    sig = sig + (SinOsc.ar(freq * 0.5) * reverence * 0.25);

    sig = sig * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_drowned_temple_pilgrim loaded".postln;
