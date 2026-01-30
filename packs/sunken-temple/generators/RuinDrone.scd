// sunken-temple/RuinDrone — Lightweight end-stage generator
/*
RUINDRONE Generator
Massive stone resonance of ancient architecture

Features:
  - Deep foundational drones
  - Cathedral-like reverberant space
  - Crumbling stone textures
  - Hollow wind resonance

Custom params:
  - P1 mass: Stone weight/bass
  - P2 space: Reverberant vastness
  - P3 crack: Fracture sounds
  - P4 age: Decay and erosion
  - P5 hollow: Empty resonance
*/

SynthDef(\ruindrone, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var mass, space, crack, age, hollow;
    var droneSig, massSig, spaceSig, crackSig, hollowSig;
    var drift;

    freq = In.kr(freqBus);

    mass = p[0];
    mass = Lag.kr(mass, 0.2);
    space = p[1];
    space = Lag.kr(space, 0.2);
    crack = p[2];
    crack = Lag.kr(crack, 0.05);
    age = p[3];
    age = Lag.kr(age, 0.2);
    hollow = p[4];
    hollow = Lag.kr(hollow, 0.1);

    // Glacial drift
    drift = LFNoise2.kr(0.1).range(0.995, 1.005);

    // === MASS (stone foundation) ===
    massSig = SinOsc.ar(freq * 0.5 * drift);
    massSig = massSig + (SinOsc.ar(freq * 0.502 * drift) * 0.8);  // Beating
    massSig = massSig + (SinOsc.ar(freq * 0.25) * 0.5);  // Sub
    massSig = LPF.ar(massSig, 200 + (mass * 300));
    massSig = massSig * mass * 0.5;

    // === SPACE (cathedral reverb simulation) ===
    spaceSig = SinOsc.ar(freq * drift);
    spaceSig = spaceSig + (SinOsc.ar(freq * 1.5 * drift) * 0.3);
    spaceSig = CombL.ar(spaceSig, 0.5, 0.23, space * 6);
    spaceSig = spaceSig + CombL.ar(spaceSig, 0.5, 0.31, space * 5);
    spaceSig = spaceSig + CombL.ar(spaceSig, 0.5, 0.17, space * 4);
    spaceSig = LPF.ar(spaceSig, 2000);
    spaceSig = spaceSig * space * 0.3;

    // === CRACK (structural sounds) ===
    crackSig = Dust.ar(crack * 8) * WhiteNoise.ar;
    crackSig = BPF.ar(crackSig, 800 + (LFNoise1.kr(2).range(0, 500)), 0.2);
    crackSig = crackSig + (Dust.ar(crack * 3) * BPF.ar(BrownNoise.ar, 200, 0.3));
    crackSig = crackSig * crack * 2;

    // === AGE (erosion texture) ===
    droneSig = LFNoise1.ar(age * 20 + 5) * age * 0.1;
    droneSig = BPF.ar(droneSig + BrownNoise.ar, freq * 2, 0.2);
    droneSig = droneSig * age * 0.3;

    // === HOLLOW (wind resonance) ===
    hollowSig = BPF.ar(PinkNoise.ar, freq * 1.5 * LFNoise2.kr(0.3).range(0.9, 1.1), 0.05);
    hollowSig = hollowSig + BPF.ar(PinkNoise.ar, freq * 2.5, 0.08);
    hollowSig = hollowSig * LFNoise1.kr(0.5).range(0.3, 1);
    hollowSig = hollowSig * hollow * 0.4;

    // === MIX ===
    sig = massSig + spaceSig + crackSig + droneSig + hollowSig;
    sig = sig.tanh;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] ruindrone loaded".postln;
