// gotham_stairs/graffiti — Lightweight end-stage generator
SynthDef(\forge_gotham_stairs_graffiti, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var spray, grit, drip, layer, vandal;
    var hiss, texture, drips, layers;

    spray = p[0];
    grit = p[1];
    drip = p[2];
    layer = p[3];
    vandal = p[4];

    freq = In.kr(freqBus);

    // Spray paint hiss - high frequency noise bursts
    hiss = WhiteNoise.ar(spray * 0.4);
    hiss = RHPF.ar(hiss, freq * 4 + (spray * 2000), 0.3);
    hiss = hiss * LFNoise2.kr(3 + (vandal * 5)).range(0.3, 1);

    // Wall texture - gritty filtered noise
    texture = BrownNoise.ar(0.3) + (PinkNoise.ar(0.2) * grit);
    texture = Resonz.ar(texture, freq * (1 + (grit * 2)), 0.5 + (grit * 0.3)) * 4;

    // Paint drips - irregular resonant pings
    drips = Dust.ar(drip.linlin(0, 1, 0.5, 8));
    drips = Ringz.ar(drips, freq * [1.5, 2.1], drip.linlin(0, 1, 0.1, 0.4)).sum * 0.3;

    // Layered depth - multiple filtered noise bands
    layers = Mix.fill(4, { |i|
        var layerFreq = freq * (1 + (i * 0.5 * layer));
        var layerNoise = PinkNoise.ar(0.15);
        Resonz.ar(layerNoise, layerFreq, 0.2 + (layer * 0.3)) * 3
    });

    // Combine with vandal chaos modulation
    sig = hiss + texture + drips + (layers * layer);
    sig = sig * (1 + (LFNoise0.kr(vandal.linlin(0, 1, 0.5, 8)).range(0, 0.5) * vandal));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_gotham_stairs_graffiti loaded".postln;
