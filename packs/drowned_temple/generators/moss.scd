// moss: Soft overgrown decay
SynthDef(\forge_drowned_temple_moss, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var soft, organic, growth, damp, life;

    // Theme params
    soft = In.kr(customBus0).linlin(0, 1, 0.3, 1);          // P1: Softness
    organic = In.kr(customBus1).linlin(0, 1, 0.05, 0.3);    // P2: Organic movement
    growth = In.kr(customBus2).linlin(0, 1, 0.2, 0.7);      // P3: Growth texture
    damp = In.kr(customBus3).linlin(0, 1, 300, 1500);       // P4: Damp cutoff
    life = In.kr(customBus4).linlin(0, 1, 0, 0.4);          // P5: Tiny life sounds

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

    // DSP: Soft pad - heavily filtered
    sig = LPF.ar(Saw.ar(freq * [0.5, 0.501, 1, 1.002]) * soft, damp);
    sig = Splay.ar(sig, 0.6) * 0.25;

    // Organic movement - slow modulated noise
    sig = sig + (LPF.ar(PinkNoise.ar(growth), damp * 0.5) * LFNoise1.kr(organic).range(0.5, 1) * 0.4);

    // Tiny life - sparse high crackles
    sig = sig + (HPF.ar(Dust2.ar(life * 15) * 0.08, 3000));

    // Sub warmth
    sig = sig + (SinOsc.ar(freq * 0.25) * soft * 0.15);

    sig = sig * 0.45;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_drowned_temple_moss loaded".postln;
