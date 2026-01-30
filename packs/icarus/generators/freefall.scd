// icarus/freefall — Lightweight end-stage generator
// Freefall -- rushing descent, wind roar, tumbling
// Role: motion

SynthDef(\forge_icarus_freefall, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var tumble, rush, void, spin, drag;
    var noise, sub, tumbleLfo, panLfo;

    freq = In.kr(freqBus);

    tumble = p[0].linlin(0, 1, 0.5, 12);  // Tumble rate Hz
    rush = p[1].linlin(0, 1, 0.1, 1.0);  // Noise intensity
    void = p[2].linlin(0, 1, 0.0, 0.6);  // Sub weight
    spin = p[3].linlin(0, 1, 0.1, 4);  // Pan rotation Hz
    drag = p[4].linexp(0, 1, 200, 4000);  // Internal filter

    // Tumbling modulation
    tumbleLfo = SinOsc.kr(tumble, 0, 0.3, 1);

    // Wind rush - filtered noise bands
    noise = PinkNoise.ar(rush) + WhiteNoise.ar(rush * 0.3);
    noise = BPF.ar(noise, freq * tumbleLfo, 0.4);
    noise = noise + BPF.ar(PinkNoise.ar(rush * 0.5), freq * 2 * tumbleLfo, 0.3);

    // Additional drag filtering
    noise = LPF.ar(noise, drag);

    // Sub void beneath
    sub = SinOsc.ar(freq * 0.25, 0, void);

    // Combine
    sig = noise + sub;

    // Stereo rotation - the tumble through space
    panLfo = SinOsc.kr(spin);
    sig = Pan2.ar(sig, panLfo);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_icarus_freefall loaded".postln;
