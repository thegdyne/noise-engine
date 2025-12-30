SynthDef(\forge_wicker_maypole, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var dance, ribbon, spiral, trance, weave;
    var danceMod, ribbonMod, spiralMod, tranceMod, weaveMod;
    var motion, colors, vertigo, pulse;

    // Read custom params
    dance = In.kr(customBus0);     // P1: Dance intensity - scaled by spiral
    ribbon = In.kr(customBus1);    // P2: Ribbon flutter - curve set by weave
    spiral = In.kr(customBus2);    // P3: Spiral tightness - modulates dance AND trance
    trance = In.kr(customBus3);    // P4: Trance depth - feeds back to ribbon
    weave = In.kr(customBus4);     // P5: Weave complexity - master hypnosis axis

    // BUTTERFLY EFFECT: Cross-modulation network
    danceMod = dance * (0.35 + (spiral * 0.65));
    ribbonMod = ribbon.linexp(0, 1, 0.3, 8) * (1 + (trance * weave * 1.3));
    spiralMod = spiral * (1 + (weave.squared * 0.5));
    tranceMod = trance * (0.4 + (dance * ribbon * 0.6));
    weaveMod = weave * (1 + (spiral * trance * 0.4));

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

    // DSP: Hypnotic circular dance
    
    // Motion: rotating modulated tones
    motion = SinOsc.ar(freq * [1, 2, 3], 0, [0.3, 0.15, 0.08]);
    motion = motion * (1 + (SinOsc.kr(danceMod * spiralMod * 2, [0, 0.5pi, pi]) * 0.4));
    motion = motion.sum;
    
    // Colors: ribbon-like AM modulation
    colors = SinOsc.ar(freq * [1.5, 2.5, 3.5], 0, [0.2, 0.12, 0.06]);
    colors = colors * SinOsc.kr(ribbonMod * [1, 1.3, 1.7], 0, 0.5, 0.5);
    colors = colors.sum;
    colors = colors * (1 + (LFTri.kr(tranceMod * 0.5) * 0.2));
    
    // Vertigo: spiral phase shifting
    vertigo = Mix.fill(4, { |i|
        var phase, speed;
        speed = spiralMod * (i + 1) * 0.3;
        phase = SinOsc.kr(speed, i * 0.5pi).range(0, 2pi);
        SinOsc.ar(freq * (i + 1), phase, 0.08 / (i + 1))
    });
    vertigo = vertigo * tranceMod.linlin(0, 1, 0.3, 1);
    
    // Pulse: heartbeat of the dance
    pulse = SinOsc.ar(freq * 0.5, 0, 0.15);
    pulse = pulse * (1 + (SinOsc.kr(danceMod * 4) * weaveMod * 0.3));
    
    // Mix based on weave (hypnosis axis)
    sig = motion + (colors * weaveMod.linlin(0, 1, 0.5, 1.2)) + (vertigo * weaveMod) + pulse;
    
    // Circular stereo motion
    sig = [sig, DelayC.ar(sig, 0.02, SinOsc.kr(spiralMod).range(0.005, 0.02))];
    sig = sig * (1 + (SinOsc.kr(tranceMod * 0.2, [0, 0.5pi]) * 0.15));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_wicker_maypole loaded".postln;
