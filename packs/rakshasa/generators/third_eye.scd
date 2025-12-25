// Third Eye — Piercing hypnotic FM tone
// Role: foreground | Family: FM

SynthDef(\forge_rakshasa_third_eye, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var gaze, trance, sight, focus, pulse;
    var carrier, modulator, fmIndex, tranceMod, pulseMod;
    var harmonicMix, focusBand;

    // Standard bus reads
    freq = In.kr(freqBus);
    portamento = In.kr(portamentoBus);
    freq = Lag.kr(freq, portamento.linexp(0, 1, 0.001, 0.5));
    filterFreq = In.kr(cutoffBus);
    rq = In.kr(resBus);
    attack = In.kr(attackBus);
    decay = In.kr(decayBus);
    filterType = In.kr(filterTypeBus);
    envSource = In.kr(envSourceBus);
    clockRate = In.kr(clockRateBus);
    amp = In.kr(~params[\amplitude]);

    // Custom parameters
    gaze = In.kr(customBus0).linexp(0, 1, 0.5, 8);         // FM index / brightness
    trance = In.kr(customBus1).linlin(0, 1, 0, 0.4);       // Modulation depth
    sight = In.kr(customBus2).linlin(0, 1, 1, 5);          // Harmonic ratio
    focus = In.kr(customBus3).linlin(0, 1, 0.5, 0.05);     // Bandwidth (inverted)
    pulse = In.kr(customBus4).linexp(0, 1, 0.1, 8);        // Pulse rate

    // Trance modulation — slow hypnotic movement
    tranceMod = SinOsc.kr(0.1 + (trance * 2)) * trance;

    // Pulse — internal throb
    pulseMod = SinOsc.kr(pulse).range(1 - (trance * 0.3), 1);

    // FM index varies with gaze and trance
    fmIndex = gaze * (1 + tranceMod);

    // Modulator frequency based on sight (harmonic reach)
    modulator = SinOsc.ar(freq * sight * (1 + (tranceMod * 0.2)));

    // Carrier with FM
    carrier = SinOsc.ar(freq + (modulator * fmIndex * freq));

    // Add harmonics for piercing gaze
    harmonicMix = SinOsc.ar(freq * 2) * 0.3 * gaze.linlin(0.5, 8, 0, 1);
    harmonicMix = harmonicMix + (SinOsc.ar(freq * 3) * 0.15 * gaze.linlin(0.5, 8, 0, 1));

    sig = (carrier + harmonicMix) * pulseMod;

    // Focus — bandpass for tight vs diffuse
    focusBand = BPF.ar(sig, freq * 1.5, focus);
    sig = (sig * (1 - focus.linlin(0.05, 0.5, 0.5, 0))) + (focusBand * focus.linlin(0.05, 0.5, 0.5, 0));

    // Stereo with subtle phase
    sig = [sig, DelayN.ar(sig, 0.01, 0.003)];

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp,
                   clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_rakshasa_third_eye loaded".postln;
