SynthDef(\forge_fuego_celeste_ash_rise, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                          filterTypeBus, envEnabledBus, envSourceBus=0,
                                          clockRateBus, clockTrigBus,
                                          midiTrigBus=0, slotIndex=0,
                                          customBus0, customBus1, customBus2, customBus3, customBus4,
                                          portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var rise, billow, choke, grey, curl;
    var riseLFO, billowMod, noiseBase, toneBase, curlPan, greyFreq;

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

    // Theme parameters
    rise = In.kr(customBus0);       // upward drift
    billow = In.kr(customBus1);     // turbulence
    choke = In.kr(customBus2);      // density
    grey = In.kr(customBus3);       // neutral timbre
    curl = In.kr(customBus4);       // swirl motion

    // Rising modulation - slow upward sweep
    riseLFO = LFSaw.kr(rise.linexp(0, 1, 0.05, 0.5)).range(0.8, 1.5);

    // Billowing turbulence - chaotic modulation
    billowMod = LFNoise1.kr(billow.linexp(0, 1, 0.5, 8)).range(0.9, 1.1);

    // Grey frequency - dull mid-range center
    greyFreq = grey.linexp(0, 1, 300, 1200);

    // Noise base - filtered for ash texture
    noiseBase = PinkNoise.ar * choke;
    noiseBase = BPF.ar(noiseBase, freq * riseLFO * billowMod, 0.4 + (choke * 0.4));

    // Tonal base - adds slight pitch to the ash
    toneBase = LFTri.ar(freq * riseLFO * billowMod * 0.5, 0, 0.3);
    toneBase = LPF.ar(toneBase, greyFreq);

    // Mix noise and tone
    sig = (noiseBase * 0.6) + (toneBase * (1 - grey) * 0.4);

    // Add subtle high frequency ash particles
    sig = sig + (Dust.ar(choke.linexp(0, 1, 20, 200)) * 0.1);

    // Grey filter - removes color
    sig = BPF.ar(sig, greyFreq * billowMod, 0.8);

    // Curl - swirling pan modulation
    curlPan = SinOsc.kr(curl.linexp(0, 1, 0.1, 2)).range(-0.8, 0.8) * curl;
    sig = Pan2.ar(sig, curlPan);

    // Standard post-chain
    sig = sig * 8;  // gain boost
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);

    Out.ar(out, sig);
}).add;
"  * forge_fuego_celeste_ash_rise loaded".postln;
