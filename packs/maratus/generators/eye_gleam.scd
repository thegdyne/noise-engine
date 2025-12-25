// Eye Gleam - Sharp, focused stab like the spider's big reflective eyes
// FM synthesis with metallic bell-like quality

SynthDef(\forge_maratus_eye_gleam, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                      filterTypeBus, envEnabledBus, envSourceBus=0,
                                      clockRateBus, clockTrigBus,
                                      midiTrigBus=0, slotIndex=0,
                                      customBus0, customBus1, customBus2, customBus3, customBus4,
                                      portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var focus, gleam, eyeSize, reflect, stare;
    var carrier, modulator, modIndex, modRatio, metallic;

    // Standard reads
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

    // Theme params
    focus = In.kr(customBus0);  // Spectral tightness
    gleam = In.kr(customBus1);  // High sparkle
    eyeSize = In.kr(customBus2);  // Resonance body
    reflect = In.kr(customBus3);  // Metallic quality
    stare = In.kr(customBus4);  // Sustain

    // FM ratios for bell-like sound
    modRatio = eyeSize.linlin(0, 1, 1.4, 3.5);  // Inharmonic ratios for bell
    modIndex = focus.linexp(0, 1, 1, 8);

    // Modulator with envelope
    modulator = SinOsc.ar(freq * modRatio) * modIndex * freq;
    modulator = modulator * EnvGen.ar(Env.perc(0.001, stare.linlin(0, 1, 0.1, 0.8)));

    // Carrier
    carrier = SinOsc.ar(freq + modulator);

    // Add second harmonic for gleam
    sig = carrier + (SinOsc.ar(freq * 2 + (modulator * 0.5)) * gleam * 0.4);

    // Metallic reflection - comb filter resonance
    metallic = CombL.ar(sig * reflect, 0.01, 1 / (freq * 2.5), reflect.linlin(0, 1, 0.05, 0.2));
    sig = sig + (metallic * 0.3);

    // Focus - bandpass emphasis around fundamental
    sig = sig + (BPF.ar(sig, freq, focus.linexp(0, 1, 0.5, 0.1)) * focus * 0.5);

    // High frequency gleam sparkle
    sig = sig + (HPF.ar(sig, 4000) * gleam * 0.3);

    // Soft saturation for intensity
    sig = (sig * 1.5).tanh * 0.7;

    // Tight stereo for focused feel
    sig = ~stereoSpread.(sig, 0.4, 0.25);

    // Mandatory output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_maratus_eye_gleam loaded".postln;
