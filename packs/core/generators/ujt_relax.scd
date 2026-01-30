// core/ujt_relax — Lightweight end-stage generator
/*
UJT Relax Generator
Unijunction transistor relaxation oscillator

Signal flow: UJT Oscillator -> Waveshaping -> Filter -> ENV VCA -> Output

Custom params:
  - P1 peak_voltage: 0-1 (firing threshold)
  - P2 valley_voltage: 0-1 (reset threshold)
  - P3 capacitance: 0-1 (timing cap size)
  - P4 resistance: 0-1 (charge resistance)
  - P5 temperature: 0-1 (thermal drift simulation)
*/

SynthDef(\ujtRelax, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var peakV, valleyV, capacitance, resistance, temperature;
    var osc, drift, spike;

    freq = In.kr(freqBus);

    peakV = p[0];
    valleyV = p[1];
    capacitance = p[2];
    resistance = p[3];
    temperature = p[4];

    // === SOUND SOURCE ===
    drift = LFNoise1.kr(temperature.linexp(0, 1, 0.1, 5)) * temperature * 0.1;

    osc = LFSaw.ar(freq * capacitance.linexp(0, 1, 0.5, 2) * (1 + drift));
    osc = osc.linlin(-1, 1, valleyV, peakV);

    spike = Impulse.ar(freq * capacitance.linexp(0, 1, 0.5, 2)) * resistance * 0.5;
    spike = spike * EnvGen.ar(Env.perc(0.0001, 0.01));

    sig = osc + spike;
    sig = (sig * (1 + resistance)).tanh * 0.7;

    sig = ~stereoSpread.(sig, 0.25, 0.3);
    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] ujtRelax loaded".postln;
