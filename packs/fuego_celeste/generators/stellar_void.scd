SynthDef(\forge_fuego_celeste_stellar_void, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                              filterTypeBus, envEnabledBus, envSourceBus=0,
                                              clockRateBus, clockTrigBus,
                                              midiTrigBus=0, slotIndex=0,
                                              customBus0, customBus1, customBus2, customBus3, customBus4,
                                              portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var vast, drift, cold, stars, distance;
    var driftLFO, voices, starShimmer, coldFilter;

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
    vast = In.kr(customBus0);       // scale/spaciousness
    drift = In.kr(customBus1);      // pitch movement rate
    cold = In.kr(customBus2);       // spectral coldness
    stars = In.kr(customBus3);      // high sparkle
    distance = In.kr(customBus4);   // apparent distance

    // Very slow drift - cosmic timescales
    driftLFO = LFNoise1.kr(drift.linexp(0, 1, 0.01, 0.15));

    // Multiple detuned voices for vast pad
    voices = Mix.fill(6, { |i|
        var detune, pan, voiceDrift;
        detune = (i - 2.5) * 0.003 * vast;
        voiceDrift = driftLFO * (i + 1) * 0.005;
        pan = (i - 2.5) / 3 * vast;
        Pan2.ar(
            LFSaw.ar(freq * (1 + detune + voiceDrift), i * 0.3, 0.15),
            pan
        );
    });

    // Add sine undertone for depth
    voices = voices + SinOsc.ar(freq * 0.5, 0, 0.2);

    // Star shimmer - high frequency sparkle
    starShimmer = Dust2.ar(stars.linexp(0, 1, 10, 200)) * stars;
    starShimmer = BPF.ar(starShimmer, 8000, 0.5) * 2;
    starShimmer = Pan2.ar(starShimmer, LFNoise1.kr(3));

    // Mix voices with shimmer
    sig = voices + (starShimmer * 0.3);

    // Cold filter - high pass removes warmth
    coldFilter = cold.linexp(0, 1, 80, 400);
    sig = HPF.ar(sig, coldFilter);

    // Distance - gentle low pass + reduced presence
    sig = LPF.ar(sig, distance.linexp(0, 1, 12000, 4000));
    sig = sig * distance.linlin(0, 1, 1.0, 0.7);

    // Standard post-chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_fuego_celeste_stellar_void loaded".postln;
