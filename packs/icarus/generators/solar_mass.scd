// icarus/solar_mass — Lightweight end-stage generator
// Solar Mass -- immense gravitational presence
// Role: bed

SynthDef(\forge_icarus_solar_mass, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var gravity, fusion, mass, pressure, radiation;
    var saws, sub, high, fusionLfo, drive;

    freq = In.kr(freqBus);

    gravity = p[0].linlin(0, 1, 0.5, 1.0);  // Overall level/weight
    fusion = p[1].linlin(0, 1, 0.05, 2);  // Beating rate
    mass = p[2].linlin(0, 1, 0.0, 0.7);  // Sub level
    pressure = p[3].linlin(0, 1, 1, 8);  // Drive amount
    radiation = p[4].linlin(0, 1, 0.0, 0.4);  // High freq content

    // Slow fusion reactor beating
    fusionLfo = SinOsc.kr(fusion, 0, 0.02, 1);

    // Massive detuned saws - the gravitational pull
    saws = Saw.ar(freq * fusionLfo) * 0.3;
    saws = saws + (Saw.ar(freq * 1.002 * fusionLfo) * 0.3);
    saws = saws + (Saw.ar(freq * 0.998 * fusionLfo) * 0.3);
    saws = saws + (Saw.ar(freq * 0.5 * fusionLfo) * 0.2);

    // Sub-harmonic mass
    sub = SinOsc.ar(freq * 0.25, 0, mass);
    sub = sub + SinOsc.ar(freq * 0.5, 0, mass * 0.5);

    // Core pressure - soft clipping/saturation
    drive = saws * pressure;
    drive = (drive.tanh) * (1 / pressure.sqrt);

    // Radiation - upper harmonics
    high = Pulse.ar(freq * 2, 0.3, radiation * 0.3);
    high = HPF.ar(high, 2000);

    // Combine with gravity weight
    sig = (drive + sub + high) * gravity;

    // Gentle stereo spread
    sig = ~stereoSpread.(sig, 0.1, 0.3);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_icarus_solar_mass loaded".postln;
