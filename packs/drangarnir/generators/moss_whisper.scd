// Moss Whisper - The soft organic layer on weathered rocks
// Gentle granular texture with breathing movement

SynthDef(\forge_drangarnir_moss_whisper, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                            filterTypeBus, envEnabledBus, envSourceBus=0,
                                            clockRateBus, clockTrigBus,
                                            midiTrigBus=0, slotIndex=0,
                                            customBus0, customBus1, customBus2, customBus3, customBus4,
                                            portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var growth, wetness, breath, texture, softness;
    var mossBase, waterDrops, breathMod, textureDust;
    var breathRate;

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
    growth = In.kr(customBus0);
    wetness = In.kr(customBus1);
    breath = In.kr(customBus2);
    texture = In.kr(customBus3);
    softness = In.kr(customBus4);

    breathRate = breath.linexp(0, 1, 0.1, 0.5);

    // Moss base - very soft filtered noise
    mossBase = PinkNoise.ar(growth * 0.3);
    mossBase = LPF.ar(mossBase, freq * softness.linlin(0, 1, 2, 0.5));
    mossBase = mossBase * LFNoise2.kr(breathRate).range(0.7, 1);

    // Breathing modulation
    breathMod = SinOsc.kr(breathRate).range(0.8, 1.2);

    // Water droplets in moss
    waterDrops = Dust.ar(wetness.linlin(0, 1, 5, 50)) * 0.1;
    waterDrops = Ringz.ar(waterDrops, freq * 3, wetness * 0.1);
    waterDrops = LPF.ar(waterDrops, freq * 4);

    // Fine texture dust
    textureDust = Dust2.ar(texture.linlin(0, 1, 100, 1000)) * 0.05;
    textureDust = BPF.ar(textureDust, freq * 2, 0.5);

    // Combine with breathing
    sig = (mossBase * breathMod) + waterDrops + textureDust;

    // Add subtle harmonic for pitched element
    sig = sig + (SinOsc.ar(freq * LFNoise1.kr(0.2).range(0.99, 1.01), 0, growth * 0.1) * breathMod);

    // Heavy softening filter
    sig = LPF.ar(sig, freq * softness.linlin(0, 1, 4, 1));

    // Gentle stereo
    sig = ~stereoSpread.(sig, breathRate * 0.5, 0.3);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_drangarnir_moss_whisper loaded".postln;
