// backyard/spokes — Lightweight end-stage generator
SynthDef(\forge_backyard_spokes, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var speed, density, chain, brake, freewheel;
    var spokeClick, chainRattle, brakeSqueak, freewheelTick, combFreq;

    speed = p[0];
    density = p[1];
    chain = p[2];
    brake = p[3];
    freewheel = p[4];

    freq = In.kr(freqBus);

    // Spoke clicks - metallic pings through comb filter
    spokeClick = Dust.ar(density.linexp(0, 1, 2, 40) * speed.linlin(0, 1, 0.5, 3));
    combFreq = freq * LFNoise1.kr(speed.linlin(0, 1, 0.5, 4)).range(0.98, 1.02);
    spokeClick = CombL.ar(spokeClick * 0.4, 0.05, combFreq.reciprocal.clip(0.0001, 0.05), 0.15);
    spokeClick = Ringz.ar(spokeClick, freq * [2.3, 3.7], 0.08).sum * 0.5;

    // Chain rattle - filtered noise bursts
    chainRattle = Dust.ar(speed.linexp(0, 1, 3, 25)) * WhiteNoise.ar(0.3);
    chainRattle = Ringz.ar(chainRattle, [1200, 2400, 3600], 0.02).sum;
    chainRattle = chainRattle * chain * 0.4;

    // Brake squeak - high pitched friction
    brakeSqueak = SinOsc.ar(
        freq * 8 + (LFNoise2.kr(12).range(0, 200)),
        0,
        brake * speed * 0.15 * LFNoise1.kr(3).range(0, 1)
    );

    // Freewheel clicking - rapid metallic ticks
    freewheelTick = Impulse.ar(speed.linexp(0, 1, 8, 80)) * (1 - speed).clip(0, 1);
    freewheelTick = Ringz.ar(freewheelTick * 0.2, [3000, 4500], 0.005).sum;
    freewheelTick = freewheelTick * freewheel * 0.5;

    // Mix all components
    sig = spokeClick + chainRattle + brakeSqueak + freewheelTick;

    // Add subtle continuous bed for drone stability
    sig = sig + (PinkNoise.ar(0.02) * density);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_backyard_spokes loaded".postln;
