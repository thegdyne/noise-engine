// Dance Step - Rhythmic percussive hit for the courtship dance
// Sharp attack with body resonance, like tiny precise footsteps

SynthDef(\forge_maratus_dance_step, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var step, floor, tap, bounce, groove;
    var body, click, pitchEnv, bodyFreq, grooveNoise;

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
    step = In.kr(customBus0);  // Attack sharpness
    floor = In.kr(customBus1);  // Body/low resonance
    tap = In.kr(customBus2);  // Click transient
    bounce = In.kr(customBus3);  // Pitch envelope
    groove = In.kr(customBus4);  // Timing humanization

    // Pitch envelope for bounce
    pitchEnv = EnvGen.ar(Env.perc(0.001, 0.08)) * bounce * 2;
    bodyFreq = freq * (1 + pitchEnv);

    // Body resonance - low sine with pitch drop
    body = SinOsc.ar(bodyFreq * floor.linexp(0, 1, 0.5, 1.5));
    body = body * EnvGen.ar(Env.perc(step.linexp(0, 1, 0.01, 0.001), 0.15));
    body = body * floor;

    // Tap click - filtered noise burst
    click = WhiteNoise.ar;
    click = HPF.ar(click, 2000 + (tap * 6000));
    click = click * EnvGen.ar(Env.perc(0.0005, step.linexp(0, 1, 0.03, 0.008)));
    click = click * tap * 0.5;

    // Mix body and click
    sig = body + click;

    // Add subtle tonal element at freq
    sig = sig + (SinOsc.ar(freq) * EnvGen.ar(Env.perc(0.001, 0.1)) * 0.3);

    // Groove - subtle random modulation on amplitude (simulates timing feel)
    grooveNoise = LFNoise1.kr(20) * groove * 0.15;
    sig = sig * (1 + grooveNoise);

    // Subtle stereo
    sig = ~stereoSpread.(sig, 0.5, 0.2);

    // Mandatory output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_maratus_dance_step loaded".postln;
