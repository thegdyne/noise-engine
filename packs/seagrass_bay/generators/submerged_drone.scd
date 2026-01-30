// seagrass_bay/submerged_drone — Lightweight end-stage generator
SynthDef(\forge_seagrass_bay_submerged_drone, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var depth, pressure, murk, drift, body;
    var subOsc, mainOsc, driftMod, pressureEnv;

    // Standard bus reads
    freq = In.kr(freqBus);

    depth = p[0];  // Sub-octave intensity
    pressure = p[1];  // Compression density
    murk = p[2];  // Filter darkness
    drift = p[3];  // Pitch wandering
    body = p[4];  // Harmonic fullness

    // Slow drift modulation
    driftMod = LFNoise1.kr(0.1 + (drift * 0.3)) * (drift * 0.02);
    freq = freq * (1 + driftMod);

    // Main oscillator - warm saw
    mainOsc = Saw.ar(freq) * body.linlin(0, 1, 0.4, 0.7);

    // Sub-octave oscillator
    subOsc = Saw.ar(freq * 0.5) * depth.linlin(0, 1, 0.0, 0.6);

    // Body harmonics - octave up blended in
    sig = mainOsc + subOsc + (Saw.ar(freq * 2) * body * 0.15);

    // Pressure - subtle compression feel via soft clip
    pressureEnv = pressure.linlin(0, 1, 1.0, 0.7);
    sig = (sig * (1 + (pressure * 0.5))).tanh * pressureEnv;

    // Murk - additional low-pass darkness
    sig = LPF.ar(sig, murk.linexp(0, 1, 8000, 800));

    // Stereo spread

    // Standard output chain
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_seagrass_bay_submerged_drone loaded".postln;
