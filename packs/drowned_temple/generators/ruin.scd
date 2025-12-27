// ruin: Crumbling ancient architecture
SynthDef(\forge_drowned_temple_ruin, { |out, freqBus, cutoffBus, resBus, attackBus, decayBus,
                                  filterTypeBus, envEnabledBus, envSourceBus=0,
                                  clockRateBus, clockTrigBus,
                                  midiTrigBus=0, slotIndex=0,
                                  customBus0, customBus1, customBus2, customBus3, customBus4,
                                  portamentoBus|

    var sig, freq, filterFreq, rq, filterType, attack, decay, amp, envSource, clockRate, portamento;
    var erosion, weight, fracture, memory, void;

    // Theme params
    erosion = In.kr(customBus0).linlin(0, 1, 0.1, 0.6);     // P1: Erosion texture
    weight = In.kr(customBus1).linlin(0, 1, 0.3, 1);        // P2: Stone weight
    fracture = In.kr(customBus2).linlin(0, 1, 1, 8);        // P3: Fracture rate
    memory = In.kr(customBus3).linlin(0, 1, 0.1, 0.5);      // P4: Fading memory tone
    void = In.kr(customBus4).linlin(0, 1, 0.1, 0.5);        // P5: Empty void

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

    // DSP: Erosion - continuous textured noise
    sig = LPF.ar(Crackle.ar(1.6) * erosion * 0.3, freq * 4);

    // Heavy stone presence
    sig = sig + (SinOsc.ar(freq * [0.5, 1]) * weight * 0.25);
    sig = sig + (LPF.ar(Pulse.ar(freq * 0.5, 0.3), 400) * weight * 0.15);

    // Fracture events - stereo
    sig = sig + (Ringz.ar(Dust.ar(fracture) * 0.25, freq * [0.7, 1, 1.5], 0.2) * 0.4);

    // Memory - fading distant tone
    sig = sig + (SinOsc.ar(freq * 2 * LFNoise1.kr(0.05).range(0.98, 1.02)) * memory * LFNoise1.kr(0.1).range(0.3, 1) * 0.15);

    // Void - empty filtered space
    sig = sig + (LPF.ar(PinkNoise.ar(void * 0.3), 300));

    sig = sig * 0.4;

    // Output chain
    sig = LeakDC.ar(sig);
    sig = ~multiFilter.(sig, filterType, filterFreq, rq);
    sig = ~envVCA.(sig, envSource, clockRate, attack, decay, amp, clockTrigBus, midiTrigBus, slotIndex);
    sig = ~ensure2ch.(sig);
    Out.ar(out, sig);
}).add;
"  * forge_drowned_temple_ruin loaded".postln;
