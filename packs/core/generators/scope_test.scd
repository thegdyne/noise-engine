// core/scope_test — Classic waveform test oscillator
/*
Scope Test Generator
Clean classic waveforms for testing the scope tap.

Waveforms (via P1 WAVE):
  0.00-0.24  Sine
  0.25-0.49  Triangle
  0.50-0.74  Square
  0.75-1.00  Pulse (width set by P2)

Custom params:
  - P1 wave: Waveform select (sine/tri/sq/pulse)
  - P2 pw: Pulse width (only affects pulse mode)
  - P3 (unused)
  - P4 (unused)
  - P5 (unused)
*/

SynthDef(\scope_test, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 5);
    var wave, pw;
    var sine, tri, square, pulse;

    freq = In.kr(freqBus);

    wave = p[0];   // 0-1: sine/tri/sq/pulse
    pw = p[1].linlin(0, 1, 0.05, 0.95);  // Pulse width 5-95%

    // === FOUR CLASSIC WAVEFORMS ===
    sine   = SinOsc.ar(freq);
    tri    = LFTri.ar(freq);
    square = LFPulse.ar(freq, width: 0.5) * 2 - 1;  // Bipolar
    pulse  = LFPulse.ar(freq, width: pw) * 2 - 1;    // Bipolar with PW

    // Select waveform (4 zones across 0-1)
    sig = Select.ar((wave * 3).round.clip(0, 3), [
        sine,
        tri,
        square,
        pulse
    ]);

    // Stereo output
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] scope_test loaded".postln;
