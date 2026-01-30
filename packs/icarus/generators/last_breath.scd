// icarus/last_breath — Lightweight end-stage generator
// Last Breath -- human fragility, heartbeat and breath
// Role: foreground

SynthDef(\forge_icarus_last_breath, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var heart, breath, fear, flesh, final;
    var pulse, inhale, tremble, body, heartTrig;

    freq = In.kr(freqBus);

    heart = p[0].linlin(0, 1, 0.8, 3);  // Heart rate Hz (48-180 bpm)
    breath = p[1].linlin(0, 1, 0.1, 0.5);  // Breath cycle Hz
    fear = p[2].linlin(0, 1, 0.0, 0.3);  // Trembling amount
    flesh = p[3].linlin(0, 1, 0.2, 0.8);  // Body resonance
    final = p[4].linlin(0, 1, 1.0, 0.3);  // Fading level

    // Fear trembling
    tremble = LFNoise2.kr(8 + (fear * 20), fear, 1);

    // Heartbeat - low thump with double-beat pattern
    heartTrig = Impulse.ar(heart) + Impulse.ar(heart, 0.3);
    pulse = SinOsc.ar(freq * 0.5 * tremble, 0, 0.6);
    pulse = pulse * Decay2.ar(heartTrig, 0.01, 0.15);

    // Breathing - filtered noise sweep
    inhale = PinkNoise.ar(0.4);
    inhale = BPF.ar(inhale, freq * SinOsc.kr(breath, 0, 0.5, 1.5), 0.3);

    // Flesh - formant resonances (organic body sound)
    body = Saw.ar(freq * tremble, flesh * 0.3);
    body = Formlet.ar(body, freq * 1.5, 0.005, 0.1);
    body = body + Formlet.ar(body, freq * 2.5, 0.005, 0.08);

    // Combine with fading
    sig = (pulse + inhale + body) * final;

    // Intimate stereo - close to the heart
    sig = ~stereoSpread.(sig, 0.05, 0.2);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_icarus_last_breath loaded".postln;
