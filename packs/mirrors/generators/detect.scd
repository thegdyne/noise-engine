// mirrors/detect — Lightweight end-stage generator
SynthDef(\forge_mirrors_detect, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var engine, approach, propeller, altitude, faint;
    var modulator, carrier, propMod, dopplerMod, engineDrone;

    engine = p[0];
    approach = p[1];
    propeller = p[2];
    altitude = p[3];
    faint = p[4];

    freq = In.kr(freqBus);

    // Doppler approach modulation
    dopplerMod = LFSaw.kr(approach.linexp(0, 1, 0.02, 0.15)).range(0.95, 1.05);
    freq = freq * dopplerMod;

    // Propeller rhythm modulation
    propMod = SinOsc.kr(propeller.linexp(0, 1, 5, 25)).range(0.8, 1.0);

    // FM modulator - engine vibration
    modulator = SinOsc.ar(freq * (2 + engine), 0, freq * (0.5 + (engine * 3)));

    // Carrier with FM
    carrier = SinOsc.ar(freq + modulator, 0, 0.3) * propMod;

    // Additional engine harmonics
    engineDrone = SinOsc.ar(freq * 0.5, 0, 0.2);
    engineDrone = engineDrone + SinOsc.ar(freq * 1.5, 0, 0.15 * engine);
    engineDrone = engineDrone + SinOsc.ar(freq * 2, 0, 0.1 * engine);

    // Propeller buzz
    engineDrone = engineDrone + (Pulse.ar(propeller.linexp(0, 1, 20, 80), 0.3, 0.15 * propeller));

    sig = carrier + engineDrone;

    // Altitude affects brightness
    sig = LPF.ar(sig, altitude.linexp(0, 1, 1500, 6000));

    // Faint distance haze
    sig = sig * (1 - (faint * 0.5));
    sig = sig + (PinkNoise.ar(0.1) * faint);

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.08), 400);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_mirrors_detect loaded".postln;
