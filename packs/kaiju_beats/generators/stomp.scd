// kaiju_beats/stomp — Lightweight end-stage generator
SynthDef(\forge_kaiju_beats_stomp, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var weight, punch, thud, rumble, width;
    var subOsc, pulseOsc, noiseHit;

    weight = p[0];  // P1: Weight - sub content
    punch = p[1];  // P2: Punch - transient attack
    thud = p[2];  // P3: Thud - body thickness
    rumble = p[3];  // P4: Rumble - low frequency motion
    width = p[4];  // P5: Stereo width

    freq = In.kr(freqBus);
    ampVal = 0.2;

    // Sub oscillator - sine for clean low end
    subOsc = SinOsc.ar(freq * 0.5);
    subOsc = subOsc * weight;

    // Add rumble modulation
    subOsc = subOsc * (1 + (LFNoise2.kr(0.5 + (rumble * 2)) * rumble * 0.3));

    // Pulse oscillator for body/thud
    pulseOsc = Pulse.ar(freq, 0.3 + (thud * 0.2));
    pulseOsc = pulseOsc + (Pulse.ar(freq * 0.5, 0.5) * 0.5);

    // Add saw for grit
    pulseOsc = pulseOsc + (LFSaw.ar(freq) * thud * 0.3);

    // Punch - noise transient
    noiseHit = LPF.ar(BrownNoise.ar(1), 200 + (punch * 300));
    noiseHit = noiseHit * punch * 0.4;

    // Mix
    sig = (subOsc * 0.6) + (pulseOsc * 0.5) + noiseHit;

    // Add stereo width via subtle detune
    sig = [
        sig + (SinOsc.ar(freq * 0.501) * width * 0.1),
        sig + (SinOsc.ar(freq * 0.499) * width * 0.1)
    ];

    // Soft saturation
    sig = (sig * 1.3).tanh * 0.8;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_kaiju_beats_stomp loaded".postln;
