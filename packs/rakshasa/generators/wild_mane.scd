// Wild Mane -- Chaotic hair texture with granular noise
// Role: motion | Family: texture

SynthDef(\forge_rakshasa_wild_mane, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                       filterTypeBus, envEnabledBus, envSourceBus=0,
                                       clockRateBus, clockTrigBus,
                                       midiTrigBus=0, slotIndex=0,
                                       customBus0, customBus1, customBus2, customBus3, customBus4,
                                       portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var wild, frizz, tangle, whip, static;
    var strands, crackle, chaos, tangled, layers;
    var whipRate, chaosLFO, panMod;

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

    // Custom parameters
    wild = In.kr(customBus0).linlin(0, 1, 0.1, 1);         // Chaos amount
    frizz = In.kr(customBus1).linexp(0, 1, 10, 200);       // Grain density
    tangle = In.kr(customBus2).linlin(0, 1, 1, 5);         // Number of layers
    whip = In.kr(customBus3).linexp(0, 1, 0.5, 30);        // Movement rate
    static = In.kr(customBus4).linlin(0, 1, 0, 0.5);       // HF crackle mix

    // Whipping movement
    whipRate = whip;
    chaosLFO = LFNoise2.kr(whipRate) * wild;

    // Hair strand layers -- filtered noise bursts
    strands = Dust.ar(frizz) * WhiteNoise.ar;
    strands = RLPF.ar(strands, freq * (1 + (chaosLFO * 2)).clip(0.5, 4), 0.3);

    // Tangled complexity -- multiple detuned layers
    layers = Mix.fill(tangle.round, { |i|
        var detune, rate, strand;
        detune = LFNoise1.kr(whipRate * 0.3).range(0.8, 1.2);
        rate = frizz * LFNoise0.kr(2).range(0.5, 1.5);
        strand = Dust.ar(rate) * BrownNoise.ar;
        RLPF.ar(strand, freq * detune * (1 + (i * 0.2)), 0.4 + (i * 0.1));
    }) / tangle.max(1);

    // High frequency static/crackle
    crackle = Dust2.ar(frizz * 3) * 0.3;
    crackle = HPF.ar(crackle, 4000);

    // Mix all elements
    sig = (strands * 0.5) + (layers * 0.4) + (crackle * static);

    // Wild stereo movement
    panMod = LFNoise2.kr(whipRate * 0.7) * wild;
    sig = Pan2.ar(sig, panMod);

    // Output chain
    sig = sig * 4;  // gain boost
    sig = sig * 8;
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp,
                   clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_rakshasa_wild_mane loaded".postln;
