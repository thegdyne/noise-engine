SynthDef(\forge_overgrown_broken_sky, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                         filterTypeBus, envEnabledBus, envSourceBus=0,
                                         clockRateBus, clockTrigBus,
                                         midiTrigBus=0, slotIndex=0,
                                         customBus0, customBus1, customBus2, customBus3, customBus4,
                                         portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var shatter, light, prism, dustAmt, hope;
    var beams, glass, sparkle, dustMotes, warmth;

    // Theme params
    shatter = In.kr(customBus0);
    light = In.kr(customBus1);
    prism = In.kr(customBus2);
    dustAmt = In.kr(customBus3);
    hope = In.kr(customBus4);

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

    // Light beams - pure sines
    beams = SinOsc.ar(freq) * light * 0.3;
    beams = beams + (SinOsc.ar(freq * 2) * light * 0.15);
    beams = beams + (SinOsc.ar(freq * 3) * light * 0.08);

    // Prism spread - detuned harmonics
    glass = SinOsc.ar(freq * (1 + (prism * 0.02))) * 0.2;
    glass = glass + (SinOsc.ar(freq * (2 - (prism * 0.03))) * 0.1);
    glass = glass + (SinOsc.ar(freq * (4 + (prism * 0.05))) * 0.06);
    glass = glass + (SinOsc.ar(freq * (5 - (prism * 0.04))) * 0.04);

    // Shatter - randomized high partials
    sparkle = SinOsc.ar(freq * 6 * LFNoise1.kr(shatter.linexp(0, 1, 0.2, 2)).range(0.95, 1.05)) * shatter * 0.08;
    sparkle = sparkle + (SinOsc.ar(freq * 8 * LFNoise1.kr(shatter.linexp(0, 1, 0.3, 3)).range(0.94, 1.06)) * shatter * 0.05);
    sparkle = sparkle + (SinOsc.ar(freq * 10 * LFNoise1.kr(shatter.linexp(0, 1, 0.4, 4)).range(0.93, 1.07)) * shatter * 0.03);

    // Dust motes - tiny grains in the light
    dustMotes = Dust.ar(dustAmt.linexp(0, 1, 5, 60)) * 0.05 * dustAmt;
    dustMotes = Ringz.ar(dustMotes, freq * [4, 5], 0.02);

    // Warmth/hope - soft low sine
    warmth = SinOsc.ar(freq * 0.5) * hope * 0.2;
    warmth = warmth + (SinOsc.ar(freq * LFNoise1.kr(0.1).range(0.99, 1.01)) * hope * 0.15);

    // Combine with stereo
    sig = beams + glass + sparkle + warmth;
    sig = [sig + dustMotes[0], sig + dustMotes[1]];

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_overgrown_broken_sky loaded".postln;
