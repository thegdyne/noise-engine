// Tiny Alien - Low, weird foundation like the spider's alien nature
// Subharmonic generator with strange modulation and slow drift

SynthDef(\forge_maratus_tiny_alien, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var alien, tiny, weird, creep, threat;
    var subFreq, mainOsc, subOsc, weirdMod, creepLFO, threatGrowl;

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
    alien = In.kr(customBus0);  // Detuning/dissonance
    tiny = In.kr(customBus1);  // Size/octave
    weird = In.kr(customBus2);  // FM complexity
    creep = In.kr(customBus3);  // Slow drift
    threat = In.kr(customBus4);  // Low growl

    // Slow creeping drift LFO
    creepLFO = LFNoise1.kr(creep.linexp(0, 1, 0.05, 0.5));

    // Subharmonic frequency - one or two octaves down based on tiny
    subFreq = freq * tiny.linlin(0, 1, 0.25, 1);

    // Alien detuning - slightly off from harmonic
    subFreq = subFreq * (1 + (alien * 0.06 * creepLFO));

    // Main oscillator with alien detune
    mainOsc = SinOsc.ar(freq * (1 + (alien * 0.03)));

    // Sub oscillator with triangle wave for warmth
    subOsc = LFTri.ar(subFreq);

    // Weird FM modulation - self-modulating sine
    weirdMod = SinOsc.ar(
        freq * weird.linlin(0, 1, 0.5, 2.3),
        SinOsc.ar(freq * 0.3) * weird * 3  // Self-modulation
    ) * weird * 0.5;

    // Mix main elements
    sig = (mainOsc * 0.4) + (subOsc * 0.4) + (weirdMod * 0.3);

    // Threat growl - low frequency amplitude modulation
    threatGrowl = 1 + (SinOsc.kr(threat.linexp(0, 1, 2, 15)) * threat * 0.5);
    sig = sig * threatGrowl;

    // Add some low frequency rumble for threat
    sig = sig + (LFNoise1.ar(threat.linexp(0, 1, 5, 30)) * threat * 0.2);

    // Creep modulates pitch slowly
    sig = sig + (SinOsc.ar(subFreq * (1 + (creepLFO * 0.1))) * creep * 0.2);

    // Soft saturation
    sig = (sig * 1.5).tanh * 0.6;

    // Moderate stereo - not too wide for bass
    sig = ~stereoSpread.(sig, 0.15, 0.3);

    // Mandatory output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_maratus_tiny_alien loaded".postln;
