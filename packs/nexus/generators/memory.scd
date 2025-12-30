SynthDef(\forge_nexus_memory, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, ampVal, envSource, clockRate, portamento;
    var clr, frg, ech, blr, tru;
    var clarity, fragment, echo, blur, truth, jumpTrig, phaseJump;

    // Read custom params - memory fragment topology
    clr = In.kr(customBus0);       // P1: Clarity (signal vs noise)
    frg = In.kr(customBus1);       // P2: Fragmentation (phase discontinuities)
    ech = In.kr(customBus2);       // P3: Echo loops (delay repetition)
    blr = In.kr(customBus3);       // P4: Blur (diffusion/smear)
    tru = In.kr(customBus4);       // P5: Truth axis (stable vs fabricated)

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

    // DSP: Memory implants with phase discontinuities
    
    // Fragment trigger: random phase jumps
    jumpTrig = Dust.kr(frg.linexp(0, 1, 0.5, 15));
    phaseJump = LFNoise0.kr(frg.linexp(0, 1, 0.5, 15)).range(0, 2pi) * frg;
    
    // Clarity: clean signal vs noisy recall
    clarity = SinOsc.ar(freq * [1, 2, 3], phaseJump, [0.3, 0.15, 0.08] * clr.linlin(0, 1, 0.5, 1)).sum;
    clarity = clarity + (WhiteNoise.ar((1 - clr) * 0.15));
    clarity = RLPF.ar(clarity, clr.linexp(0, 1, 2000, 12000), 0.5);
    
    // Fragment: ring mod discontinuities
    fragment = clarity * SinOsc.ar(freq * frg.linlin(0, 1, 1, 5), phaseJump);
    fragment = (fragment * frg) + (clarity * (1 - frg));
    
    // Echo: looping delay repetition
    echo = CombL.ar(fragment, 0.5, ech.linlin(0, 1, 0.1, 0.4), ech * 3);
    echo = echo + (AllpassC.ar(echo, 0.1, ech.linlin(0, 1, 0.03, 0.08), ech) * 0.5);
    echo = echo * ech * 0.5;
    
    // Blur: diffusion smear
    blur = fragment + echo;
    blur = blur + (DelayC.ar(blur, 0.05, LFNoise2.kr(blr * 5 + 1).range(0.01, 0.04)) * blr * 0.4);
    blur = LPF.ar(blur, blr.linexp(0, 1, 12000, 3000)) * (0.7 + (blr * 0.3));
    
    // Truth: stable vs fabricated
    truth = blur;
    truth = (truth * tru) + ((truth * SinOsc.ar(freq * 0.5, LFNoise0.kr(5) * pi)).abs * (1 - tru) * 0.7);
    truth = truth + (PinkNoise.ar((1 - tru) * 0.08));
    
    sig = truth;
    
    // Memory glitch: occasional dropout
    sig = sig * (1 - (Trig.ar(Dust.ar(frg * 3), 0.02) * frg * 0.5));

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, ampVal, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_nexus_memory loaded".postln;
