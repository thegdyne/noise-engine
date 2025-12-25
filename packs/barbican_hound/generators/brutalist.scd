// BRUTALIST - Dark filtered noise foundation like grey concrete
// Family: texture (noise_drone)
// Role: bed

SynthDef(\forge_barbican_hound_brutalist, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                             filterTypeBus, envEnabledBus, envSourceBus=0,
                                             clockRateBus, clockTrigBus,
                                             midiTrigBus=0, slotIndex=0,
                                             customBus0, customBus1, customBus2, customBus3, customBus4,
                                             portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var mass, grit, voidAmt, damp, span;
    var noise, lowDrone, midTex, hiGrit, resonator;

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
    mass = In.kr(customBus0);      // Weight/depth
    grit = In.kr(customBus1);      // Texture roughness
    voidAmt = In.kr(customBus2);   // Hollow resonance
    damp = In.kr(customBus3);      // Wetness filtering
    span = In.kr(customBus4);      // Stereo width

    // Low foundation - weighted by mass (reduced gain)
    lowDrone = LPF.ar(BrownNoise.ar(0.3), freq * 2) * mass.linexp(0, 1, 0.2, 0.5);

    // Mid texture layer
    midTex = BPF.ar(PinkNoise.ar(0.3), freq * 4, 0.3) * 0.2;

    // High grit layer
    hiGrit = HPF.ar(WhiteNoise.ar(0.2), 2000) * grit * 0.15;

    // Combine layers
    noise = lowDrone + midTex + hiGrit;

    // Void resonator - hollow concrete (reduced gain)
    resonator = Ringz.ar(noise * 0.05, [freq * 0.5, freq * 0.75, freq], voidAmt.linexp(0, 1, 0.1, 1.5)) * voidAmt * 0.5;
    noise = noise + resonator.sum;

    // Damp filter (wetness)
    noise = LPF.ar(noise, damp.linexp(0, 1, 8000, 1500));

    // Stereo spread
    sig = Pan2.ar(noise, LFNoise1.kr(0.1) * span);

    // Post-chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_barbican_hound_brutalist loaded".postln;
