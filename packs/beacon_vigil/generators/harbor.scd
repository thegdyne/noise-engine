// HARBOR - Distant foghorn arrival drone
// Source: Ship horns, harbor atmosphere, water acoustics
// Role: Bed - deep foundation with distant character

SynthDef(\forge_beacon_vigil_harbor, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|
    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var dist, horn, wave, deep, mist;
    var foghorn, sub, haze, waveMod, distance;

    // Custom params
    dist = In.kr(customBus0);  // Distance/reverb
    horn = In.kr(customBus1);  // Foghorn FM depth
    wave = In.kr(customBus2);  // Water movement
    deep = In.kr(customBus3);  // Sub bass
    mist = In.kr(customBus4);  // High haze

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

    // === DSP: Harbor Soundscape ===

    // Water movement modulation - slow undulation
    waveMod = SinOsc.kr(wave.linexp(0, 1, 0.03, 0.3)).range(0.97, 1.03);
    waveMod = waveMod * LFNoise2.kr(wave.linexp(0, 1, 0.1, 0.5)).range(0.98, 1.02);

    // Foghorn: FM synthesis with characteristic mournful quality
    foghorn = SinOsc.ar(
        freq * waveMod,
        SinOsc.ar(freq * 0.5 * waveMod) * horn.linlin(0, 1, 0.5, 3)
    );
    // Add second partial for body
    foghorn = foghorn + (SinOsc.ar(freq * 2 * waveMod) * 0.3);
    // Slight detuned layer for thickness
    foghorn = foghorn + (SinOsc.ar(freq * 1.003 * waveMod) * 0.4);

    // Deep sub bass - pure sine with gentle movement
    sub = SinOsc.ar(freq * 0.5 * waveMod) * deep.linlin(0, 1, 0.2, 0.8);
    sub = sub + (SinOsc.ar(freq * 0.25) * deep * 0.3);

    // Mist: filtered noise for atmospheric haze
    haze = PinkNoise.ar * mist * 0.1;
    haze = BPF.ar(haze, freq * 4, 0.5);
    haze = haze + (BPF.ar(PinkNoise.ar, freq * 8, 0.3) * mist * 0.05);

    // Combine
    sig = (foghorn * 0.5) + sub + haze;

    // Distance processing - allpass diffusion
    distance = sig;
    4.do { |i|
        distance = AllpassC.ar(
            distance,
            0.1,
            dist.linlin(0, 1, 0.01, 0.07) * (i + 1) / 4,
            dist.linlin(0, 1, 0.5, 3)
        );
    };
    sig = (sig * (1 - (dist * 0.5))) + (distance * dist * 0.7);

    // Gentle LP for distance
    sig = LPF.ar(sig, dist.linexp(0, 1, 15000, 4000));

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_beacon_vigil_harbor loaded".postln;
