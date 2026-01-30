// bed_stuy/boom — Lightweight end-stage generator
// boom: 808-style sub bass kick
SynthDef(\forge_bed_stuy_boom, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var sub, punch, length, drive, click;
    var kickEnv;

    sub = p[0].linlin(0, 1, 0.3, 1);  // P1: Sub level
    punch = p[1].linlin(0, 1, 0.1, 0.7);  // P2: Attack punch
    length = p[2].linlin(0, 1, 0.1, 0.8);  // P3: Decay length
    drive = p[3].linlin(0, 1, 1, 3);  // P4: Saturation drive
    click = p[4].linlin(0, 1, 0, 0.5);  // P5: Click transient

    freq = In.kr(freqBus);

    // DSP: Continuous sub bass with pulse modulation
    kickEnv = LFPulse.kr(1, 0, 0.15).lag(0.005, length * 0.5);

    // Sub oscillator
    sig = SinOsc.ar(freq * 0.5) * sub;

    // Pitch envelope for punch
    sig = sig + (SinOsc.ar(freq * 0.5 * (1 + (kickEnv * punch * 2))) * punch * kickEnv * 0.5);

    // Click transient
    sig = sig + (HPF.ar(Dust.ar(2) * click, 1000) * kickEnv);

    // Saturation
    sig = (sig * drive).tanh;

    // Continuous low drone underneath
    sig = sig + (SinOsc.ar(freq * 0.25) * 0.2);

    sig = sig * 0.5;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_bed_stuy_boom loaded".postln;
