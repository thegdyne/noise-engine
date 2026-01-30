// _example/pulse_bass — Lightweight end-stage generator
/*
Pulse Bass Generator (Example Pack)
Classic pulse wave bass with PWM and sub oscillator

Custom params:
  - P1 pulse_width: 0.1-0.9 (pulse width)
  - P2 pwm_depth: 0-1 (PWM modulation depth)
  - P3 pwm_rate: 0.1-10 Hz (PWM rate, exp scaled)
  - P4 sub_level: 0-1 (sub oscillator level)
*/

SynthDef(\example_pulse_bass, { |out, freqBus, customBus0|
    var sig, freq;
    var p = In.kr(customBus0, 4);
    var pulseWidth, pwmDepth, pwmRate, subLevel;
    var pwmLfo, modWidth, pulse, sub;

    freq = In.kr(freqBus);

    // Custom params (pwm_rate is exp scaled 0.1-10 Hz in JSON)
    pulseWidth = p[0];
    pwmDepth = p[1];
    pwmRate = p[2].linexp(0, 1, 0.1, 10);
    subLevel = p[3];

    // === SOUND SOURCE ===
    pwmLfo = SinOsc.kr(pwmRate);
    modWidth = pulseWidth + (pwmLfo * pwmDepth * 0.3);
    modWidth = modWidth.clip(0.1, 0.9);

    pulse = Pulse.ar(freq, modWidth);
    sub = SinOsc.ar(freq * 0.5) * subLevel;

    sig = (pulse * 0.7) + sub;

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  [x] example_pulse_bass loaded".postln;
