// CARTGLOW — Cartilage glow modal resonator
// Bell-like resonances of ossifying tissue, yellow/gold accents

SynthDef(\forge_nerve_glow_cartglow, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                        filterTypeBus, envEnabledBus, envSourceBus=0,
                                        clockRateBus, clockTrigBus,
                                        midiTrigBus=0, slotIndex=0,
                                        customBus0, customBus1, customBus2, customBus3, customBus4,
                                        portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var ossify, growth, luminance, dens, spark;
    var exciter, modes, modeFreqs, modeDecays;

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

    // Custom params
    ossify = In.kr(customBus0).linexp(0, 1, 0.3, 4.0);     // Ring time
    growth = In.kr(customBus1).linlin(0, 1, 1.0, 1.15);    // Inharmonic stretch
    luminance = In.kr(customBus2).linlin(0, 1, 0.3, 1.0);  // Brightness
    dens = In.kr(customBus3).linlin(0, 1, 2, 8);           // Mode count
    spark = In.kr(customBus4).linexp(0, 1, 2000, 12000);   // Exciter brightness

    // Exciter — bright impulse filtered by spark
    exciter = Impulse.ar(0) + Dust.ar(3);
    exciter = exciter * WhiteNoise.ar(1);
    exciter = LPF.ar(exciter, spark);

    // Modal frequencies with growth plate inharmonicity
    modeFreqs = [1, 2.1, 3.3, 4.7, 5.9, 7.2, 8.8, 10.5] * freq;
    modeFreqs = modeFreqs * (growth ** (0..7));

    // Variable decay per mode
    modeDecays = ossify * [1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3];

    // Sum of resonant modes
    modes = Mix.fill(8, { |i|
        var mAmp = (dens - i).clip(0, 1) * (0.6 ** i) * luminance;
        Ringz.ar(exciter, modeFreqs[i].clip(20, 16000), modeDecays[i]) * mAmp
    });

    sig = modes * 0.15;

    // Add subtle shimmer
    sig = sig + (sig * SinOsc.kr(4, 0, 0.1));

    // Stereo spread
    sig = ~stereoSpread.(sig, 0.5, 0.3);

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_nerve_glow_cartglow loaded".postln;
