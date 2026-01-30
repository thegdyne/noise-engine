// drowned_temple/deluge — Lightweight end-stage generator
// deluge: Rain cascading through broken vaults
SynthDef(\forge_drowned_temple_deluge, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var intensity, droplets, sheet, splash, distant;

    intensity = p[0].linlin(0, 1, 0.4, 1);  // P1: Rain intensity
    droplets = p[1].linlin(0, 1, 10, 60);  // P2: Droplet rate (boosted)
    sheet = p[2].linlin(0, 1, 0.3, 1);  // P3: Sheet rain noise
    splash = p[3].linlin(0, 1, 0.2, 0.8);  // P4: Splash impacts
    distant = p[4].linlin(0, 1, 0.2, 0.6);  // P5: Distant rumble

    freq = In.kr(freqBus);

    // DSP: Sheet rain - continuous filtered noise (boosted)
    sig = BPF.ar(PinkNoise.ar(sheet), 2500 * LFNoise1.kr(0.3).range(0.6, 1.4), 0.6) * 4;

    // Droplet impacts - stereo Ringz array (boosted)
    sig = sig + (Ringz.ar(Dust.ar(droplets * intensity) * 0.3, freq * [3, 4.5, 6], 0.05) * splash * 0.6);

    // Splash on stone
    sig = sig + (HPF.ar(Dust2.ar(droplets * 0.7) * splash * 0.2, 1500));

    // Distant thunder rumble (boosted)
    sig = sig + (LPF.ar(BrownNoise.ar(distant), 200) * LFNoise1.kr(0.1).range(0.4, 1) * 0.6);

    // Continuous base layer
    sig = sig + (LPF.ar(PinkNoise.ar(intensity * 0.4), 1000));

    sig = sig * intensity * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_drowned_temple_deluge loaded".postln;
