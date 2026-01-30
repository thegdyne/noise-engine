// gotham_stairs/triumph — Lightweight end-stage generator
SynthDef(\forge_gotham_stairs_triumph, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var power, spread, rise, dark, glory;
    var sawStack, subOsc, riseOsc, numSaws, detunes, pans;

    power = p[0];
    spread = p[1];
    rise = p[2];
    dark = p[3];
    glory = p[4];

    freq = In.kr(freqBus);

    // Rising motion - slow upward pitch drift
    freq = freq * (1 + (rise * SinOsc.kr(0.15).range(0, 0.1)));

    // Supersaw stack - detuned saw waves for massive sound
    numSaws = 7;
    detunes = [-0.12, -0.08, -0.04, 0, 0.04, 0.08, 0.12] * power.linlin(0, 1, 0.5, 2);
    pans = [-1, -0.6, -0.3, 0, 0.3, 0.6, 1] * spread;

    sawStack = Mix.fill(7, { |i|
        var sawFreq = freq * (1 + (detunes[i] * 0.01));
        var sawSig = Saw.ar(sawFreq);
        var panPos = pans[i];
        Pan2.ar(sawSig, panPos) * (0.15 / numSaws.sqrt)
    });

    // Sub oscillator for dark undertone
    subOsc = SinOsc.ar(freq * 0.5, 0, dark * 0.3);
    subOsc = subOsc + (Pulse.ar(freq * 0.5, 0.3) * dark * 0.15);

    // Glory harmonics - additional brightness
    riseOsc = Saw.ar(freq * 2) * glory * 0.1;
    riseOsc = riseOsc + (Pulse.ar(freq * 3, 0.2) * glory * 0.05);

    sig = sawStack + subOsc + riseOsc;

    // Power swell modulation
    sig = sig * (0.7 + (power * 0.3));

    // Slight chorus for extra width
    sig = sig + (DelayC.ar(sig, 0.03, SinOsc.kr(0.5).range(0.01, 0.02)) * spread * 0.3);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_gotham_stairs_triumph loaded".postln;
