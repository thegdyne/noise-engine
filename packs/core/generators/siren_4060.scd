// core/siren_4060 — Lightweight end-stage generator
/*
4060 Siren Generator
CD4060 counter/divider siren circuit

Signal flow: Counter outputs -> Mix -> Filter -> ENV VCA -> Output

Custom params:
  - P1 clock_rate: 0-1 (master clock speed)
  - P2 division_mix: 0-1 (which counter outputs)
  - P3 sweep_rate: 0-1 (pitch sweep speed)
  - P4 sweep_depth: 0-1 (pitch sweep amount)
  - P5 reset_chaos: 0-1 (counter reset randomness)
*/

SynthDef(\siren4060, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var clockR, divMix, sweepRate, sweepDepth, resetChaos;
    var masterClock, divisions, sweep;

    freq = In.kr(freqBus);

    clockR = p[0];
    divMix = p[1];
    sweepRate = p[2];
    sweepDepth = p[3];
    resetChaos = p[4];

    // === SOUND SOURCE ===
    sweep = SinOsc.kr(sweepRate.linexp(0, 1, 0.1, 10)) * sweepDepth;
    masterClock = freq * clockR.linexp(0, 1, 0.5, 4) * (1 + sweep);

    divisions = Mix([
        Pulse.ar(masterClock / 2, 0.5) * (1 - divMix),
        Pulse.ar(masterClock / 4, 0.5) * divMix.sqrt,
        Pulse.ar(masterClock / 8, 0.5) * divMix,
        Pulse.ar(masterClock / 16, 0.5) * (divMix ** 2)
    ]) * 0.25;

    sig = divisions;
    sig = sig + (Dust.ar(resetChaos.linexp(0, 1, 1, 100)) * resetChaos * 0.2);


    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] siren4060 loaded".postln;
