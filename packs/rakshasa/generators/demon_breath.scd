// Demon Breath -- Low exhale with formant resonances and growl
// Role: bed | Family: texture

SynthDef(\forge_rakshasa_demon_breath, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var heat, foul, hiss, depth, growl;
    var breath, lowRumble, hissLayer, formants, growlMod;
    var formantFreqs, formantAmps;

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
    heat = In.kr(customBus0).linexp(0, 1, 200, 4000);       // Spectral center
    foul = In.kr(customBus1).linlin(0, 1, 1, 20);           // Distortion amount
    hiss = In.kr(customBus2).linlin(0, 1, 0, 0.4);          // HF noise mix
    depth = In.kr(customBus3).linlin(0, 1, 0, 0.6);         // Sub rumble mix
    growl = In.kr(customBus4).linexp(0, 1, 0.1, 15);        // Growl modulation rate

    // Growl modulation
    growlMod = LFNoise1.kr(growl).range(0.7, 1.3);

    // Low rumble from the depths
    lowRumble = LPF.ar(BrownNoise.ar, freq * 0.5 * growlMod) * depth;
    lowRumble = lowRumble + (SinOsc.ar(freq * 0.5 * growlMod) * depth * 0.3);

    // Main breath noise
    breath = PinkNoise.ar;

    // Formant resonances -- demon vocal tract
    formantFreqs = [heat * 0.8, heat * 1.2, heat * 2.5] * growlMod;
    formants = Mix.ar(
        formantFreqs.collect({ |f, i|
            BPF.ar(breath, f.clip(80, 12000), 0.15) * (1 / (i + 1))
        })
    );

    // Add distortion for foulness
    formants = (formants * foul).tanh / foul.sqrt;

    // High frequency hiss
    hissLayer = HPF.ar(WhiteNoise.ar, 3000) * hiss;
    hissLayer = hissLayer * LFNoise2.kr(growl * 0.5).range(0.5, 1);

    // Combine all elements
    sig = (formants * 0.5) + lowRumble + hissLayer;

    // Stereo with slight movement
    sig = Pan2.ar(sig, LFNoise2.kr(0.3).range(-0.3, 0.3));

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp,
                   clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_rakshasa_demon_breath loaded".postln;
