// Heat Wall -- approaching inferno, rising temperature
// Role: bed

SynthDef(\forge_icarus_heat_wall, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                     filterTypeBus, envEnabledBus, envSourceBus=0,
                                     clockRateBus, clockTrigBus,
                                     midiTrigBus=0, slotIndex=0,
                                     customBus0, customBus1, customBus2, customBus3, customBus4,
                                     portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var temp, radiant, convect, scorch, plasma;
    var heat, glow, convectMod, burn, crackle;

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
    temp = In.kr(customBus0).linexp(0, 1, 400, 8000);    // Heat filter freq
    radiant = In.kr(customBus1).linlin(0, 1, 0.0, 0.5); // Upper glow level
    convect = In.kr(customBus2).linlin(0, 1, 0.2, 4);   // Convection rate
    scorch = In.kr(customBus3).linlin(0, 1, 1, 12);     // Distortion drive
    plasma = In.kr(customBus4).linlin(0, 1, 0, 40);     // Crackle density

    // Convection modulation - rising and falling air
    convectMod = LFNoise2.kr(convect, 0.3, 1);

    // Base heat - filtered noise representing thermal energy
    heat = PinkNoise.ar(0.5) + BrownNoise.ar(0.3);
    heat = RLPF.ar(heat, temp * convectMod, 0.4);

    // Radiant glow - upper harmonics
    glow = Saw.ar(freq * 2 * convectMod, radiant);
    glow = HPF.ar(glow, 3000);

    // Scorching edge - distortion
    burn = heat * scorch;
    burn = burn.tanh * (1 / scorch.sqrt);

    // Plasma crackle - ionized dust
    crackle = Dust2.ar(plasma) * 0.3;
    crackle = Ringz.ar(crackle, freq * LFNoise0.kr(8, 2, 4), 0.03);

    // Combine layers
    sig = burn + glow + crackle;

    // Stereo spread - heat shimmer
    sig = ~stereoSpread.(sig, 0.15, 0.35);

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;

"  * forge_icarus_heat_wall loaded".postln;
