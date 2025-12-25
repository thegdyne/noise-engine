// MYOFIBER — Muscle fiber bowed string
// Physical modeling of muscle tissue — warm, organic, pulsing

SynthDef(\forge_nerve_glow_myofiber, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var fiber, actin, contract, warmth, twitch;
    var bowPos, bowForce, vibRate, vibDepth;
    var fundamental, harmonics, body;

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

    // Custom params
    fiber = In.kr(customBus0).linlin(0, 1, 0.1, 0.9);      // Bow position
    actin = In.kr(customBus1).linexp(0, 1, 0.3, 3.0);     // Pressure variation rate
    contract = In.kr(customBus2).linlin(0, 1, 0.2, 0.9);  // Bow force
    warmth = In.kr(customBus3).linlin(0, 1, 1, 8);        // Harmonics count
    twitch = In.kr(customBus4).linexp(0, 1, 0.5, 12);     // Vibrato rate

    // Bow position modulation (actin sliding)
    bowPos = fiber + (SinOsc.kr(actin, 0, 0.15));

    // Muscle twitch vibrato
    vibRate = twitch;
    vibDepth = twitch.linlin(0.5, 12, 0.002, 0.015);

    // Bowed string simulation using saw + feedback
    fundamental = VarSaw.ar(
        freq * (1 + SinOsc.kr(vibRate, 0, vibDepth)),
        0,
        bowPos
    );

    // Add harmonics for warmth (like muscle fiber bundles)
    harmonics = Mix.fill(8, { |i|
        var hAmp = (warmth - i).clip(0, 1) * (0.7 ** i);
        var hFreq = freq * (i + 1) * (1 + SinOsc.kr(vibRate * (1 + (i * 0.1)), i * 0.5, vibDepth * 0.5));
        SinOsc.ar(hFreq) * hAmp * 0.12
    });

    // Bow friction noise
    body = BrownNoise.ar(0.03) * contract;
    body = BPF.ar(body, freq * 2, 0.3);

    sig = (fundamental * contract * 0.4) + harmonics + body;

    // Soft clip for organic warmth
    sig = (sig * 1.5).tanh * 0.7;

    // Stereo spread
    sig = ~stereoSpread.(sig, 0.3, 0.2);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_nerve_glow_myofiber loaded".postln;
