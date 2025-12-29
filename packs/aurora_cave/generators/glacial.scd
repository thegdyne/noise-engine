SynthDef(\forge_aurora_cave_glacial, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                         filterTypeBus, envEnabledBus, envSourceBus=0,
                                         clockRateBus, clockTrigBus,
                                         midiTrigBus=0, slotIndex=0,
                                         customBus0, customBus1, customBus2, customBus3, customBus4,
                                         portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var mass, friction, freeze, depth, crack;
    var exciter, bow, sub, crackle, delayTime;

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
    mass = In.kr(customBus0);
    friction = In.kr(customBus1);
    freeze = In.kr(customBus2);
    depth = In.kr(customBus3);
    crack = In.kr(customBus4);

    // Bowed string simulation via friction noise through resonator
    exciter = LFNoise1.ar(friction.linexp(0, 1, 20, 200)) * friction.linlin(0, 1, 0.1, 0.4);
    exciter = exciter + (LFNoise2.ar(friction.linexp(0, 1, 80, 400)) * friction * 0.2);
    
    // Waveguide-style delay for pitched resonance
    delayTime = freq.reciprocal;
    bow = CombL.ar(exciter, 0.05, delayTime, freeze.linlin(0, 1, 2, 8));
    bow = LPF.ar(bow, freeze.linexp(0, 1, 2000, 800));
    
    // Second voice detuned
    bow = bow + CombL.ar(exciter * 0.7, 0.05, (freq * 1.003).reciprocal, freeze.linlin(0, 1, 1.5, 6));
    
    // Add slight vibrato modulation
    bow = DelayC.ar(bow, 0.01, SinOsc.kr(LFNoise2.kr(0.1).range(3, 6)).range(0, 0.003));

    // Subsonic mass layer
    sub = SinOsc.ar(freq * 0.5) * mass * 0.5;
    sub = sub + (SinOsc.ar(freq * 0.25) * mass * depth * 0.4);
    sub = LPF.ar(sub, 200);

    // Ice stress crackle
    crackle = Dust.ar(crack.linexp(0, 1, 0.5, 30)) * 0.2;
    crackle = Ringz.ar(crackle, freq * [2.3, 3.7, 5.1], 0.08).sum;

    // Mix layers
    sig = (bow * 0.6) + sub + (crackle * crack);
    
    // Frozen character - slight comb filtering for icy shimmer
    sig = sig + (CombL.ar(sig, 0.03, freeze.linlin(0, 1, 0.008, 0.025), 0.15) * freeze * 0.25);

    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex); sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_aurora_cave_glacial loaded".postln;
