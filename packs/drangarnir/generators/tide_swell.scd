// Tide Swell - The rising and falling rhythm of ocean waves
// Filtered noise with breathing amplitude and filter movement

SynthDef(\forge_drangarnir_tide_swell, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var swell, period, crest, trough, drag;
    var waveOsc, base, crestNoise, troughSub, dragMod;
    var swellRate, swellEnv;

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

    // Theme params
    swell = In.kr(customBus0);
    period = In.kr(customBus1);
    crest = In.kr(customBus2);
    trough = In.kr(customBus3);
    drag = In.kr(customBus4);

    // Wave period oscillator - asymmetric like real waves
    swellRate = period.linexp(0, 1, 0.05, 0.5);
    waveOsc = LFTri.kr(swellRate);
    // Asymmetric: quick rise to crest, slow fall to trough
    waveOsc = waveOsc.pow(1 + (drag * 0.5));
    swellEnv = waveOsc.range(trough.linlin(0, 1, 0.1, 0.4), swell.linlin(0, 1, 0.5, 1));

    // Base wave sound - filtered noise
    base = PinkNoise.ar(0.5) + BrownNoise.ar(0.3);
    base = LPF.ar(base, freq * 2);

    // Crest brightness - high frequency content at peak
    crestNoise = HPF.ar(WhiteNoise.ar(crest * 0.3), 3000);
    crestNoise = crestNoise * waveOsc.range(0, 1);

    // Trough darkness - low sub rumble in the trough
    troughSub = SinOsc.ar(freq * 0.25, 0, trough * 0.4);
    troughSub = troughSub * (1 - waveOsc.range(0, 1));

    // Undertow drag - backward motion
    dragMod = LFSaw.kr(swellRate * 0.5, 1).range(0, drag);
    base = base * (1 - (dragMod * 0.3));

    // Filter movement follows wave
    base = RLPF.ar(base, 
        waveOsc.range(freq * 0.5, freq * (2 + (crest * 2))),
        0.3
    );

    // Combine with swell envelope
    sig = (base + crestNoise + troughSub) * swellEnv;

    // Add subtle pitch drift for organic feel
    sig = sig * SinOsc.ar(freq * LFNoise1.kr(0.2).range(0.99, 1.01), 0, 0.1).abs;

    // Stereo spread
    sig = ~stereoSpread.(sig, swellRate * 2, 0.5);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_drangarnir_tide_swell loaded".postln;
