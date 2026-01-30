// rakshasa/tongue_lash — Lightweight end-stage generator
// Tongue Lash -- Forked tongue with pitch dive and squelchy FM
// Role: accent | Family: FM

SynthDef(\forge_rakshasa_tongue_lash, { |out, freqBus, customBus0|

    var sig, freq;
    var p = In.kr(customBus0, 5);
    var fork, lash, slime, curl, drip;
    var tongue1, tongue2, modulator, pitchEnv, detuneAmt, fmDepth, vibrato;

    // Standard bus reads
    freq = In.kr(freqBus);

    // Custom parameters
    fork = p[0].linlin(0, 1, 1, 2.5);  // Detune ratio
    lash = p[1].linexp(0, 1, 1.01, 4);  // Pitch dive multiplier
    slime = p[2].linexp(0, 1, 0.5, 8);  // FM index
    curl = p[3].linlin(0, 1, 0, 12);  // Vibrato Hz
    drip = p[4].linlin(0, 1, 0.3, 2);  // Decay modifier

    // Pitch envelope -- dives down from high on trigger
    pitchEnv = EnvGen.kr(Env.perc(0.001, decay * drip), doneAction: 0);
    freq = freq * (1 + ((lash - 1) * pitchEnv));

    // Vibrato/curl
    vibrato = SinOsc.kr(curl, 0, curl.linlin(0, 12, 0, 0.02));
    freq = freq * (1 + vibrato);

    // Detuning for forked tongues
    detuneAmt = (fork - 1) * 0.5;

    // FM modulator -- squelchy character
    modulator = SinOsc.ar(freq * 2) * slime * freq;

    // Two forked tongue oscillators
    tongue1 = SinOsc.ar(freq * (1 - detuneAmt) + modulator);
    tongue2 = SinOsc.ar(freq * (1 + detuneAmt) + (modulator * 0.7));

    // Combine with stereo split
    sig = [tongue1 * 0.7 + (tongue2 * 0.3), tongue2 * 0.7 + (tongue1 * 0.3)];

                   clockTrigBus, midiTrigBus, slotIndex);

    // Mandatory tail
    sig = NumChannels.ar(sig, 2);
    ReplaceOut.ar(out, sig);
}).add;

"  * forge_rakshasa_tongue_lash loaded".postln;
