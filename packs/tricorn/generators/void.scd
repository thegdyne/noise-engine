SynthDef(\forge_tricorn_void, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, envSource, clockRate, portamento;
    var hollow, draft, empty, distant, abandon;
    var wind, resonance, draftMod, space;

    // Theme params
    hollow = In.kr(customBus0);
    draft = In.kr(customBus1);
    empty = In.kr(customBus2);
    distant = In.kr(customBus3);
    abandon = In.kr(customBus4);

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

    // Wind source - layered noise
    wind = PinkNoise.ar(0.5) + (BrownNoise.ar(0.3) * (1 - abandon));
    wind = wind + (WhiteNoise.ar(0.1) * abandon);

    // Draft modulation - slow undulation
    draftMod = LFNoise2.kr(0.2 + (draft * 0.5)).range(0.5, 1.0);
    wind = wind * draftMod;

    // Hollow resonance - tuned bandpass
    resonance = BPF.ar(wind, freq, hollow.linexp(0, 1, 0.5, 0.05)) * 4;
    resonance = resonance + BPF.ar(wind, freq * 1.5, hollow.linexp(0, 1, 0.6, 0.08)) * 2;
    resonance = resonance + BPF.ar(wind, freq * 0.5, hollow.linexp(0, 1, 0.7, 0.1)) * 3;

    sig = (wind * 0.3 * (1 - hollow)) + (resonance * hollow);

    // Empty space - allpass reverb character
    space = sig;
    space = AllpassC.ar(space, 0.3, empty.linlin(0, 1, 0.05, 0.2), empty * 3);
    space = AllpassC.ar(space, 0.3, empty.linlin(0, 1, 0.08, 0.25), empty * 2.5);
    space = AllpassC.ar(space, 0.3, empty.linlin(0, 1, 0.03, 0.15), empty * 2);

    sig = (sig * (1 - (empty * 0.5))) + (space * empty * 0.7);

    // Distant echoes
    sig = sig + (CombL.ar(sig, 0.5, distant.linlin(0, 1, 0.1, 0.4), distant * 4) * distant * 0.4);

    // Abandonment - spectral thinning via additional filtering
    sig = RHPF.ar(sig, abandon.linexp(0, 1, 50, 400), 0.7);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, 0.2, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_tricorn_void loaded".postln;
