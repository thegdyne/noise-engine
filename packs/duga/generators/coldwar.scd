SynthDef(\forge_duga_coldwar, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var tens, throb, feed, dark, dread;
    var baseDrone, throbMod, darkSig, dreadMod, feedAmt;

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
    tens = In.kr(customBus0);
    throb = In.kr(customBus1);
    feed = In.kr(customBus2);
    dark = In.kr(customBus3);
    dread = In.kr(customBus4);

    // Throbbing modulation
    throbMod = SinOsc.kr(throb.linexp(0, 1, 0.2, 3)).range(0.6, 1);

    // Dread modulation - slow unease
    dreadMod = LFNoise2.kr(0.1).range(1 - (dread * 0.1), 1 + (dread * 0.1));

    // Feedback amount based on tension
    feedAmt = feed.linlin(0, 1, 0.2, 0.85) * tens.linlin(0, 1, 0.8, 1.2);
    feedAmt = feedAmt.clip(0, 0.95);

    // Main feedback FM drone
    baseDrone = SinOscFB.ar(freq * 0.5 * dreadMod, feedAmt);
    baseDrone = baseDrone + SinOscFB.ar(freq * dreadMod, feedAmt * 0.7) * 0.5;
    baseDrone = baseDrone * throbMod;

    // Dark undertones - sub bass
    darkSig = SinOsc.ar(freq * 0.25 * dreadMod);
    darkSig = darkSig + SinOsc.ar(freq * 0.125, 0, 0.5);
    darkSig = darkSig * dark * 0.4;

    // Tension overlay - dissonant high partials
    sig = baseDrone * 0.4;
    sig = sig + (SinOscFB.ar(freq * 2.02 * dreadMod, feedAmt * 0.5) * tens * 0.15);
    sig = sig + (SinOscFB.ar(freq * 3.01, feedAmt * 0.4) * tens * 0.1);

    sig = sig + darkSig;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_duga_coldwar loaded".postln;
