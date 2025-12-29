SynthDef(\forge_pripyat_music, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var brok, pipe, whee, rust, memo;
    var pipes, wheezeSig, memoSig, detuneAmt;

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

    // Custom params
    brok = In.kr(customBus0);
    pipe = In.kr(customBus1);
    whee = In.kr(customBus2);
    rust = In.kr(customBus3);
    memo = In.kr(customBus4);

    // Detune amount based on broken-ness
    detuneAmt = brok.linlin(0, 1, 0.001, 0.05);

    // Organ pipes - additive synthesis with detuning (no var inside block)
    pipes = Mix.fill(8, { |i|
        SinOsc.ar(
            freq * (i + 1) * LFNoise2.kr(0.1 + (i * 0.02)).range(1 - detuneAmt, 1 + detuneAmt),
            0,
            (1 / (i + 1))
            * (LFNoise2.kr(0.05 + (i * 0.01)).range(0, 1) < pipe).asInteger
            * ((1 - rust).pow(i * 0.3))
            * LFNoise2.kr(0.3 + (i * 0.1)).range(0.8, 1)
        );
    });

    pipes = pipes * 0.4;

    // Air wheeze - breathy leaking pipes
    wheezeSig = BPF.ar(PinkNoise.ar(1), freq * LFNoise2.kr(0.5).range(0.5, 2), 0.3);
    wheezeSig = wheezeSig * LFNoise2.kr(2).range(0, 1);
    wheezeSig = wheezeSig * whee * 0.5;

    // Melody fragments - occasional pitch shifts suggesting melody
    memoSig = SinOsc.ar(freq * Select.kr(LFNoise0.kr(memo.linexp(0, 1, 0.1, 1)).range(0, 5).round, [1, 1.25, 1.5, 1.33, 2]));
    memoSig = memoSig * LFPulse.kr(memo.linexp(0, 1, 0.1, 0.5), 0, 0.3).lag(0.1);
    memoSig = memoSig * memo * 0.3;

    // Mix
    sig = pipes + wheezeSig + memoSig;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_pripyat_music loaded".postln;
