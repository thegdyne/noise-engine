// madness: Sanity shattering - the mind breaks
SynthDef(\forge_rlyeh_madness, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var fracture, spiral, voices, paranoia, hysteria;

    // Theme params
    fracture = In.kr(customBus0).linlin(0, 1, 0, 0.3);     // P1: Reality fracture
    spiral = In.kr(customBus1).linlin(0, 1, 0.5, 8);       // P2: Descending spiral rate
    voices = In.kr(customBus2).linlin(0, 1, 0, 0.6);       // P3: Whispering voices
    paranoia = In.kr(customBus3).linlin(0, 1, 1, 20);      // P4: Paranoid jitter
    hysteria = In.kr(customBus4).linlin(0, 1, 0, 0.7);     // P5: Hysterical FM

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

    // DSP: Fractured oscillators
    sig = SinOsc.ar(freq * (1 + (LFNoise2.kr(paranoia) * fracture)));
    sig = sig + (Saw.ar(freq * 0.5 * (1 + (LFNoise2.kr(paranoia * 0.7) * fracture * 0.5))) * 0.5);

    // Descending spiral
    sig = sig * SinOsc.kr(spiral).range(0.3, 1);

    // Whispering voices (granular noise)
    sig = sig + (BPF.ar(PinkNoise.ar(voices), freq * LFNoise0.kr(8).range(1, 4), 0.1) * 2);

    // Hysterical FM
    sig = sig + (SinOscFB.ar(freq * 2, hysteria * 0.8) * hysteria * 0.3);

    sig = sig * 0.25;

    // Output chain (with Limiter for FM feedback)
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = Limiter.ar(sig, 0.95);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_rlyeh_madness loaded".postln;
