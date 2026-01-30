// vapor_station/fluoro — Lightweight end-stage generator
// fluoro: Cold flickering fluorescent tubes
SynthDef(\forge_vapor_station_fluoro, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var buzz, cold, strobe, failing, tubes;

    buzz = p[0].linlin(0, 1, 0.3, 1);  // P1: Buzz intensity
    cold = p[1].linlin(0, 1, 0.2, 0.8);  // P2: Cold high harmonics
    strobe = p[2].linlin(0, 1, 0, 0.5);  // P3: Strobe flicker
    failing = p[3].linlin(0, 1, 0, 0.6);  // P4: Failing tube crackle
    tubes = p[4].linlin(0, 1, 1, 4);  // P5: Number of tubes

    freq = In.kr(freqBus);

    // DSP: High frequency buzz (different from sodium)
    sig = SinOsc.ar(120 * [1, 2, 3, 5]) * [1, 0.6, 0.3, 0.15] * buzz;
    sig = sig.sum;

    // Cold high harmonics
    sig = sig + (Blip.ar(freq * 2, tubes.round * 3) * cold * 0.2);

    // Strobe flicker - rapid on/off
    sig = sig * (1 - (LFPulse.kr(LFNoise0.kr(3).range(5, 15), 0, 0.5) * strobe));

    // Failing tube - crackle and sputter
    sig = sig + (HPF.ar(Dust2.ar(failing * 30) * 0.2, 1000));
    sig = sig * (1 - (Dust.kr(failing * 2) * 0.5).lag(0.001, 0.05));

    // Slight detuned copies for multiple tubes
    sig = sig + (DelayN.ar(sig, 0.01, 0.003) * 0.3);

    sig = sig * 0.3;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_vapor_station_fluoro loaded".postln;
