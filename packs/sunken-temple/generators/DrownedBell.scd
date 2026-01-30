// sunken-temple/DrownedBell — Lightweight end-stage generator
/*
DROWNEDBELL Generator
Ancient bells submerged in flooded ruins

Features:
  - Deep metallic bell tones
  - Water-filtered harmonics
  - Pitch drift from corrosion
  - Submerged reverberant echo

Custom params:
  - P1 depth: Underwater filtering
  - P2 toll: Strike intensity
  - P3 detune: Pitch warping
  - P4 rust: Corroded overtones
  - P5 echo: Submerged reflections
*/

SynthDef(\drownedbell, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var depth, toll, detune, rust, echo;
    var trig, bellSig, bellEnv;
    var partials, detuneAmt, waterFilter;

    freq = In.kr(freqBus);

    depth = p[0];
    depth = Lag.kr(depth, 0.1);
    toll = p[1];
    toll = Lag.kr(toll, 0.05);
    detune = p[2];
    detune = Lag.kr(detune, 0.1);
    rust = p[3];
    rust = Lag.kr(rust, 0.1);
    echo = p[4];
    echo = Lag.kr(echo, 0.1);

    // === TRIGGER ===
    trig = Select.ar(envSource.round.clip(0, 2), [
        DC.ar(0),
        Select.ar(clockRate.round.clip(0, 12), In.ar(clockTrigBus, 13)),
        Select.ar(slotIndex.clip(0, 7), In.ar(midiTrigBus, 8))
    ]);

    // Slow pitch drift
    detuneAmt = LFNoise2.kr(0.3 + (detune * 0.5)).range(1 - (detune * 0.05), 1 + (detune * 0.05));

    // === BELL PARTIALS ===
    // Classic bell ratios with underwater warping
    partials = [1, 2.0, 2.4, 3.0, 4.2, 5.4, 6.8] * freq * detuneAmt;

    bellEnv = EnvGen.ar(Env.perc(0.001, 2 + (toll * 3)), trig + Dust.ar(toll * 0.5));

    bellSig = Mix.fill(7, { |i|
        var partial = partials[i];
        var partialAmp = (1 / (i + 1).sqrt) * (1 - (rust * 0.1 * i));
        var wobble = SinOsc.kr(0.2 + (i * 0.1), i).range(0.99, 1.01);
        SinOsc.ar(partial * wobble) * partialAmp
    });

    // Strike transient
    bellSig = bellSig + (BPF.ar(WhiteNoise.ar, freq * 3, 0.1) * EnvGen.ar(Env.perc(0.001, 0.02), trig) * toll);

    bellSig = bellSig * bellEnv;

    // === RUST (inharmonic partials) ===
    bellSig = bellSig + (
        SinOsc.ar(freq * 2.73 * detuneAmt) * rust * 0.2 * bellEnv +
        SinOsc.ar(freq * 4.17 * detuneAmt) * rust * 0.15 * bellEnv
    );

    // === UNDERWATER FILTERING ===
    waterFilter = LinExp.kr(depth, 0, 1, 8000, 400);
    bellSig = LPF.ar(bellSig, waterFilter);
    bellSig = bellSig + (LPF.ar(bellSig, 200) * depth * 0.5);  // Murky doubling

    // === SUBMERGED ECHO ===
    bellSig = bellSig + (CombL.ar(bellSig, 0.5, 0.3 + (depth * 0.2), echo * 4) * echo * 0.4);
    bellSig = bellSig + (CombL.ar(bellSig, 0.5, 0.17, echo * 3) * echo * 0.3);

    sig = bellSig * 0.3;

    sig = ~stereoSpread.(sig, 0.3, 0.15);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] drownedbell loaded".postln;
