// pripyat/geiger — Lightweight end-stage generator
SynthDef(\forge_pripyat_geiger, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var rad, prox, tube, room, deca;
    var clicks, clickRate, clickFreq, decayTime, roomSig;

    freq = In.kr(freqBus);

    rad = p[0];
    prox = p[1];
    tube = p[2];
    room = p[3];
    deca = p[4];

    // Click rate based on radiation level
    clickRate = rad.linexp(0, 1, 0.5, 80);

    // Click frequency based on proximity and tube type
    clickFreq = freq * prox.linexp(0, 1, 0.5, 2) * tube.linlin(0, 1, 0.8, 1.5);
    decayTime = deca.linexp(0, 1, 0.005, 0.08);

    // Generate clicks with resonant character
    clicks = Dust.ar(clickRate);
    sig = Ringz.ar(clicks, [clickFreq, clickFreq * 1.02], decayTime);
    sig = sig * tube.linlin(0, 1, 0.3, 0.6);

    // Add slight pitch variation per click
    sig = sig + Ringz.ar(
        Dust.ar(clickRate * 0.3),
        clickFreq * LFNoise0.kr(10).range(0.95, 1.05),
        decayTime * 1.5
    ) * 0.3;

    // Room reflections - simple comb delay
    roomSig = CombL.ar(sig.sum, 0.1, room.linlin(0, 1, 0.01, 0.07), room.linlin(0, 1, 0.05, 0.3));
    sig = sig + (roomSig.dup * room * 0.4);

    sig = sig.sum;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_pripyat_geiger loaded".postln;
