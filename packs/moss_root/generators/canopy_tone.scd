SynthDef(\forge_moss_root_canopy_tone, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var glow, flutter, gaps, hue, air;
    var fmCarrier, fmMod, tremolo, gapMod, airNoise, warmth;

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
    glow = In.kr(customBus0);
    flutter = In.kr(customBus1);
    gaps = In.kr(customBus2);
    hue = In.kr(customBus3);
    air = In.kr(customBus4);

    // FM synthesis for shimmering tones
    fmMod = SinOsc.ar(freq * 2) * glow.linlin(0, 1, 0.5, 3);
    fmCarrier = SinOsc.ar(freq + fmMod) * 0.5;

    // Add harmonics via additional FM layer
    fmCarrier = fmCarrier + (SinOsc.ar(freq * 1.5 + (SinOsc.ar(freq * 3) * glow)) * 0.2 * glow);

    // Flutter: tremolo from leaves
    tremolo = LFTri.kr(flutter.linexp(0, 1, 2, 12)).range(
        1 - (flutter * 0.4),
        1
    );

    // Gaps: irregular amplitude modulation
    gapMod = LFNoise1.kr(gaps.linexp(0, 1, 0.5, 4)).range(
        1 - gaps,
        1
    );

    sig = fmCarrier * tremolo * gapMod;

    // Air: high frequency breath
    airNoise = HPF.ar(PinkNoise.ar, 6000) * air * 0.15;
    airNoise = airNoise * LFNoise2.kr(3).range(0.5, 1);
    sig = sig + airNoise;

    // Hue: warmth filtering (low hue = cooler, high = warmer golden)
    warmth = hue.linexp(0, 1, 6000, 2500);
    sig = LPF.ar(sig, warmth);
    // Add subtle warmth harmonics
    sig = sig + (SinOsc.ar(freq * 0.5) * hue * 0.1);

    // Gentle stereo spread
    sig = ~stereoSpread.(sig, flutter.linlin(0, 1, 0.1, 0.4), 0.4);

    // MANDATORY output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_moss_root_canopy_tone loaded".postln;
