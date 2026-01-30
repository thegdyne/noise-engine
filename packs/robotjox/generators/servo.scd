// robotjox/servo — Lightweight end-stage generator
SynthDef(\forge_robotjox_servo, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var pressure, stroke, load, leak, speed;
    var hiss, tube, piston, loadStrain, strokeMod;

    pressure = p[0];
    stroke = p[1];
    load = p[2];
    leak = p[3];
    speed = p[4];

    freq = In.kr(freqBus);

    // Stroke modulation - piston movement
    strokeMod = LFSaw.kr(speed.linexp(0, 1, 0.2, 3)).range(0, 1);
    strokeMod = strokeMod * stroke;

    // Hydraulic hiss - pressurized air
    hiss = WhiteNoise.ar(0.3) + PinkNoise.ar(0.2);
    hiss = BPF.ar(hiss, 3000 + (pressure * 4000), 0.3) * 2;
    hiss = hiss * (0.3 + (pressure * 0.7));
    hiss = hiss * (0.5 + (strokeMod * 0.5));

    // Tube resonance - cylinder body
    tube = BPF.ar(PinkNoise.ar(0.4), freq, 0.1) * 4;
    tube = tube + BPF.ar(BrownNoise.ar(0.3), freq * 0.5, 0.15) * 3;
    tube = CombL.ar(tube, 0.1, freq.reciprocal.clip(0.002, 0.1), 0.1 + (load * 0.3));

    // Piston mechanical sound
    piston = Pulse.ar(freq * 0.5, strokeMod.clip(0.1, 0.9), 0.2);
    piston = piston * LFNoise2.kr(speed * 5).range(0.7, 1.0);

    // Load strain - stressed mechanics
    loadStrain = Crackle.ar(1.5 + (load * 0.4), 0.15 * load);
    loadStrain = BPF.ar(loadStrain, freq * 2, 0.3);

    sig = (hiss * 0.4) + (tube * 0.3) + (piston * 0.2) + loadStrain;

    // Continuous leak hiss
    sig = sig + HPF.ar(PinkNoise.ar(0.15 * (0.3 + (leak * 0.7))), 2000);

    // Continuous bed
    sig = sig + LPF.ar(BrownNoise.ar(0.08), 300);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_robotjox_servo loaded".postln;
