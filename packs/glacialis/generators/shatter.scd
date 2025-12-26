// SHATTER - Ice crack and splinter
// Dust-triggered resonant fractures

SynthDef(\forge_glacialis_shatter, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                      filterTypeBus, envEnabledBus, envSourceBus=0,
                                      clockRateBus, clockTrigBus,
                                      midiTrigBus=0, slotIndex=0,
                                      customBus0, customBus1, customBus2, customBus3, customBus4,
                                      portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var fracture, splinter, echo, weight, spray;
    var cracks, splinters, thuds, particles, trig;

    // Theme params
    fracture = In.kr(customBus0);  // Crack density
    splinter = In.kr(customBus1);  // Splinter pitch
    echo = In.kr(customBus2);      // Resonance decay
    weight = In.kr(customBus3);    // Low thud
    spray = In.kr(customBus4);     // Spread

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

    // Main crack triggers
    trig = Dust.ar(fracture.linexp(0, 1, 2, 40));

    // Sharp cracks - high resonant pings
    cracks = Ringz.ar(trig,
        freq * splinter.linexp(0, 1, 2, 8) * [1, 1.73, 2.41],
        echo.linexp(0, 1, 0.05, 0.4)
    ).sum * 0.4;

    // Ice splinters - higher density, varied pitch
    splinters = Dust.ar(fracture.linexp(0, 1, 10, 100) * spray);
    splinters = Ringz.ar(splinters,
        TRand.ar(freq * 3, freq * 12, splinters),
        echo.linexp(0, 1, 0.02, 0.15)
    ) * 0.2 * spray;

    // Low thuds for heavy cracks
    thuds = Ringz.ar(trig * weight,
        freq * [0.5, 0.75, 1],
        echo.linexp(0, 1, 0.1, 0.5)
    ).sum * 0.5 * weight;

    // Combine
    sig = cracks + splinters + thuds;

    // Add some white noise burst for texture
    particles = WhiteNoise.ar(1) * Decay.ar(trig, 0.02) * 0.2;
    particles = HPF.ar(particles, 2000);
    sig = sig + (particles * spray);

    // Stereo spray
    sig = [
        sig + (DelayC.ar(sig, 0.05, spray.linlin(0, 1, 0.001, 0.02)) * 0.3),
        sig + (DelayC.ar(sig, 0.05, spray.linlin(0, 1, 0.002, 0.03)) * 0.3)
    ];

    // Remove DC from impulsive content
    sig = LeakDC.ar(sig);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_glacialis_shatter loaded".postln;
