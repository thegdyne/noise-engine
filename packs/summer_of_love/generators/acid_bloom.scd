// summer_of_love/acid_bloom — Lightweight end-stage generator
SynthDef(\forge_summer_of_love_acid_bloom, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var squelch, bloom, trip, dose, sub;
    var osc, subOsc, filtEnv, envTrig, filtFreqMod, saturated;

    freq = In.kr(freqBus);

    squelch = p[0];  // Filter env amount
    bloom = p[1];  // Filter env decay
    trip = p[2];  // Resonance boost
    dose = p[3];  // Distortion
    sub = p[4];  // Sub oscillator

    // Main saw oscillator with slight detuning for thickness
    osc = Saw.ar(freq) + (Saw.ar(freq * 1.005) * 0.5) + (Pulse.ar(freq, 0.5) * 0.3);
    osc = osc * 0.5;

    // Sub oscillator - one octave down square
    subOsc = Pulse.ar(freq * 0.5, 0.5) * sub * 0.6;

    sig = osc + subOsc;

    // One-shot trigger (end-stage handles retriggering)
    envTrig = Impulse.ar(0);

    // Filter envelope - this is the "acid" character
    filtEnv = EnvGen.ar(
        Env.perc(0.001, bloom.linexp(0, 1, 0.05, 0.8)),
        envTrig
    );

    // Modulate filter cutoff with envelope
    filtFreqMod = 2000 * (1 + (filtEnv * squelch * 8));

    // Resonant lowpass - trip boosts resonance beyond UI setting
    // Using RLPF for that 303 character
    sig = RLPF.ar(sig, filtFreqMod.clip(50, 16000), (0.3 * (1 - (trip * 0.7))).clip(0.1, 1));

    // Distortion/overdrive
    saturated = (sig * (1 + (dose * 4))).tanh;
    sig = XFade2.ar(sig, saturated, dose.linlin(0, 1, -1, 0.8));

    // Compensate for resonance volume loss
    sig = sig * (1 + (trip * 0.5));

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;
"  * forge_summer_of_love_acid_bloom loaded".postln;
