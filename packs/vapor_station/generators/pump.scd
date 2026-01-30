// vapor_station/pump — Lightweight end-stage generator
// pump: Mechanical fuel pump rhythm
SynthDef(\forge_vapor_station_pump, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var rate, stroke, mech, pressure, grind;
    var pumpEnv;

    rate = p[0].linlin(0, 1, 0.5, 4);  // P1: Pump rate
    stroke = p[1].linlin(0, 1, 0.3, 1);  // P2: Stroke intensity
    mech = p[2].linlin(0, 1, 0, 0.6);  // P3: Mechanical clatter
    pressure = p[3].linlin(0, 1, 0.2, 0.8);  // P4: Pressure hiss
    grind = p[4].linlin(0, 1, 0, 0.5);  // P5: Grinding texture

    freq = In.kr(freqBus);

    // DSP: Pump stroke - low thump
    pumpEnv = LFPulse.kr(rate, 0, 0.3).lag(0.02, 0.1);
    sig = SinOsc.ar(freq * 0.5) * pumpEnv * stroke;
    sig = sig + (LPF.ar(PinkNoise.ar(stroke * 0.3), freq) * pumpEnv);

    // Mechanical clatter
    sig = sig + (Ringz.ar(Dust.ar(rate * 5) * mech, freq * [2, 3.5], 0.05) * 0.4);

    // Pressure hiss (continuous)
    sig = sig + (HPF.ar(PinkNoise.ar(pressure * 0.3), 2000) * LFNoise1.kr(rate).range(0.5, 1));

    // Grinding undertone
    sig = sig + (LPF.ar(Crackle.ar(1.5) * grind * 0.2, freq * 3));

    sig = sig * 0.35;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_vapor_station_pump loaded".postln;
