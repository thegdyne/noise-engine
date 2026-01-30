// icarus/heat_wall — Lightweight end-stage generator
// Heat Wall -- approaching inferno, rising temperature
// Role: bed

SynthDef(\forge_icarus_heat_wall, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var temp, radiant, convect, scorch, plasma;
    var heat, glow, convectMod, burn, crackle;

    freq = In.kr(freqBus);

    temp = p[0].linexp(0, 1, 400, 8000);  // Heat filter freq
    radiant = p[1].linlin(0, 1, 0.0, 0.5);  // Upper glow level
    convect = p[2].linlin(0, 1, 0.2, 4);  // Convection rate
    scorch = p[3].linlin(0, 1, 1, 12);  // Distortion drive
    plasma = p[4].linlin(0, 1, 0, 40);  // Crackle density

    // Convection modulation - rising and falling air
    convectMod = LFNoise2.kr(convect, 0.3, 1);

    // Base heat - filtered noise representing thermal energy
    heat = PinkNoise.ar(0.5) + BrownNoise.ar(0.3);
    heat = RLPF.ar(heat, temp * convectMod, 0.4);

    // Radiant glow - upper harmonics
    glow = Saw.ar(freq * 2 * convectMod, radiant);
    glow = HPF.ar(glow, 3000);

    // Scorching edge - distortion
    burn = heat * scorch;
    burn = burn.tanh * (1 / scorch.sqrt);

    // Plasma crackle - ionized dust
    crackle = Dust2.ar(plasma) * 0.3;
    crackle = Ringz.ar(crackle, freq * LFNoise0.kr(8, 2, 4), 0.03);

    // Combine layers
    sig = burn + glow + crackle;

    // Stereo spread - heat shimmer

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_icarus_heat_wall loaded".postln;
