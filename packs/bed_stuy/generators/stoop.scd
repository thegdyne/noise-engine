// stoop: Brownstone steps, concrete resonance
SynthDef(\forge_bed_stuy_stoop, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var stone, weight, iron, settle, urban;

    // Theme params
    stone = In.kr(customBus0).linlin(0, 1, 0.3, 1);         // P1: Stone resonance
    weight = In.kr(customBus1).linlin(0, 1, 0.2, 0.8);      // P2: Heavy presence
    iron = In.kr(customBus2).linlin(0, 1, 0, 0.5);          // P3: Iron railing
    settle = In.kr(customBus3).linlin(0, 1, 1, 6);          // P4: Settling creaks
    urban = In.kr(customBus4).linlin(0, 1, 0.1, 0.5);       // P5: City rumble

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

    // DSP: Stone body - low filtered tone
    sig = LPF.ar(Pulse.ar(freq * [0.5, 0.501], 0.4) * stone, 600) * 0.4;

    // Heavy sub presence
    sig = sig + (SinOsc.ar(freq * 0.25) * weight * 0.4);

    // Iron railing - metallic ring
    sig = sig + (Ringz.ar(Dust.ar(settle) * 0.15, freq * [3, 4.5, 6], 0.1) * iron);

    // Urban rumble - distant traffic
    sig = sig + (LPF.ar(BrownNoise.ar(urban), 150) * 0.5);

    sig = sig * 0.45;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_bed_stuy_stoop loaded".postln;
