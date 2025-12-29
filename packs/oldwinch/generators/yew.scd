SynthDef(\forge_oldwinch_yew, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var bow, twist, ancient, resin, hollow;
    var bowNoise, bowedSig, twistMod, hollowRes, friction;

    // Theme params
    bow = In.kr(customBus0);
    twist = In.kr(customBus1);
    ancient = In.kr(customBus2);
    resin = In.kr(customBus3);
    hollow = In.kr(customBus4);

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

    // Twist modulation - gnarled trunk
    twistMod = LFNoise2.kr(0.1 + (twist * 0.3)).range(0.96, 1.04);
    freq = freq * twistMod;

    // Bow friction noise
    friction = resin.linexp(0, 1, 0.3, 0.8);
    bowNoise = BPF.ar(PinkNoise.ar(0.5), freq * 3, 0.2) * 3;
    bowNoise = bowNoise * LFNoise2.kr(5 + (resin * 10)).range(friction, 1.0);
    bowNoise = bowNoise * bow;

    // Bowed string simulation - filtered sawtooth with resonance
    bowedSig = LFSaw.ar(freq, 0, 0.3 * bow);
    bowedSig = bowedSig + LFSaw.ar(freq * 1.001, 0.5, 0.25 * bow);
    bowedSig = bowedSig + (SinOsc.ar(freq, 0, 0.2));

    // Add harmonics
    bowedSig = bowedSig + SinOsc.ar(freq * 2, 0, 0.15 * (1 - ancient));
    bowedSig = bowedSig + SinOsc.ar(freq * 3, 0, 0.1 * (1 - ancient));
    bowedSig = bowedSig + SinOsc.ar(freq * 0.5, 0, 0.2 * ancient);

    // Resonant body - comb filter
    bowedSig = bowedSig + CombL.ar(bowedSig, 0.1, freq.reciprocal.clip(0.002, 0.1), 0.2 + (hollow * 0.4), 0.3);

    sig = bowedSig + (bowNoise * 0.4);

    // Hollow trunk resonance
    hollowRes = BPF.ar(sig, freq * 0.5, 0.2 + (hollow * 0.3)) * 3;
    sig = sig + (hollowRes * hollow);

    // Ancient darkness - low pass
    sig = LPF.ar(sig, ancient.linexp(0, 1, 6000, 1500));

    // Wood body
    sig = sig + BPF.ar(BrownNoise.ar(0.1), freq, 0.3) * 2;

    // Continuous bed
    sig = sig + LPF.ar(PinkNoise.ar(0.06), 300);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_oldwinch_yew loaded".postln;
