// Leaf Rustle - Filtered noise like wind through leaves
// Role: motion | Family: texture/noise

SynthDef(\forge_emerald_canopy_leaf_rustle, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                               filterTypeBus, envEnabledBus, envSourceBus=0,
                                               clockRateBus, clockTrigBus,
                                               midiTrigBus=0, slotIndex=0,
                                               customBus0, customBus1, customBus2, customBus3, customBus4,
                                               portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var rustle, wind, dryness, layers, swirl;
    var windLfo, lowRustle, midRustle, highRustle, crackle, swirlLfo;

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

    // Theme params
    rustle = In.kr(customBus0);   // Intensity
    wind = In.kr(customBus1);     // Modulation rate
    dryness = In.kr(customBus2);  // High freq crackle
    layers = In.kr(customBus3);   // Band layering
    swirl = In.kr(customBus4);    // Stereo movement

    // Wind LFO - organic gusting
    windLfo = LFNoise2.kr(wind.linexp(0, 1, 0.2, 3));
    windLfo = windLfo.range(0.3, 1);

    // Low rustle - body of the sound
    lowRustle = BPF.ar(
        BrownNoise.ar,
        freq * 0.5 * (1 + (windLfo * 0.2)),
        0.5
    ) * 0.6;

    // Mid rustle - main texture
    midRustle = BPF.ar(
        PinkNoise.ar,
        freq * (1 + (windLfo * 0.3)),
        0.3
    );

    // High rustle - shimmer
    highRustle = BPF.ar(
        WhiteNoise.ar,
        freq * 3 * (1 + (windLfo * 0.1)),
        0.4
    ) * layers * 0.4;

    // Crackle - dry leaf sounds
    crackle = Dust2.ar(dryness.linexp(0, 1, 5, 200)) * dryness * 0.3;
    crackle = HPF.ar(crackle, 2000);

    // Mix layers based on intensity
    sig = (lowRustle * rustle) +
          (midRustle * rustle) +
          (highRustle * rustle * layers) +
          crackle;

    // Apply wind modulation to amplitude
    sig = sig * windLfo;

    // Swirl - stereo movement
    swirlLfo = SinOsc.kr(wind.linexp(0, 1, 0.1, 1)) * swirl;
    sig = Balance2.ar(sig, DelayN.ar(sig, 0.01, 0.003), swirlLfo);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_emerald_canopy_leaf_rustle loaded".postln;
