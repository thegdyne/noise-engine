SynthDef(\forge_backyard_lamb, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var bleat, run, hoof, wool, play;
    var bleatVoice, hoofSteps, woolRustle, breathNoise;
    var formantFreqs, formantAmps, bleatEnv, bleatTrig;

    // Theme params
    bleat = In.kr(customBus0);
    run = In.kr(customBus1);
    hoof = In.kr(customBus2);
    wool = In.kr(customBus3);
    play = In.kr(customBus4);

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
    ampVal = In.kr(~params[\amplitude]);

    // Bleat trigger
    bleatTrig = Dust.kr(play.linexp(0, 1, 0.3, 2));
    bleatEnv = Decay2.kr(bleatTrig, 0.05, 0.4);

    // Bleat voice - formant filtered oscillator
    bleatVoice = Saw.ar(freq * bleat.linlin(0, 1, 0.8, 1.3) * LFNoise1.kr(8).range(0.97, 1.03));
    bleatVoice = bleatVoice + Pulse.ar(freq * 1.01, 0.3, 0.3);

    // Formant filtering for "baa" sound - emphasize vowel formants
    formantFreqs = [700, 1200, 2400] * bleat.linlin(0, 1, 0.9, 1.2);
    formantAmps = [1, 0.7, 0.4];

    bleatVoice = Mix.fill(3, { |i|
        Resonz.ar(bleatVoice, formantFreqs[i], 0.15) * formantAmps[i] * 4
    });

    // Apply bleat envelope
    bleatVoice = bleatVoice * bleatEnv * 0.3;

    // Hoof steps on grass - soft thuds
    hoofSteps = Dust.ar(run.linexp(0, 1, 1, 12) * hoof);
    hoofSteps = BrownNoise.ar(1) * Decay.ar(hoofSteps, 0.04);
    hoofSteps = LPF.ar(hoofSteps, 300);
    hoofSteps = hoofSteps * hoof * 0.4;

    // Wool rustle - filtered noise texture
    woolRustle = PinkNoise.ar(0.2);
    woolRustle = BPF.ar(woolRustle, 2000, 0.8);
    woolRustle = woolRustle * LFNoise1.kr(run.linlin(0, 1, 1, 6)).range(0.2, 1);
    woolRustle = woolRustle * wool * run * 0.3;

    // Breath noise - adds life
    breathNoise = PinkNoise.ar(0.08) * bleatEnv;
    breathNoise = HPF.ar(breathNoise, 1500);

    // Mix all components
    sig = bleatVoice + hoofSteps + woolRustle + breathNoise;

    // Continuous bed for drone mode - grass/field ambience
    sig = sig + (BrownNoise.ar(0.06) + PinkNoise.ar(0.04));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_backyard_lamb loaded".postln;
