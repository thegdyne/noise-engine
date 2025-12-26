SynthDef(\forge_seagrass_bay_gentle_giant, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var mass, grace, skin, breath, swim;
    var mainOsc, subOsc, breathMod, swimMod, skinNoise;

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
    mass = In.kr(customBus0);       // Size/weight
    grace = In.kr(customBus1);      // Smoothness
    skin = In.kr(customBus2);       // Texture
    breath = In.kr(customBus3);     // Breathing mod
    swim = In.kr(customBus4);       // Motion quality

    // Breathing modulation - slow amplitude swell
    breathMod = SinOsc.kr(breath.linexp(0, 1, 0.08, 0.3)).range(1 - (breath * 0.15), 1);

    // Swim modulation - gentle pitch drift
    swimMod = LFTri.kr(swim.linexp(0, 1, 0.05, 0.25)) * swim * 0.008;
    freq = freq * (1 + swimMod);

    // Main oscillator - triangle for smoothness, saw for body
    mainOsc = (VarSaw.ar(freq, 0, grace.linlin(0, 1, 0.5, 0.1)) * 0.6) +
              (LFTri.ar(freq) * grace * 0.4);

    // Sub oscillator for mass
    subOsc = SinOsc.ar(freq * 0.5) * mass * 0.5;

    // Octave up for presence
    sig = mainOsc + subOsc + (LFTri.ar(freq * 2) * (1 - mass) * 0.15);

    // Skin texture - subtle noise
    skinNoise = LPF.ar(PinkNoise.ar, freq * 3) * skin * 0.08;
    sig = sig + skinNoise;

    // Apply breathing
    sig = sig * breathMod;

    // Grace = smoothing/filtering
    sig = LPF.ar(sig, grace.linexp(0, 1, 3000, 12000));

    // Warm stereo spread
    sig = ~stereoSpread.(sig, 0.15, 0.35);

    // Standard output chain
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_seagrass_bay_gentle_giant loaded".postln;
