// Stone Arch - Ancient basalt formation with wind and erosion
// Physical modeling: resonant body excited by filtered noise

SynthDef(\forge_drangarnir_stone_arch, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var age, mass, wind, erosion, vibration;
    var exciter, body, windTone, texture;

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
    age = In.kr(customBus0);
    mass = In.kr(customBus1);
    wind = In.kr(customBus2);
    erosion = In.kr(customBus3);
    vibration = In.kr(customBus4);

    // Exciter: low rumble with erosion texture
    exciter = LPF.ar(PinkNoise.ar(0.3), freq * 2);
    exciter = exciter + (Dust.ar(erosion.linlin(0, 1, 5, 50)) * 0.1);

    // Main body: stacked comb filters for resonant stone
    body = Mix.fill(4, { |i|
        var delayTime = 1 / (freq * (1 + (i * 0.02 * mass)));
        var decayTime = mass.linlin(0, 1, 0.5, 4);
        CombL.ar(exciter, 0.1, delayTime, decayTime);
    }) * 0.3;

    // Age formants - shift character over millennia
    body = BPF.ar(body, freq * age.linlin(0, 1, 0.5, 2), 0.3) * 2;
    body = body + BPF.ar(body, freq * 2.5, 0.5);

    // Wind howling through the arch
    windTone = BPF.ar(
        WhiteNoise.ar(wind * 0.4),
        LFNoise1.kr(0.3).range(freq * 3, freq * 8),
        0.1
    );
    windTone = windTone * LFNoise2.kr(2).range(0.3, 1);

    // Erosion surface texture
    texture = HPF.ar(GrayNoise.ar(erosion * 0.15), 2000);

    // Seismic vibration
    body = body * (1 + (SinOsc.ar(LFNoise1.kr(0.1).range(1, 5)) * vibration * 0.1));

    // Combine
    sig = body + windTone + texture;

    // Add subtle sub harmonics for mass
    sig = sig + SinOsc.ar(freq * 0.5, 0, mass * 0.2);

    // Stereo spread
    sig = ~stereoSpread.(sig, 0.1, 0.3);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_drangarnir_stone_arch loaded".postln;
