SynthDef(\forge_wicker_pyre, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var kindle, blaze, ember, smoke, ash;
    var kindleMod, blazeMod, emberMod, smokeMod, ashMod;
    var crackle, roar, glow, sparks;

    // Read custom params
    kindle = In.kr(customBus0);    // P1: Kindle intensity - scaled by ember
    blaze = In.kr(customBus1);     // P2: Blaze height - curve set by ash
    ember = In.kr(customBus2);     // P3: Ember glow - modulates kindle AND smoke
    smoke = In.kr(customBus3);     // P4: Smoke density - feeds back to blaze
    ash = In.kr(customBus4);       // P5: Ash accumulation - master decay reshaper

    // BUTTERFLY EFFECT: Cross-modulation network
    kindleMod = kindle * (0.4 + (ember * 0.6));
    blazeMod = blaze.linexp(0, 1, 0.5, 8) * (1 + (smoke * ash * 1.5));
    emberMod = ember * (1 + (ash.squared * 0.4));
    smokeMod = smoke * (0.3 + (kindle * blaze * 0.7));
    ashMod = ash * (1 + (ember * smoke * 0.5));

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

    // DSP: Fire crackling and roar
    
    // Crackle: rhythmic pops and snaps
    crackle = Dust.ar(kindleMod.linexp(0, 1, 5, 80) * [1, 1.2]);
    crackle = Ringz.ar(crackle, [2200, 3500, 5800, 8200] * emberMod.linlin(0, 1, 0.5, 1.5), 0.01).sum * 0.4;
    crackle = crackle * (1 + (LFNoise1.kr(blazeMod) * 0.5));
    
    // Roar: low rumble of flames
    roar = BrownNoise.ar(0.3) + (PinkNoise.ar(0.2) * smokeMod);
    roar = RLPF.ar(roar, freq * blazeMod.linlin(0, 1, 1, 4), 0.3 + (ashMod * 0.4));
    roar = roar * kindleMod.linlin(0, 1, 0.3, 1);
    
    // Glow: warm sustained tone
    glow = SinOsc.ar(freq * [1, 2.01, 3.02], 0, [0.3, 0.15, 0.08]).sum;
    glow = glow * emberMod.linlin(0, 1, 0.2, 0.8);
    glow = glow * (1 + (SinOsc.kr(blazeMod * 2) * smokeMod * 0.3));
    
    // Sparks: occasional bright transients
    sparks = Dust.ar(ashMod.linexp(0, 1, 0.5, 8) * [1, 0.8]);
    sparks = Ringz.ar(sparks, freq * [4, 6, 8], smokeMod.linlin(0, 1, 0.05, 0.2)).sum * 0.2;
    
    // Mix based on ash (chaos axis)
    sig = (roar * 0.4) + (crackle * (0.3 + (ashMod * 0.3))) + (glow * (1 - (ashMod * 0.5))) + sparks;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_wicker_pyre loaded".postln;
