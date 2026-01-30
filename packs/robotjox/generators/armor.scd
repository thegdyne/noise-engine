// robotjox/armor — Lightweight end-stage generator
SynthDef(\forge_robotjox_armor, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var plate, stress, dent, rust, flex;
    var exciter, modes, flexMod, rustNoise, ringTime;

    plate = p[0];
    stress = p[1];
    dent = p[2];
    rust = p[3];
    flex = p[4];

    freq = In.kr(freqBus);

    // Flex modulation - hull bending
    flexMod = LFNoise2.kr(0.3 + (flex * 0.5)).range(0.97, 1.03);
    freq = freq * flexMod;

    // Exciter - impacts and continuous vibration
    exciter = PinkNoise.ar(0.2) + (Dust.ar(dent.linexp(0, 1, 1, 15)) * 0.5);

    // Ring time based on plate thickness
    ringTime = plate.linexp(0, 1, 0.1, 0.6);

    // Metal plate modal resonances
    modes = Ringz.ar(exciter, freq, ringTime, 0.3 * stress);
    modes = modes + Ringz.ar(exciter, freq * 1.6, ringTime * 0.7, 0.25 * stress);
    modes = modes + Ringz.ar(exciter, freq * 2.3, ringTime * 0.5, 0.2 * stress);
    modes = modes + Ringz.ar(exciter, freq * 3.1, ringTime * 0.35, 0.15 * stress * plate);
    modes = modes + Ringz.ar(exciter, freq * 4.2, ringTime * 0.25, 0.1 * stress * plate);

    // Low structural resonance
    modes = modes + Ringz.ar(exciter, freq * 0.5, ringTime * 1.5, 0.25);

    sig = modes * 0.5;

    // Rust texture - surface degradation
    rustNoise = Crackle.ar(1.6 + (rust * 0.3), 0.15 * rust);
    rustNoise = BPF.ar(rustNoise, freq * 2, 0.4);
    sig = sig + rustNoise;

    // Hull vibration continuous
    sig = sig + BPF.ar(BrownNoise.ar(0.15), freq, 0.2) * 2;

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.08), 400);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_robotjox_armor loaded".postln;
