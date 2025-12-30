SynthDef(\forge_wicker_sun, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var golden, heat, zenith, haze, scorch;
    var goldenMod, heatMod, zenithMod, hazeMod, scorchMod;
    var warmth, shimmer, oppression, pulse;

    // Read custom params
    golden = In.kr(customBus0);    // P1: Golden intensity - scaled by zenith
    heat = In.kr(customBus1);      // P2: Heat intensity - curve set by scorch
    zenith = In.kr(customBus2);    // P3: Zenith height - modulates golden AND haze
    haze = In.kr(customBus3);      // P4: Haze thickness - feeds back to heat
    scorch = In.kr(customBus4);    // P5: Scorch severity - master oppression axis

    // BUTTERFLY EFFECT: Cross-modulation network
    goldenMod = golden * (0.35 + (zenith * 0.65));
    heatMod = heat.linexp(0, 1, 0.2, 4) * (1 + (haze * scorch * 1.4));
    zenithMod = zenith * (1 + (scorch.squared * 0.55));
    hazeMod = haze * (0.4 + (golden * heat * 0.6));
    scorchMod = scorch * (1 + (zenith * haze * 0.45));

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
    ampVal = In.kr(~params[\amplitude]);

    // DSP: Oppressive summer sun
    
    // Warmth: rich filtered noise bed
    warmth = PinkNoise.ar(0.3) + (BrownNoise.ar(0.2) * goldenMod);
    warmth = RLPF.ar(warmth, freq * heatMod.linlin(0, 1, 1, 4), 0.3 + (hazeMod * 0.3));
    warmth = warmth * goldenMod.linlin(0, 1, 0.3, 0.8);
    
    // Shimmer: high frequency heat distortion
    shimmer = WhiteNoise.ar(0.1) * Resonz.ar(
        PinkNoise.ar(0.5),
        freq * zenithMod.linlin(0, 1, 4, 12) * [1, 1.02, 1.05],
        0.05
    ).sum;
    shimmer = shimmer * zenithMod.linlin(0, 1, 0.1, 0.5);
    shimmer = shimmer * (1 + (SinOsc.kr(heatMod * 0.5) * 0.2));
    
    // Oppression: slow heavy modulation
    oppression = SinOsc.ar(freq * [0.5, 1, 1.5], 0, [0.2, 0.15, 0.08]).sum;
    oppression = oppression * (1 + (SinOsc.kr(scorchMod * 0.1) * hazeMod * 0.4));
    oppression = oppression + (LFTri.ar(freq * 2) * 0.05 * scorchMod);
    
    // Pulse: heartbeat of the unrelenting
    pulse = SinOsc.ar(freq * 0.25, 0, 0.1);
    pulse = pulse * (1 + (SinOsc.kr(0.3 * scorchMod) * 0.5));
    pulse = pulse * scorchMod.linlin(0, 1, 0.2, 1);
    
    // Mix based on scorch (oppression axis)
    sig = warmth + shimmer + (oppression * (1 - (scorchMod * 0.3))) + pulse;
    
    // Heat haze wavering
    sig = sig + (DelayC.ar(sig, 0.02, SinOsc.kr(hazeMod * 2).range(0.005, 0.015)) * hazeMod * 0.2);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_wicker_sun loaded".postln;
