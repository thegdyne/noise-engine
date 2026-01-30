// kaiju_beats/boom — Lightweight end-stage generator
SynthDef(\forge_kaiju_beats_boom, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var bits, rate, wow, hiss, bass;
    var source, crushed, tapeWow, tapeHiss;

    bits = p[0];  // P1: Bit depth reduction
    rate = p[1];  // P2: Sample rate reduction
    wow = p[2];  // P3: Tape wow/flutter
    hiss = p[3];  // P4: Tape hiss amount
    bass = p[4];  // P5: Boombox bass boost

    freq = In.kr(freqBus);
    ampVal = 0.2;

    // Tape wow - pitch modulation
    tapeWow = SinOsc.kr(0.3 + (LFNoise1.kr(0.1) * 0.2)) * wow * 0.03;

    // Source - thick saw/pulse combo for that boombox vibe
    source = Saw.ar(freq * (1 + tapeWow));
    source = source + Pulse.ar(freq * 0.5 * (1 + tapeWow), 0.5) * 0.7;
    source = source + SinOsc.ar(freq * (1 + tapeWow)) * 0.5;

    // Bass boost - subharmonic
    source = source + (SinOsc.ar(freq * 0.5) * bass * 0.6);

    // Bitcrushing
    crushed = source.round(2.pow(1 - (bits * 8)).max(0.001));

    // Sample rate reduction
    crushed = Latch.ar(crushed, Impulse.ar(SampleRate.ir * (0.1 + (rate.neg + 1) * 0.9)));

    // Tape hiss
    tapeHiss = HPF.ar(WhiteNoise.ar(hiss * 0.15), 2000);

    // Mix
    sig = crushed + tapeHiss;

    // Slight saturation for warmth
    sig = (sig * 1.5).tanh * 0.7;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_kaiju_beats_boom loaded".postln;
