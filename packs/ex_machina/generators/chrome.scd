// chrome: Metallic skull mask - reflective, cold beauty
SynthDef(\forge_ex_machina_chrome, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var shine, cold, reflect, skull, amber;

    // Theme params
    shine = In.kr(customBus0).linlin(0, 1, 0.3, 1);         // P1: Chrome shine
    cold = In.kr(customBus1).linlin(0, 1, 2000, 8000);      // P2: Cold brightness
    reflect = In.kr(customBus2).linlin(0, 1, 3, 15);        // P3: Reflection rate
    skull = In.kr(customBus3).linlin(0, 1, 0.2, 0.7);       // P4: Skull resonance
    amber = In.kr(customBus4).linlin(0, 1, 0, 0.4);         // P5: Amber glow warmth

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

    // DSP: Chrome shimmer - high metallic harmonics
    sig = Ringz.ar(Dust.ar(reflect) * 0.2, freq * [8, 10, 12, 15], 0.08) * shine;
    sig = Splay.ar(sig, 0.7);

    // Skull resonance - hollow metallic body
    sig = sig + (BPF.ar(PinkNoise.ar(skull * 0.4), freq * 2, 0.2));
    sig = sig + (Ringz.ar(Dust.ar(reflect * 0.5) * 0.15, freq * [1.5, 2.5], 0.15) * skull);

    // Cold brightness filter
    sig = HPF.ar(sig, 200) + (sig * 0.3);

    // Amber glow - warm undertone
    sig = sig + (SinOsc.ar(freq * [0.5, 1]) * amber * 0.25);

    // Continuous metallic bed
    sig = sig + (BPF.ar(WhiteNoise.ar(shine * 0.2), cold, 0.15));

    sig = sig * 0.45;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_ex_machina_chrome loaded".postln;
