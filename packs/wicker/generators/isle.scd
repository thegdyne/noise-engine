SynthDef(\forge_wicker_isle, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var wind, shore, gull, mist, doom;
    var windMod, shoreMod, gullMod, mistMod, doomMod;
    var breeze, waves, cries, fog, distance;

    // Read custom params
    wind = In.kr(customBus0);      // P1: Wind strength - scaled by mist
    shore = In.kr(customBus1);     // P2: Shore distance - curve set by doom
    gull = In.kr(customBus2);      // P3: Gull presence - modulates wind AND doom
    mist = In.kr(customBus3);      // P4: Mist density - feeds back to shore
    doom = In.kr(customBus4);      // P5: Doom approach - master isolation axis

    // BUTTERFLY EFFECT: Cross-modulation network
    windMod = wind * (0.3 + (mist * 0.7));
    shoreMod = shore.linexp(0, 1, 0.2, 5) * (1 + (mist * doom * 1.2));
    gullMod = gull * (1 + (doom.squared * 0.45));
    mistMod = mist * (0.4 + (wind * shore * 0.6));
    doomMod = doom * (1 + (gull * mist * 0.35));

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

    // DSP: Isolated isle soundscape
    
    // Breeze: wind through grass
    breeze = PinkNoise.ar(0.3) * (1 + (LFNoise1.kr(windMod * 3) * 0.4));
    breeze = RHPF.ar(breeze, freq * windMod.linlin(0, 1, 2, 8), 0.3);
    breeze = breeze + (WhiteNoise.ar(0.1) * LFNoise2.kr(windMod * 5).range(0, 1));
    breeze = breeze * windMod.linlin(0, 1, 0.3, 0.8);
    
    // Waves: distant surf
    waves = BrownNoise.ar(0.25) + (PinkNoise.ar(0.15) * shoreMod.linlin(0, 1, 0.5, 1));
    waves = RLPF.ar(waves, freq * shoreMod.linlin(0, 1, 0.5, 2), 0.4);
    waves = waves * (1 + (SinOsc.kr(shoreMod * 0.15) * 0.4));
    waves = waves * shoreMod.linlin(0, 1, 0.2, 0.6);
    
    // Cries: gull-like tones
    cries = SinOsc.ar(
        freq * gullMod.linlin(0, 1, 3, 6) * (1 + (LFNoise1.kr(4) * 0.1)),
        0,
        0.1
    );
    cries = cries * LFPulse.kr(gullMod.linexp(0, 1, 0.1, 2), 0, 0.1);
    cries = cries * gullMod.linlin(0, 1, 0.1, 0.5);
    
    // Fog: muffled low presence
    fog = LFNoise1.ar(mistMod * 10) * 0.15;
    fog = RLPF.ar(fog, freq * mistMod.linlin(0, 1, 0.5, 1.5), 0.5);
    fog = fog + (SinOsc.ar(freq * 0.5, 0, 0.1) * mistMod);
    
    // Distance: doom closing in
    distance = SinOsc.ar(freq * [1, 1.5, 2], 0, [0.1, 0.06, 0.03]).sum;
    distance = distance * (1 + (LFNoise1.kr(doomMod * 2) * 0.2));
    distance = CombL.ar(distance, 0.3, doomMod.linlin(0, 1, 0.1, 0.25), doomMod * 1.5);
    distance = distance * doomMod.linlin(0, 1, 0.1, 0.6);
    
    // Mix based on doom (isolation axis)
    sig = breeze + waves + cries + fog + distance;
    
    // Isolation reverb
    sig = sig + (AllpassC.ar(sig, 0.1, mistMod.linlin(0, 1, 0.03, 0.08), doomMod * 0.5) * 0.2);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_wicker_isle loaded".postln;
