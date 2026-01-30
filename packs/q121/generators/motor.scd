// q121/motor — Lightweight end-stage generator
SynthDef(\forge_q121_motor, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var rpm, load, hum, grind, throb;
    var motorBase, humOsc, grindNoise, throbLFO, pwmMod;

    rpm = p[0];
    load = p[1];
    hum = p[2];
    grind = p[3];
    throb = p[4];

    freq = In.kr(freqBus);

    // Throbbing modulation - motor pulsation
    throbLFO = SinOsc.kr(rpm.linexp(0, 1, 1, 15)).range(1 - (throb * 0.4), 1);

    // PWM modulation for load variation
    pwmMod = LFNoise1.kr(load.linexp(0, 1, 0.5, 4)).range(0.3, 0.7);

    // Motor base - dark pulse waves with detune
    motorBase = Pulse.ar(freq, pwmMod, 0.4);
    motorBase = motorBase + Pulse.ar(freq * 1.003, pwmMod * 0.9, 0.3);
    motorBase = motorBase + Pulse.ar(freq * 0.998, pwmMod * 1.1, 0.3);
    motorBase = motorBase + Pulse.ar(freq * 0.5, 0.5, 0.5);

    // 50/60Hz electromagnetic hum harmonics
    humOsc = SinOsc.ar(freq) * 0.3;
    humOsc = humOsc + (SinOsc.ar(freq * 2) * 0.2);
    humOsc = humOsc + (SinOsc.ar(freq * 3) * 0.1);
    humOsc = humOsc + (SinOsc.ar(freq * 4) * 0.05);
    humOsc = humOsc * hum;

    // Bearing grind - filtered noise
    grindNoise = BPF.ar(GrayNoise.ar(1), freq * rpm.linexp(0, 1, 4, 16), 0.4);
    grindNoise = grindNoise + BPF.ar(PinkNoise.ar(0.5), freq * 6, 0.3);
    grindNoise = grindNoise * grind * 0.4;

    // Mix
    sig = (motorBase * 0.4) + humOsc + grindNoise;
    sig = sig * throbLFO;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_q121_motor loaded".postln;
