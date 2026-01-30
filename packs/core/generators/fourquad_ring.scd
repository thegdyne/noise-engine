// core/fourquad_ring — Lightweight end-stage generator
/*
Four-Quadrant Ring Generator
Balanced four-quadrant multiplier ring modulator

Signal flow: Carrier x Modulator (balanced) -> Filter -> ENV VCA -> Output

Custom params:
  - P1 mod_ratio: 0.1-10 (modulator frequency ratio)
  - P2 balance: 0-1 (carrier bleed amount)
  - P3 symmetry: 0-1 (quadrant balance)
  - P4 carrier_wave: 0-1 (sine <-> triangle)
  - P5 mod_wave: 0-1 (sine <-> triangle)
*/

SynthDef(\fourQuadRing, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var modRatio, balance, symmetry, carrierWave, modWave;
    var carrier, modulator, modFreq, ring;

    freq = In.kr(freqBus);

    modRatio = p[0];
    balance = p[1];
    symmetry = p[2];
    carrierWave = p[3];
    modWave = p[4];

    // === SOUND SOURCE ===
    modFreq = freq * modRatio;

    carrier = SelectX.ar(carrierWave, [
        SinOsc.ar(freq),
        LFTri.ar(freq)
    ]);

    modulator = SelectX.ar(modWave, [
        SinOsc.ar(modFreq),
        LFTri.ar(modFreq)
    ]);

    ring = carrier * modulator;
    ring = ring + (carrier * balance * 0.5);

    sig = (ring * symmetry.linlin(0, 1, 0.5, 1.5)).softclip;


    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] fourQuadRing loaded".postln;
