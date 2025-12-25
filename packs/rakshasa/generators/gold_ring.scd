// Gold Ring — Metallic ring modulation with pendulum swing
// Role: motion | Family: physical

SynthDef(\forge_rakshasa_gold_ring, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var metal, shine, swing, clang, chain;
    var carrier, modulator, ringMod, shimmer, swingMod;
    var clangEnv, resonance;

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
    metal = In.kr(customBus0).linlin(0, 1, 0, 1);          // Ring mod mix
    shine = In.kr(customBus1).linexp(0, 1, 1, 4);          // Brightness/harmonics
    swing = In.kr(customBus2).linexp(0, 1, 0.2, 5);        // Pendulum rate
    clang = In.kr(customBus3).linexp(0, 1, 0.01, 0.001);   // Attack sharpness
    chain = In.kr(customBus4).linlin(0, 1, 0.9, 0.998);    // Resonance/sustain

    // Swing modulation — pendulum movement
    swingMod = SinOsc.kr(swing).range(0.95, 1.05);

    // Carrier — clean tone
    carrier = SinOsc.ar(freq * swingMod);

    // Modulator for ring mod — inharmonic ratio for metal
    modulator = SinOsc.ar(freq * 1.414 * swingMod);  // sqrt(2) for metallic

    // Ring modulation
    ringMod = carrier * modulator;

    // Mix clean and ring mod based on metal
    sig = (carrier * (1 - metal)) + (ringMod * metal);

    // Shimmer — high harmonics for gold shine
    shimmer = SinOsc.ar(freq * shine * swingMod) * 0.2;
    shimmer = shimmer + (SinOsc.ar(freq * shine * 1.5 * swingMod) * 0.1);
    sig = sig + (shimmer * shine.linlin(1, 4, 0, 0.5));

    // Resonant ringing with feedback for chain
    resonance = CombL.ar(sig, 0.1, 1/freq, decay * chain.linlin(0.9, 0.998, 0.5, 4));
    sig = sig + (resonance * chain.linlin(0.9, 0.998, 0, 0.4));

    // Stereo swing
    sig = Pan2.ar(sig, SinOsc.kr(swing * 0.7).range(-0.5, 0.5));

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp,
                   clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_rakshasa_gold_ring loaded".postln;
