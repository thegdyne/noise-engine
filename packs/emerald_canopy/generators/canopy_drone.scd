// Canopy Drone - Dense layered saws like overlapping leaves
// Role: bed | Family: subtractive

SynthDef(\forge_emerald_canopy_canopy_drone, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                                 filterTypeBus, envEnabledBus, envSourceBus=0,
                                                 clockRateBus, clockTrigBus,
                                                 midiTrigBus=0, slotIndex=0,
                                                 customBus0, customBus1, customBus2, customBus3, customBus4,
                                                 portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var vegetation, sunlight, sway, depth, mist;
    var saws, numLayers, detune, swayLfo, mistNoise, pan;

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
    vegetation = In.kr(customBus0);  // Density of layers
    sunlight = In.kr(customBus1);    // Brightness
    sway = In.kr(customBus2);        // Pitch drift
    depth = In.kr(customBus3);       // Stereo spread
    mist = In.kr(customBus4);        // Noise layer

    // Sway LFO - slow organic drift
    swayLfo = LFNoise2.kr(0.1 + (sway * 0.3)) * (sway * 0.02);

    // Create layered saws with vegetation-based detuning
    numLayers = 7;
    detune = vegetation.linexp(0, 1, 0.001, 0.015);  // Detune spread
    saws = Array.fill(numLayers, { |i|
        var ratio = (i - 3) * detune + 1;  // Centered detune
        var layerFreq = freq * ratio * (1 + swayLfo);
        var layerPan = (i - 3) / 3 * depth;  // Spread across stereo
        Pan2.ar(Saw.ar(layerFreq), layerPan)
    }).sum / numLayers;

    // Sunlight - additional brightness control via separate filter
    saws = LPF.ar(saws, sunlight.linexp(0, 1, 400, 8000));

    // Mist layer - filtered noise
    mistNoise = LPF.ar(PinkNoise.ar(0.3), 2000) * mist;
    mistNoise = Pan2.ar(mistNoise, LFNoise2.kr(0.2) * depth);

    sig = saws + mistNoise;

    // Output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;

"  * forge_emerald_canopy_canopy_drone loaded".postln;
