// ROUTEMASTER - Engine rumble and mechanical movement like the red bus
// Family: fm (feedback_fm)
// Role: motion

SynthDef(\forge_barbican_hound_routemaster, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                               filterTypeBus, envEnabledBus, envSourceBus=0,
                                               clockRateBus, clockTrigBus,
                                               midiTrigBus=0, slotIndex=0,
                                               customBus0, customBus1, customBus2, customBus3, customBus4,
                                               portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var idle, rev, chug, heat, dist;
    var carrier, modulator, feedback, chugLfo, engine;

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
    idle = In.kr(customBus0);   // Engine base frequency
    rev = In.kr(customBus1);    // Modulation depth
    chug = In.kr(customBus2);   // Rhythmic pulse
    heat = In.kr(customBus3);   // Drive/warmth
    dist = In.kr(customBus4);   // Distance/presence

    // Engine frequency modified by idle
    freq = freq * idle.linexp(0, 1, 0.5, 2);

    // Chug rhythm - engine pulse
    chugLfo = LFPulse.kr(freq * 0.02, 0, 0.3 + (chug * 0.4)) * chug;

    // Feedback FM synthesis
    feedback = LocalIn.ar(1) * rev.linexp(0, 1, 0.1, 3);
    modulator = SinOsc.ar(freq * 0.5, feedback) * rev * freq;
    carrier = SinOsc.ar(freq + modulator);

    // Add sub-harmonic rumble
    engine = carrier + (SinOsc.ar(freq * 0.25) * 0.4);

    // Apply chug modulation
    engine = engine * (1 - (chugLfo * 0.5));

    // Feedback path
    LocalOut.ar(carrier);

    // Heat saturation
    engine = (engine * heat.linexp(0, 1, 1, 4)).tanh;

    // Distance filtering (close = bright, far = muffled)
    engine = LPF.ar(engine, dist.linexp(0, 1, 1000, 8000));

    // Stereo with subtle movement
    sig = Pan2.ar(engine, SinOsc.kr(0.15) * 0.3);

    // Post-chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    sig = Limiter.ar(sig, 0.95);
    Out.ar(out, sig);
}).add;

"  * forge_barbican_hound_routemaster loaded".postln;
