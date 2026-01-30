// nexus/seawall — Lightweight end-stage generator
SynthDef(\forge_nexus_seawall, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var mas, prs, crk, slt, tde;
    var mass, pressure, cracks, salt, tide, subFreq, foldAmt;

    // Read custom params - seawall mass topology
    mas = p[0];  // P1: Mass (subharmonic weight)
    prs = p[1];  // P2: Pressure (compression density)
    crk = p[2];  // P3: Cracks (stress fracture noise)
    slt = p[3];  // P4: Salt corrosion (textural grit)
    tde = p[4];  // P5: Tide cycle (slow macro modulation)

    freq = In.kr(freqBus);

    // DSP: Massive seawall infrastructure

    // Tide: slow macro modulation cycle
    tide = SinOsc.kr(tde.linexp(0, 1, 0.02, 0.2)).range(0.7, 1);

    // Subharmonic frequency
    subFreq = freq * mas.linlin(0, 1, 0.5, 0.25);

    // Mass: heavy subharmonic weight with wavefold
    mass = LFSaw.ar(subFreq * [1, 1.003], 0, 0.6);
    foldAmt = prs.linlin(0, 1, 1, 3);
    mass = (mass * foldAmt).fold2(1) * 0.4;
    mass = mass + (SinOsc.ar(subFreq * 2, 0, 0.2) * mas);
    mass = mass + (LFTri.ar(subFreq * 0.5, 0, 0.15) * mas * mas);
    mass = mass * tide;

    // Pressure: compression density wavefold cascade
    pressure = mass;
    pressure = (pressure * (1 + prs)).fold2(1);
    pressure = (pressure * (1 + (prs * 0.5))).tanh;
    pressure = RLPF.ar(pressure, freq * prs.linlin(0, 1, 1, 4), 0.4);

    // Cracks: stress fracture noise
    cracks = Dust.ar(crk.linexp(0, 1, 0.5, 20) * [1, 1.1]);
    cracks = Ringz.ar(cracks, freq * [1.7, 2.9, 4.3], crk.linlin(0, 1, 0.02, 0.1)).sum * 0.2;
    cracks = cracks + (Crackle.ar(crk.linlin(0, 1, 1.2, 1.7)) * crk * 0.1);
    cracks = cracks * tide;

    // Salt: corrosion grit texture
    salt = GrayNoise.ar(0.15) + (PinkNoise.ar(0.1) * slt);
    salt = BPF.ar(salt, freq * slt.linlin(0, 1, 2, 8), 0.3) * 3;
    salt = salt + (WhiteNoise.ar(slt * 0.05));
    salt = salt * slt.linlin(0, 1, 0.2, 0.6);

    sig = (mass * 0.4) + (pressure * 0.3) + cracks + salt;

    // Tide breathing
    sig = sig * (1 + (SinOsc.kr(tde * 0.1 + 0.02) * tde * 0.15));

    // Massive infrastructure reverb
    sig = sig + (CombL.ar(sig, 0.3, tde.linlin(0, 1, 0.1, 0.25), tde * 2) * 0.2);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_nexus_seawall loaded".postln;
