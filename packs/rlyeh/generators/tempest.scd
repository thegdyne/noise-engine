// rlyeh/tempest — Lightweight end-stage generator
// tempest: The storm summoned - chaos of wind and wave
SynthDef(\forge_rlyeh_tempest, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var wind, waves, thunder, rain, chaos;

    wind = p[0].linlin(0, 1, 0.3, 1);  // P1: Wind intensity
    waves = p[1].linlin(0, 1, 0.1, 0.8);  // P2: Wave rate
    thunder = p[2].linlin(0, 1, 0.1, 0.6);  // P3: Thunder rumble
    rain = p[3].linlin(0, 1, 5, 100);  // P4: Rain density
    chaos = p[4].linlin(0, 1, 0.2, 1);  // P5: Storm chaos

    freq = In.kr(freqBus);

    // DSP: Wind - continuous filtered noise
    sig = BPF.ar(PinkNoise.ar(wind), freq * LFNoise1.kr(chaos).exprange(0.5, 3), 0.4) * 3;
    sig = sig + (LPF.ar(BrownNoise.ar(wind * 0.6), freq * 2));

    // Wave modulation - continuous
    sig = sig * SinOsc.kr(waves).range(0.6, 1);

    // Thunder rumble - continuous low drone with variation
    sig = sig + (LPF.ar(BrownNoise.ar(thunder), 80 + (LFNoise1.kr(0.3) * 40)) * 0.5);

    // Rain texture - continuous high crackle
    sig = sig + (HPF.ar(Dust2.ar(rain) * 0.15, 3000));

    sig = sig * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_rlyeh_tempest loaded".postln;
