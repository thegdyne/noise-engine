// bed_stuy/radio — Lightweight end-stage generator
// radio: Boombox speaker - lo-fi blown driver
SynthDef(\forge_bed_stuy_radio, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var blown, bass, treble, static, battery;

    blown = p[0].linlin(0, 1, 1, 4);  // P1: Blown speaker drive
    bass = p[1].linlin(0, 1, 0.3, 1);  // P2: Bass boost
    treble = p[2].linlin(0, 1, 1000, 6000);  // P3: Treble cutoff
    static = p[3].linlin(0, 1, 0, 0.3);  // P4: Static noise
    battery = p[4].linlin(0, 1, 0.95, 1.05);  // P5: Battery wobble

    freq = In.kr(freqBus);

    // DSP: Base tone - slightly detuned
    sig = Saw.ar(freq * [1, 1.003] * LFNoise1.kr(0.2).range(battery.reciprocal, battery)) * 0.4;

    // Bass boost
    sig = sig + (SinOsc.ar(freq * 0.5) * bass * 0.3);

    // Blown speaker saturation
    sig = (sig * blown).tanh;

    // Speaker resonance - bandpass character
    sig = BPF.ar(sig, 800, 0.8) + (sig * 0.3);

    // Treble rolloff
    sig = LPF.ar(sig, treble);

    // Static noise
    sig = sig + (HPF.ar(WhiteNoise.ar(static), 2000) * LFNoise1.kr(0.5).range(0.5, 1));

    // Cabinet resonance
    sig = sig + (Ringz.ar(sig * 0.05, 150, 0.1));

    sig = sig * 0.4;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_bed_stuy_radio loaded".postln;
