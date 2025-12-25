SynthDef(\forge_fuego_celeste_star_ping, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                           filterTypeBus, envEnabledBus, envSourceBus=0,
                                           clockRateBus, clockTrigBus,
                                           midiTrigBus=0, slotIndex=0,
                                           customBus0, customBus1, customBus2, customBus3, customBus4,
                                           portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var twinkle, distance, color, size, echo;
    var modRatio, modIndex, carrier, modulator, twinkleLFO, echoSig;

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

    // Theme parameters
    twinkle = In.kr(customBus0);    // scintillation rate
    distance = In.kr(customBus1);   // apparent distance
    color = In.kr(customBus2);      // warm red to cool blue
    size = In.kr(customBus3);       // apparent magnitude
    echo = In.kr(customBus4);       // cosmic reflection

    // Color determines FM ratio - red stars are warmer (lower ratio), blue stars brighter (higher)
    modRatio = color.linlin(0, 1, 1.5, 4.5);
    modIndex = color.linlin(0, 1, 2, 6);

    // FM synthesis - bell-like
    modulator = SinOsc.ar(freq * modRatio) * modIndex * freq;
    carrier = SinOsc.ar(freq + modulator);

    // Add sine fundamental for body (size)
    carrier = carrier + (SinOsc.ar(freq) * size * 0.5);

    // Add upper partials for sparkle
    carrier = carrier + (SinOsc.ar(freq * 3) * (1 - size) * 0.2);

    // Twinkle - amplitude tremolo
    twinkleLFO = SinOsc.kr(twinkle.linexp(0, 1, 2, 15)).range(0.7, 1.0);
    carrier = carrier * twinkleLFO;

    sig = carrier * 0.4;

    // Distance - high pass and level reduction
    sig = HPF.ar(sig, distance.linexp(0, 1, 100, 800));
    sig = sig * distance.linlin(0, 1, 1.0, 0.6);

    // Echo - simple comb filter reflection
    echoSig = CombL.ar(sig, 0.3, echo.linlin(0, 1, 0.05, 0.25), echo * 2);
    sig = sig + (echoSig * echo * 0.4);

    // Standard post-chain
    sig = ~stereoSpread.(sig, twinkle.linlin(0, 1, 0.2, 0.6), 0.4);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_fuego_celeste_star_ping loaded".postln;
