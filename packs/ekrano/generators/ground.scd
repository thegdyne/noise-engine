// ekrano/ground — Lightweight end-stage generator
SynthDef(\forge_ekrano_ground, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var altitude, airflow, lift, turbulence, hiss;
    var exciter, tubeDelay, tubeSig, turbMod, hissSig;

    freq = In.kr(freqBus);

    altitude = p[0].linexp(0, 1, 0.5, 4);
    airflow = p[1].linlin(0, 1, 0.1, 0.8);
    lift = p[2].linlin(0, 1, 0.1, 0.9);
    turbulence = p[3].linexp(0, 1, 0.5, 15);
    hiss = p[4];

    // Turbulence modulation
    turbMod = LFNoise1.kr(turbulence).range(0.9, 1.1);

    // Air flow excitation
    exciter = PinkNoise.ar(airflow) + (BrownNoise.ar(airflow * 0.3));

    // Tube resonator - waveguide style
    tubeDelay = (1 / (freq * altitude * turbMod)).clip(0.0001, 0.05);
    tubeSig = CombL.ar(exciter, 0.05, tubeDelay, lift * 0.5);
    tubeSig = tubeSig + CombL.ar(exciter, 0.05, tubeDelay * 1.5, lift * 0.3);

    // High frequency hiss layer
    hissSig = HPF.ar(WhiteNoise.ar(hiss * 0.3), 4000);

    sig = (tubeSig * 0.6) + (hissSig * 0.4);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_ekrano_ground loaded".postln;
